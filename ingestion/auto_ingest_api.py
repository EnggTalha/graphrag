"""
Auto-Ingestion API Service
Watches for new files and automatically ingests them.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# File watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("watchdog not installed. Install with: pip install watchdog")

from .ingest import DocumentIngestionPipeline
from ..agent.models import IngestionConfig

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Reduce Neo4j verbosity
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neo4j.io").setLevel(logging.WARNING)

# FastAPI app
app = FastAPI(
    title="Auto-Ingestion API",
    description="Automatically ingests new documents from watched folder",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
ingestion_pipeline: Optional[DocumentIngestionPipeline] = None
observer: Optional[Observer] = None
watch_folder: str = "data"
is_watching: bool = False
ingestion_queue: asyncio.Queue = asyncio.Queue()
processing_files: set = set()
ingestion_history: List[Dict[str, Any]] = []


class FileWatcher(FileSystemEventHandler):
    """File system event handler for auto-ingestion."""
    
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop
        self.supported_extensions = {'.txt', '.md', '.markdown', '.pdf', '.xls', '.xlsx', '.csv', '.doc', '.docx'}
        self.debounce_time = {}  # Track file modifications to avoid duplicate events
        
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported for ingestion."""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def _add_to_queue(self, event_type: str, file_path: str):
        """Add file event to queue (thread-safe)."""
        try:
            # Schedule coroutine in the event loop
            asyncio.run_coroutine_threadsafe(
                self.queue.put((event_type, file_path)),
                self.loop
            )
        except Exception as e:
            logger.error(f"Failed to add {file_path} to queue: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self.is_supported_file(event.src_path):
            logger.info(f"📁 New file detected: {event.src_path}")
            self._add_to_queue("created", event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self.is_supported_file(event.src_path):
            # Debounce: only process if file hasn't been modified recently
            file_path = event.src_path
            current_time = datetime.now().timestamp()
            
            # Skip if we just processed this file (within last 5 seconds)
            if file_path in self.debounce_time:
                if current_time - self.debounce_time[file_path] < 5:
                    return
            
            self.debounce_time[file_path] = current_time
            logger.info(f"📝 File modified: {file_path}")
            self._add_to_queue("modified", file_path)


async def process_ingestion_queue():
    """Background task to process ingestion queue."""
    global ingestion_pipeline, processing_files
    
    logger.info("🔄 Ingestion queue processor started")
    
    while True:
        try:
            # Wait for file event
            event_type, file_path = await asyncio.wait_for(
                ingestion_queue.get(),
                timeout=1.0
            )
            
            # Skip if already processing
            if file_path in processing_files:
                logger.debug(f"⏭️  Skipping {file_path} (already processing)")
                continue
            
            # Skip if file doesn't exist
            if not os.path.exists(file_path):
                logger.warning(f"⚠️  File no longer exists: {file_path}")
                continue
            
            # Add to processing set
            processing_files.add(file_path)
            
            try:
                logger.info(f"🚀 Auto-ingesting: {os.path.basename(file_path)}")
                
                # Initialize pipeline if needed
                if ingestion_pipeline is None:
                    config = IngestionConfig()
                    ingestion_pipeline = DocumentIngestionPipeline(
                        config=config,
                        documents_folder=os.path.dirname(file_path) or ".",
                        clean_before_ingest=False
                    )
                    await ingestion_pipeline.initialize()
                
                # Ingest the file
                start_time = datetime.now()
                result = await ingestion_pipeline._ingest_single_document(file_path)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Record in history
                ingestion_history.append({
                    "file_path": file_path,
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "chunks_created": result.chunks_created,
                    "entities_extracted": result.entities_extracted,
                    "relationships_created": result.relationships_created,
                    "success": len(result.errors) == 0,
                    "errors": result.errors
                })
                
                # Keep only last 100 entries
                if len(ingestion_history) > 100:
                    ingestion_history.pop(0)
                
                if result.errors:
                    logger.error(f"❌ Failed to ingest {file_path}: {result.errors}")
                else:
                    logger.info(f"✅ Auto-ingested: {os.path.basename(file_path)} "
                              f"({result.chunks_created} chunks, {duration:.1f}s)")
                
            except Exception as e:
                logger.error(f"❌ Error ingesting {file_path}: {e}")
                ingestion_history.append({
                    "file_path": file_path,
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "errors": [str(e)]
                })
            finally:
                # Remove from processing set
                processing_files.discard(file_path)
                
        except asyncio.TimeoutError:
            # Timeout is expected, just continue
            continue
        except Exception as e:
            logger.error(f"❌ Error in ingestion queue processor: {e}")
            await asyncio.sleep(1)


def start_file_watcher(folder: str):
    """Start watching folder for new files."""
    global observer, is_watching
    
    if not WATCHDOG_AVAILABLE:
        logger.error("❌ watchdog library not installed. Install with: pip install watchdog")
        return False
    
    if is_watching:
        logger.warning("⚠️  File watcher already running")
        return True
    
    if not os.path.exists(folder):
        logger.error(f"❌ Watch folder does not exist: {folder}")
        return False
    
    try:
        # Get the event loop for thread-safe queue operations
        loop = asyncio.get_event_loop()
        event_handler = FileWatcher(ingestion_queue, loop)
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=True)
        observer.start()
        is_watching = True
        logger.info(f"👀 Started watching folder: {folder}")
        logger.info(f"   Supported formats: .txt, .md, .pdf, .xls, .xlsx, .csv, .doc, .docx")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start file watcher: {e}")
        return False


def stop_file_watcher():
    """Stop watching folder."""
    global observer, is_watching
    
    if observer and is_watching:
        observer.stop()
        observer.join()
        is_watching = False
        logger.info("🛑 Stopped file watcher")
        return True
    return False


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global ingestion_pipeline
    
    logger.info("="*70)
    logger.info("🚀 AUTO-INGESTION API STARTING")
    logger.info("="*70)
    
    # Initialize ingestion pipeline
    try:
        config = IngestionConfig()
        ingestion_pipeline = DocumentIngestionPipeline(
            config=config,
            documents_folder=watch_folder,
            clean_before_ingest=False
        )
        await ingestion_pipeline.initialize()
        logger.info("✅ Ingestion pipeline initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize ingestion pipeline: {e}")
    
    # Start file watcher
    if start_file_watcher(watch_folder):
        logger.info("✅ File watcher started")
    else:
        logger.warning("⚠️  File watcher not started")
    
    # Start background ingestion processor
    asyncio.create_task(process_ingestion_queue())
    logger.info("✅ Ingestion queue processor started")
    
    logger.info("="*70)
    logger.info("✅ AUTO-INGESTION API READY")
    logger.info(f"   Watching: {watch_folder}")
    logger.info(f"   API: http://localhost:8059")
    logger.info("="*70)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global ingestion_pipeline
    
    logger.info("🛑 Shutting down auto-ingestion API...")
    
    stop_file_watcher()
    
    if ingestion_pipeline:
        await ingestion_pipeline.close()
    
    logger.info("✅ Shutdown complete")


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Auto-Ingestion API",
        "status": "running",
        "watching": is_watching,
        "watch_folder": watch_folder,
        "processing": len(processing_files),
        "queue_size": ingestion_queue.qsize()
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "watching": is_watching,
        "pipeline_initialized": ingestion_pipeline is not None,
        "processing_files": len(processing_files),
        "queue_size": ingestion_queue.qsize()
    }


@app.get("/status")
async def status():
    """Get detailed status."""
    return {
        "watching": is_watching,
        "watch_folder": watch_folder,
        "pipeline_initialized": ingestion_pipeline is not None,
        "processing_files": list(processing_files),
        "queue_size": ingestion_queue.qsize(),
        "recent_ingestions": ingestion_history[-10:] if ingestion_history else []
    }


@app.post("/watch/start")
async def start_watch(folder: Optional[str] = None):
    """Start watching a folder."""
    global watch_folder
    
    if folder:
        watch_folder = folder
    
    if start_file_watcher(watch_folder):
        return {"status": "started", "folder": watch_folder}
    else:
        raise HTTPException(status_code=500, detail="Failed to start file watcher")


@app.post("/watch/stop")
async def stop_watch():
    """Stop watching folder."""
    if stop_file_watcher():
        return {"status": "stopped"}
    else:
        return {"status": "not_watching"}


@app.post("/ingest/file")
async def ingest_file(file_path: str, background_tasks: BackgroundTasks):
    """Manually trigger ingestion of a specific file."""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    if file_path in processing_files:
        raise HTTPException(status_code=409, detail="File is already being processed")
    
    # Add to queue
    await ingestion_queue.put(("manual", file_path))
    
    return {
        "status": "queued",
        "file": file_path,
        "queue_position": ingestion_queue.qsize()
    }


@app.post("/ingest/folder")
async def ingest_folder(folder: Optional[str] = None, background_tasks: BackgroundTasks = None):
    """Manually trigger ingestion of all files in a folder."""
    target_folder = folder or watch_folder
    
    if not os.path.exists(target_folder):
        raise HTTPException(status_code=404, detail=f"Folder not found: {target_folder}")
    
    # Find all supported files
    supported_extensions = {'.txt', '.md', '.markdown', '.pdf', '.xls', '.xlsx', '.csv'}
    files = []
    for ext in supported_extensions:
        files.extend(Path(target_folder).rglob(f"*{ext}"))
    
    files = [str(f) for f in files if f.is_file()]
    
    if not files:
        return {"status": "no_files", "folder": target_folder, "files_found": 0}
    
    # Add all files to queue
    for file_path in files:
        await ingestion_queue.put(("manual", file_path))
    
    return {
        "status": "queued",
        "folder": target_folder,
        "files_found": len(files),
        "queue_size": ingestion_queue.qsize()
    }


@app.get("/history")
async def get_history(limit: int = 50):
    """Get ingestion history."""
    return {
        "total": len(ingestion_history),
        "history": ingestion_history[-limit:]
    }


@app.get("/history/stats")
async def get_history_stats():
    """Get ingestion statistics."""
    if not ingestion_history:
        return {"total": 0, "stats": {}}
    
    successful = sum(1 for h in ingestion_history if h.get("success", False))
    failed = len(ingestion_history) - successful
    total_chunks = sum(h.get("chunks_created", 0) for h in ingestion_history)
    total_entities = sum(h.get("entities_extracted", 0) for h in ingestion_history)
    total_relationships = sum(h.get("relationships_created", 0) for h in ingestion_history)
    
    return {
        "total_ingestions": len(ingestion_history),
        "successful": successful,
        "failed": failed,
        "total_chunks": total_chunks,
        "total_entities": total_entities,
        "total_relationships": total_relationships
    }


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("AUTO_INGEST_PORT", 8059))
    
    uvicorn.run(
        "ingestion.auto_ingest_api:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )

