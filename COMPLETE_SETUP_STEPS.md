# ✅ Complete Setup - Step by Step

Follow these steps in order:

## 🗄️ Step 1: Get Neon Database (5 minutes)

### A. Get Connection String from Neon Dashboard

1. Go to: https://console.neon.tech
2. Sign in or create free account
3. Click on your project (or create one)
4. Find **"Connection Details"** section
5. Copy the **Connection string** - looks like:
   ```
   postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
6. **Save this string** - you'll need it in step 3

### B. Alternative: Using CLI
```powershell
npx neonctl@latest init
npx neonctl@latest connection-string
```

---

## 🔵 Step 2: Setup Neo4j (10 minutes)

1. Download: https://neo4j.com/download/
2. Install Neo4j Desktop
3. Create new Project → Create new Database
4. Click "Start" to start the database
5. Set a password (remember it!)
6. **Save these values:**
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: (your password)

---

## 🤖 Step 3: Get OpenAI API Key (2 minutes)

1. Go to: https://platform.openai.com/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...`)
5. **Save this key** - you'll need it next

---

## ⚙️ Step 4: Create .env File (3 minutes)

### Option A: Use the Script
```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\CREATE_ENV.bat
notepad .env
```

### Option B: Manual
```powershell
New-Item -Path ".env" -ItemType File
notepad .env
```

Paste this and **fill in your values from steps 1-3**:

```env
# PostgreSQL Database from Neon (Step 1)
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Neo4j from Step 2
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# OpenAI from Step 3
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-proj-your-key-here
LLM_CHOICE=gpt-4o-mini

EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-proj-your-key-here
EMBEDDING_MODEL=text-embedding-3-small

INGESTION_LLM_CHOICE=gpt-4o-mini
APP_ENV=development
LOG_LEVEL=INFO
APP_PORT=8058
```

**Save and close the file**

---

## 📦 Step 5: Install Python Packages (5 minutes)

```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

---

## 🗃️ Step 6: Initialize Database Schema (2 minutes)

```powershell
# Replace with your actual connection string from .env
psql -d "postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require" -f sql/schema.sql
```

**Or** open `sql/schema.sql` in pgAdmin and execute it.

---

## 📄 Step 7: Ingest Your Documents (20-30 minutes)

```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Ingest all documents (PDF, Excel, TXT)
python -m ingestion.ingest --verbose --clean
```

**This will process:**
- ✅ meetings_minutes.txt
- ✅ knowledge_bot_data.txt
- ✅ knowledge_bot_data.xlsx
- ✅ knowledge_bot_doc.pdf

**Wait for it to complete** - you'll see progress updates.

---

## 🚀 Step 8: Start the System

### Terminal 1 - Start API Server

```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python -m agent.api
```

Wait for:
```
INFO:     Uvicorn running on http://0.0.0.0:8058
```

### Terminal 2 - Start CLI Interface

Open a **NEW terminal** and run:

```powershell
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
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

---

## 💬 Step 9: Ask Questions!

Type your questions in the CLI:

```
You: What projects are in the database?

🤖 Assistant:
Based on the data, I found several projects including:
- Project PRJ-026 (Orion Analytics Dashboard) owned by Kiran Williams
- Project PRJ-055 (Pulse Client Portal) owned by Noor Smith
...

🛠 Tools Used:
  1. vector_search (query='projects database', limit=10)
```

### Try These Questions:

- "What is project PRJ-026?"
- "Tell me about the November meeting"
- "Who is Kiran Williams?"
- "What projects are in the PMO department?"
- "What decisions were made in recent meetings?"
- "Show me all escalation processes"

---

## ✅ Verification Checklist

Make sure all these are ✅:

- [ ] Neon database connection string obtained
- [ ] Neo4j Desktop installed and database started
- [ ] OpenAI API key obtained
- [ ] .env file created with all values filled in
- [ ] Python packages installed (requirements.txt)
- [ ] Database schema initialized (sql/schema.sql)
- [ ] Documents ingested successfully
- [ ] API server running (port 8058)
- [ ] CLI connected and responsive
- [ ] Can ask questions and get answers

---

## 🎯 Quick Reference

### Start System Daily

```powershell
# 1. Start Neo4j Desktop (if not auto-start)

# 2. Terminal 1 - API
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python -m agent.api

# 3. Terminal 2 - CLI
cd "D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph"
.\venv\Scripts\Activate.ps1
python cli.py
```

### Check Status

```powershell
# API health
curl http://localhost:8058/health

# View API docs
start http://localhost:8058/docs
```

### View Conversations

```powershell
# Navigate to conversations
cd data\conversations\conversations

# List all
dir

# View one
notepad <session-id>.json
```

---

## 🆘 Common Issues

### "Execution of scripts is disabled"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Cannot find psql"
- Use pgAdmin to run sql/schema.sql
- Or install PostgreSQL tools

### "Connection refused" to Neon
- Check DATABASE_URL has no extra spaces
- Verify connection string is correct

### "Connection refused" to Neo4j
- Open Neo4j Desktop
- Make sure database is Started (green indicator)

### "OpenAI API error"
- Verify API key is correct
- Check you have credits: https://platform.openai.com/account/usage

### "Module not found"
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 💰 Cost Estimate

### One-Time Ingestion:
- **OpenAI**: ~$1-2 for processing all documents
- **Neon**: Free (free tier)
- **Neo4j**: Free (local)

### Per Query:
- **OpenAI**: ~$0.01-0.05 per question
- **Storage**: Free (JSON files locally)

### Monthly (100 queries):
- **Total**: ~$1-5/month

---

## 🎊 You're Done!

Your Real Estate Q/A RAG system is now:
- ✅ Processing PDF, Excel, and text files
- ✅ Using OpenAI GPT-4o-mini
- ✅ Saving conversations to JSON
- ✅ Ready to answer questions!

Ask away! 🚀

---

**Need more help?**
- NEON_SETUP.md - Detailed Neon guide
- START_HERE.md - Quick start
- SETUP_GUIDE.md - Full documentation

