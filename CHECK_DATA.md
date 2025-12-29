# 📊 How to Check Your Ingested Data

This guide shows you where your data is stored and how to verify it after ingestion.

## 📍 Where Data is Stored

Your ingested data is stored in **two places**:

### 1. **PostgreSQL Database** (Vector Embeddings & Chunks)
- **Location**: Docker container `agentic-rag-postgres`
- **Database**: `agentic_rag`
- **Tables**:
  - `documents` - Original documents
  - `chunks` - Text chunks with vector embeddings
  - `sessions` - Chat sessions
  - `messages` - Chat messages

### 2. **Neo4j Database** (Knowledge Graph)
- **Location**: Docker container `agentic-rag-neo4j`
- **Database**: Neo4j graph database
- **Contains**: Entities, relationships, and graph connections

### 3. **Docker Volumes** (Persistent Storage)
- **PostgreSQL data**: `postgres_data` volume
- **Neo4j data**: `neo4j_data` and `neo4j_logs` volumes
- **Physical location**: Managed by Docker (usually `/var/lib/docker/volumes/`)

---

## 🔍 How to Check PostgreSQL Data

### Method 1: Using Docker Exec (Quick Check)

```bash
# Connect to PostgreSQL container
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag

# Once inside psql, run these queries:

# Count documents
SELECT COUNT(*) FROM documents;

# List all documents
SELECT id, title, source, created_at FROM documents ORDER BY created_at DESC;

# Count chunks
SELECT COUNT(*) FROM chunks;

# Count chunks per document
SELECT d.title, COUNT(c.id) as chunk_count 
FROM documents d 
LEFT JOIN chunks c ON d.id = c.document_id 
GROUP BY d.title 
ORDER BY chunk_count DESC;

# View sample chunks
SELECT c.id, c.chunk_index, LEFT(c.content, 100) as content_preview, 
       d.title as document_title
FROM chunks c
JOIN documents d ON c.document_id = d.id
ORDER BY d.title, c.chunk_index
LIMIT 10;

# Check if embeddings exist
SELECT COUNT(*) as chunks_with_embeddings 
FROM chunks 
WHERE embedding IS NOT NULL;

# Exit psql
\q
```

### Method 2: Using Python Script

Create a file `check_data.py`:

```python
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_data():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    # Count documents
    doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
    print(f"📄 Documents: {doc_count}")
    
    # Count chunks
    chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
    print(f"📦 Chunks: {chunk_count}")
    
    # Count chunks with embeddings
    embedding_count = await conn.fetchval(
        "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL"
    )
    print(f"🔢 Chunks with embeddings: {embedding_count}")
    
    # List documents
    print("\n📋 Documents:")
    docs = await conn.fetch("""
        SELECT title, source, created_at, 
               (SELECT COUNT(*) FROM chunks WHERE document_id = documents.id) as chunk_count
        FROM documents 
        ORDER BY created_at DESC
    """)
    for doc in docs:
        print(f"  - {doc['title']} ({doc['chunk_count']} chunks) - {doc['source']}")
    
    # Sample chunks
    print("\n📝 Sample Chunks:")
    chunks = await conn.fetch("""
        SELECT d.title, c.chunk_index, LEFT(c.content, 80) as preview
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY d.title, c.chunk_index
        LIMIT 5
    """)
    for chunk in chunks:
        print(f"  [{chunk['title']}] Chunk {chunk['chunk_index']}: {chunk['preview']}...")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_data())
```

Run it:
```bash
python check_data.py
```

### Method 3: Quick One-Liners

```bash
# Count documents
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) FROM documents;"

# Count chunks
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) FROM chunks;"

# List document titles
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT title, source FROM documents;"

# Check embeddings
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;"
```

---

## 🕸️ How to Check Neo4j Data

### Method 1: Neo4j Browser (Web Interface)

1. **Open Neo4j Browser**:
   ```bash
   # Open in your browser
   http://localhost:7474
   ```

2. **Login**:
   - Username: `neo4j`
   - Password: `neo4j_password_change_me` (or whatever you set in docker-compose.yml)

3. **Run Cypher Queries**:

```cypher
// Count all nodes
MATCH (n) RETURN count(n) as total_nodes;

// Count all relationships
MATCH ()-[r]->() RETURN count(r) as total_relationships;

// View all node types
MATCH (n) RETURN labels(n) as node_type, count(*) as count;

// View all relationship types
MATCH ()-[r]->() RETURN type(r) as relationship_type, count(*) as count;

// View sample nodes
MATCH (n) RETURN n LIMIT 25;

// View sample relationships
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25;

// Find specific entity (example)
MATCH (n) WHERE n.name CONTAINS 'project' RETURN n LIMIT 10;
```

### Method 2: Using Cypher Shell (Command Line)

```bash
# Connect to Neo4j via cypher-shell
docker exec -it agentic-rag-neo4j cypher-shell -u neo4j -p neo4j_password_change_me

# Then run queries:
# MATCH (n) RETURN count(n);
# MATCH ()-[r]->() RETURN count(r);
# MATCH (n) RETURN n LIMIT 10;
```

### Method 3: Python Script

```python
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def check_neo4j():
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()["count"]
        print(f"🕸️  Nodes: {node_count}")
        
        # Count relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        print(f"🔗 Relationships: {rel_count}")
        
        # Node types
        result = session.run("""
            MATCH (n) 
            RETURN labels(n)[0] as label, count(*) as count 
            ORDER BY count DESC
        """)
        print("\n📊 Node Types:")
        for record in result:
            print(f"  - {record['label']}: {record['count']}")
        
        # Sample nodes
        result = session.run("MATCH (n) RETURN n LIMIT 5")
        print("\n🔍 Sample Nodes:")
        for record in result:
            print(f"  {record['n']}")

    driver.close()

if __name__ == "__main__":
    check_neo4j()
```

---

## 📦 Check Docker Volumes

### View Volume Information

```bash
# List all volumes
docker volume ls

# Inspect PostgreSQL volume
docker volume inspect graph_rag_postgres_data

# Inspect Neo4j volumes
docker volume inspect graph_rag_neo4j_data
docker volume inspect graph_rag_neo4j_logs

# Check volume size (requires du)
docker run --rm -v graph_rag_postgres_data:/data alpine sh -c "du -sh /data"
docker run --rm -v graph_rag_neo4j_data:/data alpine sh -c "du -sh /data"
```

### Find Physical Location

```bash
# Find where Docker stores volumes
docker volume inspect graph_rag_postgres_data | grep Mountpoint

# Usually located at:
# /var/lib/docker/volumes/graph_rag_postgres_data/_data
# /var/lib/docker/volumes/graph_rag_neo4j_data/_data
```

---

## ✅ Quick Verification Checklist

After running ingestion, verify everything worked:

```bash
# 1. Check PostgreSQL - Documents
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) as documents FROM documents;"

# 2. Check PostgreSQL - Chunks
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) as chunks FROM chunks;"

# 3. Check PostgreSQL - Embeddings
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT COUNT(*) as chunks_with_embeddings FROM chunks WHERE embedding IS NOT NULL;"

# 4. Check Neo4j - Nodes (via browser or cypher-shell)
# Open http://localhost:7474 and run: MATCH (n) RETURN count(n);

# 5. Check Neo4j - Relationships
# In Neo4j browser: MATCH ()-[r]->() RETURN count(r);
```

**Expected Results:**
- Documents: Should match number of files in `data/` folder
- Chunks: Should be > 0 (depends on document size)
- Embeddings: Should equal chunks count (if ingestion completed)
- Neo4j nodes: Should be > 0 (if knowledge graph was built)
- Neo4j relationships: Should be > 0 (if knowledge graph was built)

---

## 🗑️ How to Clear Data

If you need to start fresh:

```bash
# Clear PostgreSQL data
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "TRUNCATE chunks, documents CASCADE;"

# Clear Neo4j data (via browser or cypher-shell)
# In Neo4j browser: MATCH (n) DETACH DELETE n;

# Or completely reset volumes (WARNING: Deletes all data!)
docker compose down -v
docker compose up -d
python init_database.py
```

---

## 📊 Data Storage Summary

| Component | Location | What's Stored |
|-----------|----------|---------------|
| **Documents** | PostgreSQL `documents` table | Original document content, metadata |
| **Chunks** | PostgreSQL `chunks` table | Text chunks with vector embeddings (1536 dimensions) |
| **Knowledge Graph** | Neo4j database | Entities, relationships, graph connections |
| **Persistent Storage** | Docker volumes | All database files (survives container restarts) |

---

## 💡 Tips

1. **Backup Data**: Docker volumes persist data even if containers are stopped
2. **Check Logs**: If ingestion fails, check logs: `docker logs agentic-rag-postgres`
3. **Neo4j Browser**: Best way to visualize the knowledge graph
4. **Performance**: Large documents create many chunks - this is normal!

---

**Need help?** Check the ingestion logs or verify your `.env` file configuration.

