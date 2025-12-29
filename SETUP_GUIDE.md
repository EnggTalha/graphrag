# Real Estate Q/A RAG Knowledge Graph - Setup Guide

## Overview
This system provides an intelligent Q/A interface for your real estate data and meeting minutes using:
- **OpenAI GPT-4o-mini** for LLM responses
- **OpenAI text-embedding-3-small** for vector embeddings
- **PostgreSQL + pgvector** for semantic search
- **Neo4j + Graphiti** for knowledge graph relationships
- **FastAPI** for the API server

## 📁 Your Data
The following documents are ready for ingestion:
- `knowledge_bot_data.txt` (13.3 MB) - Real estate/project data ✅
- `meetings_minutes.txt` (28 KB) - Meeting minutes ✅
- `knowledge_bot_data.xlsx` (20 KB) - Spreadsheet data ✅ **NOW SUPPORTED!**
- `knowledge_bot_doc.pdf` (27 KB) - PDF documentation ✅ **NOW SUPPORTED!**

**✨ NEW:** The system now supports `.txt`, `.md`, `.pdf`, `.xls`, `.xlsx`, and `.csv` files. No conversion needed!

## 🚀 Quick Start

### Step 1: Set Up PostgreSQL Database

You need a PostgreSQL database with pgvector extension. Choose one option:

#### Option A: Cloud Database (Recommended - Easy)
1. Create a free account at [Neon](https://neon.tech)
2. Create a new project
3. Copy your connection string (looks like: `postgresql://user:pass@ep-xxx.aws.neon.tech/dbname`)
4. The pgvector extension is pre-installed on Neon

#### Option B: Local PostgreSQL
1. Install PostgreSQL: https://www.postgresql.org/download/windows/
2. Install pgvector extension:
   ```bash
   # Using pgAdmin or psql
   CREATE EXTENSION vector;
   ```
3. Create a database for the project

### Step 2: Set Up Neo4j

Neo4j is required for the knowledge graph functionality.

#### Option A: Neo4j Desktop (Recommended)
1. Download [Neo4j Desktop](https://neo4j.com/download/)
2. Create a new project
3. Add a local DBMS (database)
4. Set a password (remember this!)
5. Start the DBMS
6. Connection details:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: (what you set)

#### Option B: Neo4j AuraDB (Cloud)
1. Create free account at [Neo4j Aura](https://neo4j.com/cloud/aura/)
2. Create a free instance
3. Save the connection details

### Step 3: Configure Environment Variables

1. **Copy the environment template:**
   ```powershell
   # Create .env file from template
   # Since .env is gitignored, manually create it:
   New-Item -Path ".env" -ItemType File
   notepad .env
   ```

2. **Add your configuration to `.env`:**
   ```env
   # Database Configuration
   DATABASE_URL=postgresql://username:password@your-host:5432/dbname
   
   # Neo4j Configuration
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here
   
   # OpenAI Configuration
   LLM_PROVIDER=openai
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-your-openai-api-key-here
   LLM_CHOICE=gpt-4o-mini
   
   # Embedding Configuration
   EMBEDDING_PROVIDER=openai
   EMBEDDING_BASE_URL=https://api.openai.com/v1
   EMBEDDING_API_KEY=sk-your-openai-api-key-here
   EMBEDDING_MODEL=text-embedding-3-small
   
   # Ingestion Model (same as above for consistency)
   INGESTION_LLM_CHOICE=gpt-4o-mini
   
   # Application
   APP_ENV=development
   LOG_LEVEL=INFO
   APP_PORT=8058
   ```

3. **Get your OpenAI API Key:**
   - Go to https://platform.openai.com/api-keys
   - Create a new secret key
   - Copy and paste into the `.env` file

### Step 4: Install Python Dependencies

```powershell
# Make sure you're in the project directory
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Initialize Database Schema

Run the SQL schema to create tables:

```powershell
# Connect to your PostgreSQL database and run the schema
# Option 1: Using psql command line
psql -d "your_database_url" -f sql/schema.sql

# Option 2: Copy and paste the contents of sql/schema.sql into pgAdmin query tool
```

**Important:** Check `sql/schema.sql` line 31, 67, and 100 - the vector dimensions are set to 1536 (correct for OpenAI text-embedding-3-small).

### Step 6: Ingest Your Documents

Now ingest your real estate data and meeting minutes:

```powershell
# Basic ingestion (recommended first time)
python -m ingestion.ingest --verbose

# With all features (slower but builds complete knowledge graph)
python -m ingestion.ingest --clean --verbose

# Fast mode (skip knowledge graph building for quick testing)
python -m ingestion.ingest --fast --verbose
```

**What happens during ingestion:**
1. Documents are read and chunked intelligently
2. Embeddings are generated using OpenAI
3. Entities (projects, people, properties) are extracted
4. Knowledge graph relationships are built
5. Everything is stored in PostgreSQL and Neo4j

**Note:** Full ingestion with knowledge graph can take 15-30 minutes for large documents.

### Step 7: Start the API Server

```powershell
# Start the FastAPI server
python -m agent.api
```

Server will be available at: http://localhost:8058

### Step 8: Use the CLI Interface

Open a **new terminal** and start the CLI:

```powershell
# Navigate to project directory
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start CLI
python cli.py
```

## 💬 Example Questions to Ask

Once your system is running, try these queries:

### Project Information
- "What projects are mentioned in the meeting minutes?"
- "Tell me about project PRJ-026"
- "What is the status of the Orion Analytics Dashboard?"

### Meeting Minutes
- "What were the key decisions from the November 6th meeting?"
- "Show me all action items from recent meetings"
- "Who attended the GitOps planning meeting?"

### Team & Relationships
- "Who is Kiran Williams and what projects do they own?"
- "What are the relationships between the PMO and Operations departments?"
- "Which team members are working on multiple projects?"

### Property/Real Estate Data
- "What properties are in our database?"
- "Tell me about the escalation process for projects"
- "What runbooks are available for deployments?"

## 🔧 Troubleshooting

### Issue: "No module named 'psycopg2'"
**Solution:** The project uses `asyncpg`, not psycopg2. Make sure you installed from requirements.txt

### Issue: "Connection refused" to PostgreSQL
**Solution:** 
- Check your DATABASE_URL in .env
- Verify your PostgreSQL server is running
- Test connection: `psql -d "your_database_url"`

### Issue: "Connection refused" to Neo4j
**Solution:**
- Start Neo4j Desktop and ensure DBMS is running
- Check NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env
- Default port is 7687

### Issue: OpenAI API errors
**Solution:**
- Verify your API key is correct
- Check you have credits in your OpenAI account
- Ensure no spaces in the API key in .env

### Issue: Ingestion takes too long
**Solution:**
- Use `--fast` flag to skip knowledge graph: `python -m ingestion.ingest --fast`
- Knowledge graph building is computationally expensive but provides better relationship understanding

### Issue: No results from queries
**Solution:**
- Make sure ingestion completed successfully
- Check logs for errors during ingestion
- Verify data is in database: Check pgAdmin or query the `documents` and `chunks` tables

## 📊 Monitoring Your System

### Check API Health
```bash
curl http://localhost:8058/health
```

### View API Documentation
Open in browser: http://localhost:8058/docs

### Check Database
```sql
-- Count documents
SELECT COUNT(*) FROM documents;

-- Count chunks
SELECT COUNT(*) FROM chunks;

-- Recent sessions
SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;
```

### Check Neo4j Graph
Open Neo4j Browser and run:
```cypher
// Count all nodes
MATCH (n) RETURN count(n);

// Show some relationships
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25;
```

## 🎯 Next Steps

1. **Convert PDF and Excel to Text**: Extract text from `knowledge_bot_doc.pdf` and `knowledge_bot_data.xlsx` and save as `.txt` files for ingestion

2. **Customize Chunking**: Adjust chunk size in ingestion command:
   ```powershell
   python -m ingestion.ingest --chunk-size 800 --chunk-overlap 150
   ```

3. **Test Different Models**: Try different OpenAI models by changing `LLM_CHOICE` in .env:
   - `gpt-4o` - More powerful but slower/expensive
   - `gpt-4o-mini` - Fast and cost-effective (recommended)
   - `gpt-3.5-turbo` - Fastest and cheapest

4. **Build a Frontend**: The API is ready - build a React/Vue frontend to make it more user-friendly

5. **Add More Documents**: Drop new `.txt` or `.md` files in the `documents` folder and re-run ingestion

## 🔒 Security Notes

- Never commit `.env` file to git (already in .gitignore)
- Keep your OpenAI API keys secure
- Use environment-specific credentials for production
- Consider using AWS Secrets Manager or Azure Key Vault for production deployments

## 📚 Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic AI](https://ai.pydantic.dev/)

## ✅ You're Ready!

Your Real Estate Q/A RAG system with Knowledge Graph is now set up! The system will intelligently answer questions about your properties, projects, meetings, and organizational data using both semantic search and relationship understanding.

Happy querying! 🚀

