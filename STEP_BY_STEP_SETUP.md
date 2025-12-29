# Step-by-Step Guide: Setting Up Local PostgreSQL with pgvector

Follow these steps in order to get your local database running.

## Prerequisites Check

### Step 1: Verify Docker is Installed

Open PowerShell and run:
```powershell
docker --version
```

**If Docker is NOT installed:**
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install and restart your computer
3. Make sure Docker Desktop is running (you'll see the Docker icon in your system tray)

### Step 2: Verify Docker is Running

```powershell
docker ps
```

You should see a table (even if empty). If you get an error, start Docker Desktop.

---

## Database Setup

### Step 3: Start PostgreSQL Container

Navigate to your project directory and run:
```powershell
docker compose up -d
```

**What this does:**
- Downloads the PostgreSQL image with pgvector (first time only, ~200MB)
- Creates and starts a container named `agentic-rag-postgres`
- Exposes PostgreSQL on port 5432

**Expected output:**
```
[+] Running 2/2
 ✔ Network agentic-rag-knowledge-graph_default    Created
 ✔ Container agentic-rag-postgres                 Started
```

### Step 4: Wait for Database to be Ready

Wait about 10-15 seconds, then check if it's running:
```powershell
docker ps
```

You should see `agentic-rag-postgres` in the list.

Check the logs to see when it's ready:
```powershell
docker logs agentic-rag-postgres
```

Look for: `"database system is ready to accept connections"`

### Step 5: Verify pgvector Extension

Test that pgvector is available:
```powershell
docker exec agentic-rag-postgres psql -U postgres -d agentic_rag -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

You should see:
```
CREATE EXTENSION
 extname
---------
 vector
(1 row)
```

---

## Configuration

### Step 6: Create .env File

Create a file named `.env` in your project root directory.

**Option A: Using PowerShell**
```powershell
@"
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag

# Neo4j Configuration (if you're using it)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM Provider Configuration
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key
LLM_CHOICE=gpt-4.1-mini

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-api-key
EMBEDDING_MODEL=text-embedding-3-small

# Ingestion Configuration
INGESTION_LLM_CHOICE=gpt-4.1-nano

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
APP_PORT=8058
"@ | Out-File -FilePath .env -Encoding utf8
```

**Option B: Manually**
1. Create a new file named `.env` in the project root
2. Copy and paste the content above
3. Update the values (especially API keys) as needed

### Step 7: Verify .env File

```powershell
Get-Content .env
```

Make sure `DATABASE_URL` is set correctly.

---

## Database Initialization

### Step 8: Install Python Dependencies (if not already done)

```powershell
pip install -r requirements.txt
```

### Step 9: Initialize Database Schema

This creates all the tables, indexes, and functions:
```powershell
python init_database.py
```

**Expected output:**
```
============================================================
Database Initialization Script
============================================================

🔗 Connecting to database...
   URL: postgresql://postgres:postgres@localhost:5432/agentic_rag
✅ Connected successfully!
📄 Reading schema from: ...
🔧 Executing schema SQL...
   This will create tables: documents, chunks, sessions, messages
✅ Database schema initialized successfully!

📊 Created 4 tables:
   ✓ chunks
   ✓ documents
   ✓ messages
   ✓ sessions

🎉 Database is ready!

✅ Ready for next step: Document ingestion
   Run: python -m ingestion.ingest --verbose --clean
```

---

## Verification

### Step 10: Test Database Connection

```powershell
python -c "import asyncio; from agent.db_utils import test_connection; result = asyncio.run(test_connection()); print('✅ Connection successful!' if result else '❌ Connection failed!')"
```

Or using psql directly:
```powershell
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
```

You should see:
```
 tablename
-----------
 chunks
 documents
 messages
 sessions
(4 rows)
```

---

## Next Steps

### Step 11: Ingest Documents (Optional but Recommended)

Once the database is set up, you can ingest your documents:

```powershell
python -m ingestion.ingest --verbose
```

Or to clean and re-ingest:
```powershell
python -m ingestion.ingest --verbose --clean
```

### Step 12: Start the API Server

```powershell
python -m agent.api
```

The API will be available at: http://localhost:8058

---

## Common Commands Reference

### Start Database
```powershell
docker compose up -d
```

### Stop Database
```powershell
docker compose down
```

### View Database Logs
```powershell
docker logs agentic-rag-postgres
```

### Access PostgreSQL CLI
```powershell
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag
```

### Reset Database (removes all data)
```powershell
docker compose down -v
docker compose up -d
python init_database.py
```

---

## Troubleshooting

### Port 5432 Already in Use

If you get an error about port 5432 being in use:

1. Edit `docker-compose.yml`
2. Change the port mapping from `"5432:5432"` to `"5433:5432"`
3. Update `.env` to use port 5433: `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/agentic_rag`
4. Restart: `docker compose down && docker compose up -d`

### Container Won't Start

Check logs:
```powershell
docker logs agentic-rag-postgres
```

### Connection Refused

1. Make sure Docker Desktop is running
2. Check container is running: `docker ps`
3. Wait a bit longer (database takes 10-15 seconds to start)

### Module Not Found Errors

Make sure you're in a virtual environment and dependencies are installed:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

