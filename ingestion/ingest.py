"""
Main ingestion script for processing markdown documents into vector DB and knowledge graph.
"""

import os
import asyncio
import logging
import json
import glob
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse
import sys

import asyncpg
from dotenv import load_dotenv

# File watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("watchdog not installed. Install with: pip install watchdog")

from .chunker import ChunkingConfig, create_chunker, DocumentChunk
from .embedder import create_embedder
from .graph_builder import create_graph_builder
from .file_parsers import parse_document, is_supported_file, get_supported_extensions

# Import agent utilities
try:
    from ..agent.db_utils import initialize_database, close_database, db_pool
    from ..agent.graph_utils import initialize_graph, close_graph
    from ..agent.models import IngestionConfig, IngestionResult
except ImportError:
    # For direct execution or testing
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.db_utils import initialize_database, close_database, db_pool
    from agent.graph_utils import initialize_graph, close_graph
    from agent.models import IngestionConfig, IngestionResult

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into vector DB and knowledge graph."""
    
    def __init__(
        self,
        config: IngestionConfig,
        documents_folder: str = "documents",
        clean_before_ingest: bool = False
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            config: Ingestion configuration
            documents_folder: Folder containing markdown documents
            clean_before_ingest: Whether to clean existing data before ingestion
        """
        self.config = config
        self.documents_folder = documents_folder
        self.clean_before_ingest = clean_before_ingest
        
        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
            use_semantic_splitting=config.use_semantic_chunking
        )
        
        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()
        self.graph_builder = create_graph_builder()
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return
        
        logger.info("="*70)
        logger.info("🔧 INITIALIZING INGESTION PIPELINE")
        logger.info("="*70)
        
        try:
            logger.info("   📊 Connecting to PostgreSQL...")
            await initialize_database()
            logger.info("   ✅ PostgreSQL connected")
            
            logger.info("   🕸️  Connecting to Neo4j...")
            await initialize_graph()
            logger.info("   ✅ Neo4j connected")
            
            logger.info("   🔗 Initializing Graphiti client...")
            await self.graph_builder.initialize()
            logger.info("   ✅ Graphiti initialized")
            
            self._initialized = True
            logger.info("="*70)
            logger.info("✅ INGESTION PIPELINE READY")
            logger.info("="*70)
        except Exception as e:
            logger.error(f"❌ FAILED TO INITIALIZE: {e}")
            raise
    
    async def close(self):
        """Close database connections."""
        if self._initialized:
            await self.graph_builder.close()
            await close_graph()
            await close_database()
            self._initialized = False
    
    async def _document_exists(self, source_path: str) -> bool:
        """Check if a document with the given source path already exists."""
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM documents WHERE source = $1",
                    source_path
                )
                return result > 0
        except Exception as e:
            logger.warning(f"Error checking if document exists: {e}")
            return False
    
    async def _get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating file hash: {e}")
            return ""
    
    async def ingest_documents(
        self,
        progress_callback: Optional[callable] = None
    ) -> List[IngestionResult]:
        """
        Ingest all documents from the documents folder.
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of ingestion results
        """
        if not self._initialized:
            await self.initialize()
        
        # Clean existing data if requested
        if self.clean_before_ingest:
            logger.info("🧹 Cleaning existing data from databases...")
            await self._clean_databases()
            logger.info("✅ Database cleaned")
        
        # Find all supported files
        markdown_files = self._find_markdown_files()
        
        if not markdown_files:
            logger.warning(f"⚠️  No files found in {self.documents_folder}")
            return []
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📁 Found {len(markdown_files)} file(s) to process")
        logger.info(f"📂 Folder: {self.documents_folder}")
        logger.info(f"{'='*70}\n")
        
        # Check existing documents
        logger.info("🔍 Checking for already ingested files...")
        files_to_process = []
        files_skipped = []
        
        for file_path in markdown_files:
            source_path = os.path.relpath(file_path, self.documents_folder)
            exists = await self._document_exists(source_path)
            
            if exists:
                files_skipped.append(file_path)
                logger.info(f"⏭️  SKIPPED (already ingested): {os.path.basename(file_path)}")
            else:
                files_to_process.append(file_path)
        
        if files_skipped:
            logger.info(f"\n✅ Skipped {len(files_skipped)} already ingested file(s)")
        
        if not files_to_process:
            logger.info("\n✨ All files are already ingested! Nothing to do.")
            return []
        
        logger.info(f"\n🚀 Processing {len(files_to_process)} new file(s)...\n")
        
        results = []
        start_time = datetime.now()
        
        for i, file_path in enumerate(files_to_process, 1):
            try:
                file_name = os.path.basename(file_path)
                logger.info(f"\n{'─'*70}")
                logger.info(f"📄 [{i}/{len(files_to_process)}] Processing: {file_name}")
                logger.info(f"   Path: {file_path}")
                logger.info(f"{'─'*70}")
                
                result = await self._ingest_single_document(file_path)
                results.append(result)
                
                # Log result
                status = "✅" if not result.errors else "❌"
                logger.info(f"{status} Completed: {file_name}")
                logger.info(f"   • Chunks: {result.chunks_created}")
                logger.info(f"   • Entities: {result.entities_extracted}")
                logger.info(f"   • Relationships: {result.relationships_created}")
                logger.info(f"   • Time: {result.processing_time_ms/1000:.2f}s")
                
                if progress_callback:
                    progress_callback(i, len(files_to_process))
                
            except Exception as e:
                logger.error(f"❌ Failed to process {file_path}: {e}")
                results.append(IngestionResult(
                    document_id="",
                    title=os.path.basename(file_path),
                    chunks_created=0,
                    entities_extracted=0,
                    relationships_created=0,
                    processing_time_ms=0,
                    errors=[str(e)]
                ))
        
        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        total_chunks = sum(r.chunks_created for r in results)
        total_entities = sum(r.entities_extracted for r in results)
        total_relationships = sum(r.relationships_created for r in results)
        total_errors = sum(len(r.errors) for r in results)
        successful = len([r for r in results if not r.errors])
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 INGESTION SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"✅ Successfully processed: {successful}/{len(results)} files")
        logger.info(f"⏭️  Skipped (already ingested): {len(files_skipped)} files")
        logger.info(f"📦 Total chunks created: {total_chunks}")
        logger.info(f"🔗 Total entities extracted: {total_entities}")
        logger.info(f"🕸️  Total relationships created: {total_relationships}")
        logger.info(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        if total_errors > 0:
            logger.info(f"❌ Total errors: {total_errors}")
        logger.info(f"{'='*70}\n")
        
        return results
    
    async def _ingest_single_document(self, file_path: str) -> IngestionResult:
        """
        Ingest a single document.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Ingestion result
        """
        start_time = datetime.now()
        
        # Read document with parser
        logger.info(f"   📖 Reading file: {os.path.basename(file_path)}")
        try:
            document_content, parser_metadata = self._read_document(file_path)
            file_type = parser_metadata.get('file_type', 'unknown')
            logger.info(f"   ✅ File read successfully ({file_type}, {len(document_content):,} chars)")
        except Exception as e:
            logger.error(f"   ❌ FAILED TO READ FILE: {e}")
            raise
        
        document_title = self._extract_title(document_content, file_path)
        document_source = os.path.relpath(file_path, self.documents_folder)
        
        # Extract metadata from content
        document_metadata = self._extract_document_metadata(document_content, file_path)
        document_metadata.update(parser_metadata)  # Add parser metadata
        
        logger.info(f"   📝 Document: {document_title}")
        logger.info(f"   📏 Content length: {len(document_content):,} characters")
        logger.info(f"   📄 File type: {file_type}")
        
        # Chunk the document
        logger.info(f"   ✂️  Chunking document...")
        chunks = await self.chunker.chunk_document(
            content=document_content,
            title=document_title,
            source=document_source,
            metadata=document_metadata
        )
        
        if not chunks:
            logger.warning(f"   ⚠️  No chunks created for {document_title}")
            return IngestionResult(
                document_id="",
                title=document_title,
                chunks_created=0,
                entities_extracted=0,
                relationships_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created"]
            )
        
        logger.info(f"   ✅ Created {len(chunks)} chunks")
        
        # Extract entities if configured (before embeddings)
        entities_extracted = 0
        if self.config.extract_entities and not self.config.skip_graph_building:
            logger.info(f"   🔍 Extracting entities...")
            # For very large documents, skip entity extraction to speed up processing
            max_chunks_for_entity_extraction = 5000
            if len(chunks) > max_chunks_for_entity_extraction:
                logger.warning(f"   ⚠️  Document has {len(chunks)} chunks. Skipping entity extraction for speed.")
                logger.info(f"   ℹ️  Entities will be extracted automatically by Graphiti during graph building.")
                entities_extracted = 0
            else:
                try:
                    chunks = await self.graph_builder.extract_entities_from_chunks(chunks)
                    entities_extracted = sum(
                        len(chunk.metadata.get("entities", {}).get("companies", [])) +
                        len(chunk.metadata.get("entities", {}).get("technologies", [])) +
                        len(chunk.metadata.get("entities", {}).get("people", []))
                        for chunk in chunks
                    )
                    logger.info(f"   ✅ Extracted {entities_extracted} entities")
                except Exception as e:
                    logger.warning(f"   ⚠️  Entity extraction failed: {e}")
                    entities_extracted = 0
        
        # Generate embeddings
        logger.info(f"   🔢 Generating embeddings for {len(chunks)} chunks...")
        embedding_start = datetime.now()
        failed_embeddings = 0
        
        for i, chunk in enumerate(chunks):
            try:
                embedding = await self.embedder.embed_text(chunk.content)
                chunk.embedding = embedding
                
                # Progress logging
                if (i + 1) % 50 == 0 or (i + 1) == len(chunks):
                    elapsed = (datetime.now() - embedding_start).total_seconds()
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(chunks) - (i + 1)) / rate if rate > 0 else 0
                    logger.info(f"      Embeddings: {i+1}/{len(chunks)} ({((i+1)/len(chunks)*100):.1f}%) | "
                              f"Rate: {rate:.1f} chunks/s | Est. remaining: {remaining:.0f}s")
            except Exception as e:
                failed_embeddings += 1
                logger.warning(f"      ⚠️  Failed embedding for chunk {i}: {e}")
                # Continue without embedding for this chunk
        
        elapsed = (datetime.now() - embedding_start).total_seconds()
        if failed_embeddings > 0:
            logger.warning(f"   ⚠️  Embeddings: {len(chunks) - failed_embeddings}/{len(chunks)} successful ({failed_embeddings} failed)")
        else:
            logger.info(f"   ✅ Embeddings generated ({len(chunks)} chunks in {elapsed:.1f}s)")
        
        # Save to PostgreSQL
        logger.info(f"   💾 Saving to PostgreSQL...")
        logger.info(f"      • Document: {document_title}")
        logger.info(f"      • Chunks: {len(chunks)}")
        logger.info(f"      • Source: {document_source}")
        
        try:
            save_start = datetime.now()
            document_id = await self._save_to_postgres(
                document_title,
                document_source,
                document_content,
                chunks,  # Use chunks (already have embeddings)
                document_metadata
            )
            save_time = (datetime.now() - save_start).total_seconds()
            logger.info(f"   ✅ Document saved to PostgreSQL (ID: {document_id[:8]}...) in {save_time:.1f}s")
        except Exception as e:
            logger.error(f"   ❌ FAILED TO SAVE TO POSTGRESQL: {e}")
            raise
        
        # Add to knowledge graph (if enabled)
        relationships_created = 0
        graph_errors = []
        
        if not self.config.skip_graph_building:
            try:
                logger.info(f"   🕸️  Building knowledge graph...")
                logger.info(f"      • Chunks to process: {len(chunks)}")
                logger.info(f"      • This may take a while for large documents...")
                
                graph_start = datetime.now()
                graph_result = await self.graph_builder.add_document_to_graph(
                    chunks=chunks,  # Use chunks (already have embeddings)
                    document_title=document_title,
                    document_source=document_source,
                    document_metadata=document_metadata
                )
                graph_time = (datetime.now() - graph_start).total_seconds()
                
                relationships_created = graph_result.get("episodes_created", 0)
                graph_errors = graph_result.get("errors", [])
                
                if relationships_created > 0:
                    logger.info(f"   ✅ Knowledge graph: {relationships_created} relationships created in {graph_time:.1f}s")
                else:
                    if graph_errors:
                        logger.warning(f"   ⚠️  Knowledge graph: No relationships created")
                        logger.warning(f"      Errors: {len(graph_errors)}")
                        for error in graph_errors[:3]:  # Show first 3 errors
                            logger.warning(f"      • {error}")
                    else:
                        logger.info(f"   ℹ️  Knowledge graph: Skipped (likely tabular data)")
                
            except Exception as e:
                error_msg = f"Failed to add to knowledge graph: {str(e)}"
                logger.error(f"   ❌ KNOWLEDGE GRAPH ERROR: {error_msg}")
                logger.error(f"      Exception type: {type(e).__name__}")
                graph_errors.append(error_msg)
        else:
            logger.info("Skipping knowledge graph building (skip_graph_building=True)")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return IngestionResult(
            document_id=document_id,
            title=document_title,
            chunks_created=len(chunks),
            entities_extracted=entities_extracted,
            relationships_created=relationships_created,
            processing_time_ms=processing_time,
            errors=graph_errors
        )
    
    def _find_markdown_files(self) -> List[str]:
        """Find all supported document files in the documents folder."""
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
            return []
        
        # Support multiple file types: .txt, .md, .pdf, .xls, .xlsx, .csv, .doc, .docx
        patterns = ["*.md", "*.markdown", "*.txt", "*.pdf", "*.xls", "*.xlsx", "*.csv", "*.doc", "*.docx"]
        files = []
        
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.documents_folder, "**", pattern), recursive=True))
        
        # Filter to only supported files
        files = [f for f in files if is_supported_file(f)]
        
        return sorted(files)
    
    def _read_document(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Read document content from file using appropriate parser.
        
        Returns:
            Tuple of (content, parser_metadata)
        """
        try:
            content, parser_metadata = parse_document(file_path)
            logger.info(f"Parsed {parser_metadata.get('file_type', 'unknown')} file: {file_path}")
            return content, parser_metadata
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            # Fallback to basic text reading
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, {"file_type": "text", "parser": "fallback"}
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content, {"file_type": "text", "parser": "fallback", "encoding": "latin-1"}
    
    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract title from document content or filename."""
        # Try to find markdown title
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0]
    
    def _extract_document_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from document content."""
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "ingestion_date": datetime.now().isoformat()
        }
        
        # Try to extract YAML frontmatter
        if content.startswith('---'):
            try:
                import yaml
                end_marker = content.find('\n---\n', 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict):
                        metadata.update(yaml_metadata)
            except ImportError:
                logger.warning("PyYAML not installed, skipping frontmatter extraction")
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")
        
        # Extract some basic metadata from content
        lines = content.split('\n')
        metadata['line_count'] = len(lines)
        metadata['word_count'] = len(content.split())
        
        return metadata
    
    async def _save_to_postgres(
        self,
        title: str,
        source: str,
        content: str,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any]
    ) -> str:
        """Save document and chunks to PostgreSQL using batch inserts."""
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Insert document
                document_result = await conn.fetchrow(
                    """
                    INSERT INTO documents (title, source, content, metadata)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id::text
                    """,
                    title,
                    source,
                    content,
                    json.dumps(metadata)
                )
                
                document_id = document_result["id"]
                
                # Insert chunks in batches (pgvector doesn't support bulk copy)
                logger.info(f"   💾 Saving {len(chunks)} chunks to PostgreSQL...")
                batch_size = 100
                total_batches = (len(chunks) + batch_size - 1) // batch_size
                
                for i in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    
                    # Insert each chunk in the batch
                    for chunk in batch_chunks:
                        # Convert embedding to PostgreSQL vector string format
                        embedding_data = None
                        if hasattr(chunk, 'embedding') and chunk.embedding:
                            # PostgreSQL vector format: '[1.0,2.0,3.0]' (no spaces after commas)
                            embedding_data = '[' + ','.join(map(str, chunk.embedding)) + ']'
                        
                        await conn.execute(
                            """
                            INSERT INTO chunks (document_id, content, embedding, chunk_index, metadata, token_count)
                            VALUES ($1::uuid, $2, $3::vector, $4, $5::jsonb, $6)
                            """,
                            document_id,
                            chunk.content,
                            embedding_data,
                            chunk.index,
                            json.dumps(chunk.metadata),
                            chunk.token_count
                        )
                    
                    if batch_num % 5 == 0 or batch_num == total_batches:
                        logger.info(f"      Batch {batch_num}/{total_batches} saved ({len(batch_chunks)} chunks)")
                
                logger.info(f"   ✅ Saved {len(chunks)} chunks to PostgreSQL")
                return document_id
    
    async def _clean_databases(self):
        """Clean existing data from databases."""
        logger.warning("Cleaning existing data from databases...")
        
        # Clean PostgreSQL
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM messages")
                await conn.execute("DELETE FROM sessions")
                await conn.execute("DELETE FROM chunks")
                await conn.execute("DELETE FROM documents")
        
        logger.info("Cleaned PostgreSQL database")
        
        # Clean knowledge graph
        await self.graph_builder.clear_graph()
        logger.info("Cleaned knowledge graph")
    
    async def watch_and_ingest(self, check_interval: int = 5):
        """
        Continuously watch for new files and ingest them automatically.
        
        Args:
            check_interval: How often to check for new files (seconds)
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info("="*70)
        logger.info("👀 STARTING CONTINUOUS FILE WATCHING")
        logger.info("="*70)
        logger.info(f"📂 Watching folder: {self.documents_folder}")
        logger.info(f"⏱️  Check interval: {check_interval} seconds")
        logger.info(f"📊 Status updates every: {check_interval * 6} seconds")
        logger.info("="*70)
        logger.info("💡 Press Ctrl+C to stop")
        logger.info("="*70)
        
        # Track processed files
        processed_files = set()
        last_status_time = datetime.now()
        status_interval = check_interval * 6  # Show status every 6 checks
        
        # Initial ingestion of existing files
        logger.info("\n🔄 Running initial ingestion of existing files...")
        initial_results = await self.ingest_documents()
        for result in initial_results:
            if result.document_id:
                processed_files.add(result.title)
        
        logger.info("\n✅ Initial ingestion complete. Now watching for new files...\n")
        
        try:
            while True:
                # Check for new files
                markdown_files = self._find_markdown_files()
                new_files = []
                
                for file_path in markdown_files:
                    source_path = os.path.relpath(file_path, self.documents_folder)
                    
                    # Check if already processed
                    exists = await self._document_exists(source_path)
                    if not exists and file_path not in processed_files:
                        new_files.append(file_path)
                
                # Process new files
                if new_files:
                    logger.info(f"\n📁 Found {len(new_files)} new file(s) to process")
                    for file_path in new_files:
                        try:
                            logger.info(f"🚀 Auto-ingesting: {os.path.basename(file_path)}")
                            result = await self._ingest_single_document(file_path)
                            
                            if result.document_id:
                                processed_files.add(file_path)
                                logger.info(f"✅ Successfully ingested: {os.path.basename(file_path)} "
                                          f"({result.chunks_created} chunks)")
                            else:
                                logger.warning(f"⚠️  Failed to ingest: {os.path.basename(file_path)}")
                        except Exception as e:
                            logger.error(f"❌ Error ingesting {file_path}: {e}")
                
                # Show status periodically
                if (datetime.now() - last_status_time).total_seconds() >= status_interval:
                    await self._print_status()
                    last_status_time = datetime.now()
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("\n\n🛑 Stopping file watcher...")
            await self._print_status()
            logger.info("✅ File watcher stopped")
    
    async def _print_status(self):
        """Print current status."""
        try:
            # Count documents in database
            async with db_pool.acquire() as conn:
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
            
            logger.info("\n" + "="*70)
            logger.info("📊 CURRENT STATUS")
            logger.info("="*70)
            logger.info(f"📄 Documents in database: {doc_count}")
            logger.info(f"📦 Total chunks: {chunk_count}")
            logger.info(f"📂 Watching folder: {self.documents_folder}")
            logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*70 + "\n")
        except Exception as e:
            logger.warning(f"Could not get status: {e}")


async def main():
    """Main function for running ingestion."""
    parser = argparse.ArgumentParser(description="Ingest documents into vector DB and knowledge graph")
    parser.add_argument("--documents", "-d", default="documents", help="Documents folder path")
    parser.add_argument("--clean", "-c", action="store_true", help="Clean existing data before ingestion")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size for splitting documents")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap size")
    parser.add_argument("--no-semantic", action="store_true", help="Disable semantic chunking")
    parser.add_argument("--no-entities", action="store_true", help="Disable entity extraction")
    parser.add_argument("--fast", "-f", action="store_true", help="Fast mode: skip knowledge graph building")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch for new files continuously (keeps running)")
    parser.add_argument("--check-interval", type=int, default=5, help="How often to check for new files in watch mode (seconds)")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Reduce Neo4j verbosity (only show WARNING and above)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("neo4j.io").setLevel(logging.WARNING)
    logging.getLogger("neo4j.pool").setLevel(logging.WARNING)
    
    # Create ingestion configuration
    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_semantic_chunking=not args.no_semantic,
        extract_entities=not args.no_entities,
        skip_graph_building=args.fast
    )
    
    # Create and run pipeline
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=args.clean
    )
    
    def progress_callback(current: int, total: int):
        percentage = (current / total) * 100
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\r   📊 Progress: [{bar}] {current}/{total} ({percentage:.1f}%)", end='', flush=True)
        if current == total:
            print()  # New line when complete
    
    try:
        # Watch mode: continuously watch for new files
        if args.watch:
            if not WATCHDOG_AVAILABLE:
                logger.error("❌ Watchdog not installed. Install with: pip install watchdog")
                logger.error("   Or run without --watch flag for one-time ingestion")
                sys.exit(1)
            
            # Start watching (handles its own cleanup on KeyboardInterrupt)
            try:
                await pipeline.watch_and_ingest(check_interval=args.check_interval)
            except KeyboardInterrupt:
                logger.info("\n\n🛑 Stopping file watcher...")
                await pipeline._print_status()
                logger.info("✅ File watcher stopped")
            finally:
                await pipeline.close()
        
        else:
            # One-time ingestion mode
            start_time = datetime.now()
            
            results = await pipeline.ingest_documents(progress_callback)
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            # Print summary
            print("\n" + "="*50)
            print("INGESTION SUMMARY")
            print("="*50)
            print(f"Documents processed: {len(results)}")
            print(f"Total chunks created: {sum(r.chunks_created for r in results)}")
            print(f"Total entities extracted: {sum(r.entities_extracted for r in results)}")
            print(f"Total graph episodes: {sum(r.relationships_created for r in results)}")
            print(f"Total errors: {sum(len(r.errors) for r in results)}")
            print(f"Total processing time: {total_time:.2f} seconds")
            print()
            
            # Print individual results
            for result in results:
                status = "✓" if not result.errors else "✗"
                print(f"{status} {result.title}: {result.chunks_created} chunks, {result.entities_extracted} entities")
                
                if result.errors:
                    for error in result.errors:
                        print(f"  Error: {error}")
        
    except KeyboardInterrupt:
        print("\nIngestion interrupted by user")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise
    finally:
        if not args.watch:  # Only close if not in watch mode (watch mode handles its own cleanup)
            await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())