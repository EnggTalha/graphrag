# Quick Start Commands - Real Estate Q/A RAG

## Prerequisites Checklist
- [ ] PostgreSQL database with pgvector (Neon or local)
- [ ] Neo4j running (Desktop or Aura)
- [ ] OpenAI API key
- [ ] Python 3.11+ installed

## 1️⃣ One-Time Setup

```powershell
# Navigate to project
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file
New-Item -Path ".env" -ItemType File
notepad .env
```

### Add to .env file:
```env
DATABASE_URL=postgresql://user:pass@host:5432/db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_CHOICE=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
INGESTION_LLM_CHOICE=gpt-4o-mini
APP_PORT=8058
```

### Initialize Database
```powershell
# Run schema.sql in your PostgreSQL database
psql -d "your_database_url" -f sql/schema.sql
```

## 2️⃣ Ingest Documents (First Time)

```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Ingest with verbose output
python -m ingestion.ingest --verbose --clean
```

**This will take 15-30 minutes for large documents!**

## 3️⃣ Start the System

### Terminal 1 - API Server
```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python -m agent.api
```

### Terminal 2 - CLI Interface
```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python cli.py
```

## 4️⃣ Test Your System

### Via CLI
Just type your questions:
- "What projects are mentioned in the meetings?"
- "Who is Kiran Williams?"
- "What is project PRJ-026?"

### Via API
```powershell
# Health check
curl http://localhost:8058/health

# Send a query
curl -X POST "http://localhost:8058/chat" `
  -H "Content-Type: application/json" `
  -d '{"message": "What projects are in the database?"}'
```

## 🔄 Daily Usage

```powershell
# Start Neo4j (if not auto-started)
# Open Neo4j Desktop and click Start on your database

# Terminal 1 - Start API
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python -m agent.api

# Terminal 2 - Start CLI
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python cli.py
```

## 📝 Adding New Documents

```powershell
# Add .txt or .md files to the documents folder
Copy-Item "path\to\new\document.txt" -Destination "documents\"

# Re-run ingestion (add --clean to replace all data)
python -m ingestion.ingest --verbose

# Or just add new documents without cleaning
python -m ingestion.ingest --verbose
```

## ⚡ Fast Ingestion (Skip Knowledge Graph)

```powershell
# For testing or if you don't need relationship graphs
python -m ingestion.ingest --fast --verbose
```

## 🛠️ Useful Commands

```powershell
# Check if API is running
curl http://localhost:8058/health

# View API docs in browser
start http://localhost:8058/docs

# Check database records
psql -d "your_db_url" -c "SELECT COUNT(*) FROM documents;"

# View logs with more detail
$env:LOG_LEVEL="DEBUG"
python -m agent.api
```

## 🐛 Quick Fixes

**Virtual environment not activating?**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

**Port already in use?**
Change APP_PORT in .env to different port like 8059

**Can't connect to database?**
Test connection:
```powershell
psql -d "your_database_url"
```

**OpenAI API errors?**
- Check API key has no spaces
- Verify you have credits: https://platform.openai.com/account/usage

## 📊 Check Status

```powershell
# Documents ingested
psql -d "your_db" -c "SELECT title, created_at FROM documents;"

# Number of chunks
psql -d "your_db" -c "SELECT COUNT(*) FROM chunks;"

# Recent chat sessions
psql -d "your_db" -c "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;"
```

## 🎯 Your Documents Ready for Ingestion

✅ `meetings_minutes.txt` (28 KB)
✅ `knowledge_bot_data.txt` (13.3 MB)
✅ `knowledge_bot_data.xlsx` (20 KB) - **NOW SUPPORTED!**
✅ `knowledge_bot_doc.pdf` (27 KB) - **NOW SUPPORTED!**

**✨ NEW:** PDF and Excel files are automatically parsed - no conversion needed!

**Supported formats:** .txt, .md, .pdf, .xls, .xlsx, .csv

---

**Need help?** Check `SETUP_GUIDE.md` for detailed instructions!

