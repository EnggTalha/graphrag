"""
Graph utilities for Neo4j knowledge graph integration.
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncio
import uuid
import httpx

from neo4j import AsyncGraphDatabase, AsyncDriver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

from .providers import get_embedding_client


async def extract_entities_with_llm(
    content: str, 
    llm_base_url: str = "http://localhost:11434",
    llm_model: str = "qwen3:0.6b",
    max_retries: int = 2,
    initial_timeout: float = 8.0
) -> List[Dict[str, str]]:
    """
    Extract entities and relationships from content using Qwen LLM.
    
    Args:
        content: Text content to extract entities from
        llm_base_url: Ollama base URL
        llm_model: Model name
        max_retries: Maximum number of retries for LLM calls
        initial_timeout: Initial timeout for LLM calls (in seconds)
    
    Returns:
        List of extracted entities with types
    """
    # Truncate content if too long
    max_content_length = 2000
    truncated_content = content[:max_content_length] if len(content) > max_content_length else content
    
    prompt = f"""/no_think
Extract entities (organizations, regulations, rules, laws, concepts, terms) from the following text.
Return ONLY a JSON array of objects with "name" and "type" keys.
Types should be one of: ORGANIZATION, REGULATION, LAW, RULE, CONCEPT, TERM, PERSON, FINANCIAL_INSTRUMENT, PROCEDURE.

Text:
{truncated_content}

Return ONLY valid JSON array, nothing else:"""

    attempt = 0
    timeout = initial_timeout

    while attempt <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{llm_base_url}/api/generate",
                    json={
                        "model": llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 500
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "")
                    
                    # Try to extract JSON from response
                    json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
                    if json_match:
                        try:
                            entities = json.loads(json_match.group())
                            # Validate and clean entities
                            valid_entities = []
                            for e in entities:
                                if isinstance(e, dict) and "name" in e and "type" in e:
                                    name = str(e["name"]).strip()[:100]  # Limit name length
                                    entity_type = str(e["type"]).upper().strip()[:50]
                                    if name and len(name) > 1:
                                        valid_entities.append({"name": name, "type": entity_type})
                            return valid_entities[:20]  # Limit to 20 entities per chunk
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            logger.warning(f"Entity extraction attempt {attempt + 1} failed: {e}")
            attempt += 1
            timeout *= 2  # Exponential backoff

    # Fallback: simple regex-based extraction for key terms
    logger.warning("All LLM attempts failed. Falling back to regex-based extraction.")
    return extract_entities_simple(truncated_content)


def extract_entities_simple(content: str) -> List[Dict[str, str]]:
    """
    Simple regex-based entity extraction as fallback.
    
    Args:
        content: Text content
    
    Returns:
        List of entities
    """
    entities = []
    
    # Common regulatory patterns
    patterns = [
        (r'\b(FINRA|SEC|NYSE|NASDAQ|MSRB|CFTC|OCC|FDIC|Federal Reserve)\b', 'ORGANIZATION'),
        (r'\b(Rule\s+\d+[a-zA-Z\-\.]*\d*)\b', 'RULE'),
        (r'\b(Section\s+\d+[a-zA-Z]*)\b', 'LAW'),
        (r'\b(Regulation\s+[A-Z]+)\b', 'REGULATION'),
        (r'\b(Exchange\s+Act|Securities\s+Act|Dodd-Frank|Sarbanes-Oxley)\b', 'LAW'),
        (r'\b(Form\s+[A-Z0-9\-]+)\b', 'REGULATION'),
        (r'\b(NMS|ATS|SRO|BD|RIA|IAR)\b', 'CONCEPT'),
    ]
    
    seen = set()
    for pattern, entity_type in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            name = match.strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                entities.append({"name": name, "type": entity_type})
    
    return entities[:15]  # Limit entities


class Neo4jGraphClient:
    """Custom Neo4j knowledge graph client using SentenceTransformer and Qwen."""
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None
    ):
        """
        Initialize Neo4j graph client.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        # Neo4j configuration
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        
        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD environment variable not set")
        
        # LLM configuration
        self.llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.llm_choice = os.getenv("LLM_CHOICE", "qwen3:0.6b")
        
        # Embedding configuration
        self.embedding_model = 'all-MiniLM-L6-v2'
        self.embedding_dimensions = 384  # Dimension for MiniLM embeddings
        
        self.driver: Optional[AsyncDriver] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Neo4j connection and create constraints."""
        if self._initialized:
            return

        try:
            # Create async driver
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            
            # Create constraints and indices
            await self._create_indices_and_constraints()
            
            self._initialized = True
            logger.info("Neo4j graph client initialized successfully.")

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j graph client: {e}")
            raise
    
    async def _create_indices_and_constraints(self):
        """Create necessary indices and constraints."""
        try:
            async with self.driver.session() as session:
                # Create index on Entity nodes
                await session.run(
                    "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)"
                )
                # Create index on Document nodes
                await session.run(
                    "CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)"
                )
                logger.info("Indices and constraints created successfully.")
        except Exception as e:
            logger.warning(f"Failed to create indices: {e}")
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            self.driver = None
            self._initialized = False
            logger.info("Neo4j connection closed")
    
    async def add_episode(
        self,
        episode_id: str,
        content: str,
        source: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add an episode (document chunk) to the knowledge graph.
        Extracts entities and creates relationships.
        
        Args:
            episode_id: Unique episode identifier
            content: Episode content
            source: Source of the content
            timestamp: Episode timestamp
            metadata: Additional metadata
        """
        if not self._initialized:
            await self.initialize()
        
        episode_timestamp = timestamp or datetime.now(timezone.utc)
        
        try:
            # Extract entities from content
            entities = await extract_entities_with_llm(
                content, 
                self.llm_base_url, 
                self.llm_choice
            )
            
            async with self.driver.session() as session:
                # Create Episode node
                embedding = await self.generate_embedding(content)
                await session.run(
                    """
                    MERGE (e:Episode {id: $id})
                    SET e.content = $content,
                        e.source = $source,
                        e.timestamp = $timestamp,
                        e.metadata = $metadata,
                        e.embedding = $embedding
                    """,
                    id=episode_id,
                    content=content,
                    source=source,
                    timestamp=episode_timestamp.isoformat(),
                    metadata=json.dumps(metadata or {}),
                    embedding=embedding
                )
                
                # Create Entity nodes and relationships
                for entity in entities:
                    entity_name = entity.get("name", "")
                    entity_type = entity.get("type", "CONCEPT")
                    
                    if entity_name:
                        # Create Entity node if it doesn't exist
                        await session.run(
                            """
                            MERGE (ent:Entity {name: $name})
                            ON CREATE SET ent.type = $type, ent.created_at = $created_at
                            ON MATCH SET ent.mention_count = COALESCE(ent.mention_count, 0) + 1
                            """,
                            name=entity_name,
                            type=entity_type,
                            created_at=episode_timestamp.isoformat()
                        )
                        
                        # Create MENTIONS relationship between Episode and Entity
                        await session.run(
                            """
                            MATCH (ep:Episode {id: $episode_id})
                            MATCH (ent:Entity {name: $entity_name})
                            MERGE (ep)-[r:MENTIONS]->(ent)
                            ON CREATE SET r.created_at = $created_at
                            """,
                            episode_id=episode_id,
                            entity_name=entity_name,
                            created_at=episode_timestamp.isoformat()
                        )
                
                # Create RELATED_TO relationships between entities in same episode
                if len(entities) > 1:
                    for i, ent1 in enumerate(entities):
                        for ent2 in entities[i+1:]:
                            name1 = ent1.get("name", "")
                            name2 = ent2.get("name", "")
                            if name1 and name2:
                                await session.run(
                                    """
                                    MATCH (e1:Entity {name: $name1})
                                    MATCH (e2:Entity {name: $name2})
                                    MERGE (e1)-[r:RELATED_TO]-(e2)
                                    ON CREATE SET r.co_occurrence = 1
                                    ON MATCH SET r.co_occurrence = r.co_occurrence + 1
                                    """,
                                    name1=name1,
                                    name2=name2
                                )
                
            entity_count = len(entities)
            if entity_count > 0:
                logger.debug(f"Added episode {episode_id} with {entity_count} entities")
            else:
                logger.debug(f"Added episode {episode_id} (no entities extracted)")
                
        except Exception as e:
            logger.error(f"Failed to add episode to graph: {e}")
            raise
    
    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge graph using embeddings.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            Search results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate embedding for the query
            query_embedding = await self.generate_embedding(query)
            
            async with self.driver.session() as session:
                # Simple search - find episodes with similar content
                results = await session.run(
                    """
                    MATCH (e:Episode)
                    RETURN e.id as id, e.content as content, e.source as source,
                           e.timestamp as timestamp
                    LIMIT $limit
                    """,
                    limit=limit
                )
                
                return [dict(record) for record in results]
            
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []
    
    async def get_related_entities(
        self,
        entity_name: str,
        relationship_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get entities related to a given entity.
        
        Args:
            entity_name: Name of the entity
            relationship_types: Types of relationships to follow
            depth: Maximum depth to traverse
        
        Returns:
            Related entities and relationships
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.driver.session() as session:
                # Find entities related to the given entity
                results = await session.run(
                    """
                    MATCH (e:Entity {name: $name})-[*1..$depth]-(related:Entity)
                    RETURN DISTINCT related.name as entity, COUNT(*) as connections
                    """,
                    name=entity_name,
                    depth=depth
                )
                
                related_entities = [dict(record) for record in results]
                
                return {
                    "central_entity": entity_name,
                    "related_entities": related_entities,
                    "search_method": "neo4j_graph_traversal"
                }
        except Exception as e:
            logger.error(f"Failed to get related entities: {e}")
            return {
                "central_entity": entity_name,
                "related_entities": [],
                "error": str(e)
            }
    
    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of facts for an entity.
        
        Args:
            entity_name: Name of the entity
            start_date: Start of time range
            end_date: End of time range
        
        Returns:
            Timeline of facts
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.driver.session() as session:
                # Get episodes related to the entity ordered by timestamp
                results = await session.run(
                    """
                    MATCH (e:Entity {name: $name})<-[:MENTIONS]-(ep:Episode)
                    RETURN ep.id as id, ep.content as content, ep.timestamp as timestamp
                    ORDER BY ep.timestamp DESC
                    """,
                    name=entity_name
                )
                
                timeline = [dict(record) for record in results]
                return timeline
        except Exception as e:
            logger.error(f"Failed to get entity timeline: {e}")
            return []
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get basic statistics about the knowledge graph.
        
        Returns:
            Graph statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.driver.session() as session:
                # Get node counts by label
                node_result = await session.run(
                    """
                    CALL db.labels() YIELD label
                    CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value
                    RETURN label, value.count as count
                    """
                )
                
                nodes_data = []
                try:
                    async for record in node_result:
                        nodes_data.append({"label": record["label"], "count": record["count"]})
                except:
                    # Fallback if APOC not available
                    node_result2 = await session.run(
                        """
                        MATCH (n)
                        RETURN labels(n)[0] as label, count(n) as count
                        """
                    )
                    async for record in node_result2:
                        nodes_data.append({"label": record["label"], "count": record["count"]})
                
                # Get relationship counts
                rel_result = await session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN type(r) as relationship, COUNT(*) as count
                    """
                )
                
                rels_data = []
                async for record in rel_result:
                    rels_data.append({"relationship": record["relationship"], "count": record["count"]})
                
                # Get total counts
                totals_result = await session.run(
                    """
                    MATCH (n) WITH count(n) as nodes
                    MATCH ()-[r]->() 
                    RETURN nodes, count(r) as relationships
                    """
                )
                
                totals = {"nodes": 0, "relationships": 0}
                async for record in totals_result:
                    totals = {"nodes": record["nodes"], "relationships": record["relationships"]}
                
                return {
                    "neo4j_initialized": True,
                    "total_nodes": totals["nodes"],
                    "total_relationships": totals["relationships"],
                    "node_labels": nodes_data,
                    "relationship_types": rels_data
                }
        except Exception as e:
            logger.warning(f"Failed to get graph statistics: {e}")
            return {
                "neo4j_initialized": False,
                "error": str(e)
            }
    
    async def clear_graph(self):
        """Clear all data from the graph (USE WITH CAUTION)."""
        if not self._initialized:
            await self.initialize()
        
        try:
            async with self.driver.session() as session:
                await session.run("MATCH (n) DETACH DELETE n")
                logger.warning("Cleared all data from knowledge graph")
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using SentenceTransformer.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # SentenceTransformer.encode is CPU-bound and blocking; offload to thread
        try:
            client = get_embedding_client()
            embedding = await asyncio.to_thread(client.encode, text)
            # embedding may be a numpy array
            try:
                return embedding.tolist()
            except Exception:
                return list(embedding)
        except Exception as e:
            logger.warning(f"Embedding generation failed (fallback to zeros): {e}")
            return [0.0] * self.embedding_dimensions


# Global Neo4j graph client instance
graph_client = Neo4jGraphClient()


async def initialize_graph():
    """Initialize graph client."""
    await graph_client.initialize()


async def close_graph():
    """Close graph client."""
    await graph_client.close()


# Convenience functions for common operations
async def add_to_knowledge_graph(
    content: str,
    source: str,
    episode_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Add content to the knowledge graph.
    
    Args:
        content: Content to add
        source: Source of the content
        episode_id: Optional episode ID
        metadata: Optional metadata
    
    Returns:
        Episode ID
    """
    if not episode_id:
        episode_id = f"episode_{uuid.uuid4().hex[:8]}"
    
    await graph_client.add_episode(
        episode_id=episode_id,
        content=content,
        source=source,
        metadata=metadata
    )
    
    return episode_id


async def search_knowledge_graph(
    query: str
) -> List[Dict[str, Any]]:
    """
    Search the knowledge graph.
    
    Args:
        query: Search query
    
    Returns:
        Search results
    """
    return await graph_client.search(query)


async def get_entity_relationships(
    entity: str,
    depth: int = 2
) -> Dict[str, Any]:
    """
    Get relationships for an entity.
    
    Args:
        entity: Entity name
        depth: Maximum traversal depth
    
    Returns:
        Entity relationships
    """
    return await graph_client.get_related_entities(entity, depth=depth)


async def test_graph_connection() -> bool:
    """
    Test graph database connection.
    
    Returns:
        True if connection successful
    """
    try:
        await graph_client.initialize()
        stats = await graph_client.get_graph_statistics()
        logger.info(f"Graph connection successful. Stats: {stats}")
        return True
    except Exception as e:
        logger.error(f"Graph connection test failed: {e}")
        return False