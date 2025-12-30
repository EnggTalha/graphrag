# 🚀 How to Run the Graph RAG System

## Quick Start Guide

### Step 1: Start Docker Containers (PostgreSQL & Neo4j)

```bash
# Make sure you're in the project directory
cd /home/talha/proxima/Graph_Rag/Graph_Rag

# Start containers
docker compose up -d

# Verify they're running
docker ps
# Should see: agentic-rag-postgres and agentic-rag-neo4j
```

### Step 2: Ingest Your Documents

**Option A: Continuous Mode (Recommended)**
```bash
# Activate your conda environment
conda activate Talha

# Run with --watch flag (keeps running and watches for new files)
python -m ingestion.ingest --documents data --watch --verbose
```

**Option B: One-Time Ingestion**
```bash
# Activate your conda environment
conda activate Talha

# Run ingestion once (will skip already ingested files)
python -m ingestion.ingest --documents data --verbose
```

**Note**: 
- **Continuous mode** (`--watch`): Keeps running forever, automatically ingests new files as they appear
- **One-time mode**: Processes files once and exits

### Step 3: Start the Main API Server (Terminal 1)

```bash
# Make sure conda environment is activated
conda activate Talha

# Start API server
python -m agent.api
```

**Keep this terminal open!** You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8058
```

### Step 4: Run the CLI (Terminal 2)

Open a **new terminal** and run:

```bash
# Navigate to project
cd /home/talha/proxima/Graph_Rag/Graph_Rag

# Activate conda environment
conda activate Talha

# Run CLI
python cli.py
```

You should see:
```
🤖 Agentic RAG with Knowledge Graph CLI
============================================================
Connected to: http://localhost:8058
✓ API is healthy
Ready to chat!
```

### Step 5: Ask Questions!

Once CLI is running, type your questions:

```
You: What projects are in the database?
You: Tell me about project PRJ-032
You: Who is Sophia Williams?
You: What happened in the meetings?
```

---

## Daily Usage (After Initial Setup)

### Start Everything

```bash
# Terminal 1: Start Docker (if not running)
docker compose up -d

# Terminal 2: Start Continuous Ingestion (watches for new files)
conda activate Talha
python -m ingestion.ingest --documents data --watch --verbose

# Terminal 3: Start Main API
conda activate Talha
python -m agent.api

# Terminal 4: Start CLI
conda activate Talha
python cli.py
```

**Or use One-Time Ingestion instead:**
```bash
# Terminal 2: One-time ingestion
conda activate Talha
python -m ingestion.ingest --documents data --verbose
```

### Stop Everything

```bash
# Stop CLI: Type 'exit' or press Ctrl+C
# Stop API: Press Ctrl+C in Terminal 2
# Stop Docker (optional): docker compose down
```

---

## Useful Commands

### Check Data Status

```bash
# Quick check
python check_data.py
```

### Re-ingest Documents (if needed)

```bash
# Clean and re-ingest everything
python -m ingestion.ingest --documents data --clean --verbose

# Or just add new files (will skip existing)
python -m ingestion.ingest --documents data --verbose
```

### Check API Health

```bash
curl http://localhost:8058/health
```

### View API Documentation

Open in browser: http://localhost:8058/docs

---

## Troubleshooting

### "Connection refused" to API
- Make sure API server is running in Terminal 1
- Check: `curl http://localhost:8058/health`

### "No documents found"
- Run ingestion: `python -m ingestion.ingest --documents data --verbose`

### Docker containers not running
- Start them: `docker compose up -d`
- Check: `docker ps`

### Slow responses in CLI
- This is normal for complex queries
- System is searching vector DB + knowledge graph
- Shows "💭 Thinking..." while processing

---

## Quick Reference

| Task | Command |
|------|---------|
| Start Docker | `docker compose up -d` |
| Ingest documents | `python -m ingestion.ingest --documents data --verbose` |
| Start API | `python -m agent.api` |
| Start CLI | `python cli.py` |
| Check data | `python check_data.py` |
| Check health | `curl http://localhost:8058/health` |

---

**That's it!** You're ready to use the system. 🎉

