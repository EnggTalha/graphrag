# 🚀 START HERE - Quick Setup Guide

## Step 1: Create .env File

### Option A: Use the Script (Easiest)
```powershell
# Double-click this file or run:
.\CREATE_ENV.bat
```

Then edit `.env` file and fill in your actual values.

### Option B: Manual Creation
```powershell
# Create .env file
New-Item -Path ".env" -ItemType File
notepad .env
```

Copy and paste this into `.env`:

```env
# PostgreSQL Database
DATABASE_URL=postgresql://username:password@host:5432/database

# Neo4j Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# OpenAI API
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-proj-your-api-key-here
LLM_CHOICE=gpt-4o-mini

# OpenAI Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-proj-your-api-key-here
EMBEDDING_MODEL=text-embedding-3-small

# Ingestion
INGESTION_LLM_CHOICE=gpt-4o-mini

# Application
APP_ENV=development
LOG_LEVEL=INFO
APP_PORT=8058
```

## Step 2: Get Your Services

### 1. PostgreSQL (for vector search)
**Option A: Neon (Recommended - Free)**
- Go to https://neon.tech
- Sign up and create project
- Copy connection string
- Paste into `DATABASE_URL` in .env

**Option B: Local PostgreSQL**
- Download from https://www.postgresql.org/download/windows/
- Install and create database

### 2. Neo4j (for knowledge graph)
- Download Neo4j Desktop: https://neo4j.com/download/
- Install and create new database
- Start the database
- Copy password to `NEO4J_PASSWORD` in .env

### 3. OpenAI API Key
- Go to https://platform.openai.com/api-keys
- Create new secret key
- Copy key to both `LLM_API_KEY` and `EMBEDDING_API_KEY` in .env

## Step 3: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

## Step 4: Initialize Database

```powershell
# Run schema (use your database URL)
psql -d "your_database_url" -f sql/schema.sql

# OR copy contents of sql/schema.sql into pgAdmin
```

## Step 5: Ingest Documents

```powershell
# Ingest all documents (PDF, Excel, TXT)
python -m ingestion.ingest --verbose --clean
```

**Wait 15-30 minutes** for processing.

## Step 6: Run the System

### Terminal 1 - API Server
```powershell
.\venv\Scripts\Activate.ps1
python -m agent.api
```

### Terminal 2 - CLI Interface
```powershell
.\venv\Scripts\Activate.ps1
python cli.py
```

## Step 7: Ask Questions!

```
You: What projects are in the database?
You: Tell me about project PRJ-026
You: What happened in the November meeting?
```

## 📚 Full Documentation

- **CHANGES_SUMMARY.md** - What's new
- **SETUP_GUIDE.md** - Detailed setup
- **QUICK_START.md** - Command reference
- **JSON_STORAGE_GUIDE.md** - Conversation storage
- **UPDATES_DEC_2025.md** - All updates

## ✅ Your Documents

All ready to ingest:
- ✅ meetings_minutes.txt
- ✅ knowledge_bot_data.txt
- ✅ knowledge_bot_data.xlsx (Excel)
- ✅ knowledge_bot_doc.pdf (PDF)

## 🆘 Need Help?

### Common Issues

**"Scripts disabled"**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"No module named..."**
```powershell
pip install -r requirements.txt
```

**Can't connect to database**
- Check DATABASE_URL in .env
- Verify database is running

**OpenAI errors**
- Verify API key is correct
- Check you have credits

## 🎯 Quick Test

After setup, test the system:

```powershell
# Check API health
curl http://localhost:8058/health

# Should return: {"status":"healthy"}
```

---

**You're ready!** Follow steps 1-7 above. 🚀

