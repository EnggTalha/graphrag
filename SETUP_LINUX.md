# 🐧 Linux Setup Guide - Step by Step (100% Local)

Complete step-by-step guide to set up the Graph RAG system on Linux **with everything running locally** - no cloud services required!

## 🏠 Local Setup (Databases Local, OpenAI for AI)

This guide sets up:
- ✅ **PostgreSQL** - Running locally in Docker
- ✅ **Neo4j** - Running locally in Docker  
- ✅ **OpenAI** - For embeddings and text generation (model 4.1)
- ✅ **All data** - Stored on your local machine

**Databases run locally, OpenAI API used for AI processing.**

## 📋 Prerequisites Checklist

Before starting, make sure you have:
- [ ] Linux server/desktop with bash shell
- [ ] Python 3.11 or higher installed
- [ ] Docker and Docker Compose installed (for local PostgreSQL and Neo4j)
- [ ] OpenAI API key (for embeddings and generation)

---

## Step 1: Install Prerequisites

### 1.1 Check Python Version

```bash
python3 --version
# Should show Python 3.11 or higher
```

If Python is not installed or outdated:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# CentOS/RHEL
sudo yum install python3.11 python3-pip
```

### 1.2 Install Docker and Docker Compose

```bash
# Check if Docker is installed
docker --version
docker compose version

# If not installed, install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (if not included)
sudo apt install docker-compose-plugin

# Log out and log back in for group changes to take effect
# OR use: newgrp docker
```

### 1.3 Fix Docker Permission Issues

If you get "permission denied" errors when running Docker commands:

```bash
# Option 1: Add your user to docker group (if not already added)
sudo usermod -aG docker $USER

# Then either:
# - Log out and log back in
# - OR run: newgrp docker
# - OR use: su - $USER

# Option 2: Use sudo (temporary solution)
sudo docker compose up -d

# Option 3: Verify you're in the docker group
groups | grep docker
# Should show: docker in the list
```

---

## Step 2: Clone/Navigate to Project

```bash
# If you haven't already, navigate to your project directory
cd /home/talha/proxima/Graph_Rag/Graph_Rag

# Verify you're in the right place
ls -la
# Should see: agent/, ingestion/, sql/, requirements.txt, etc.
```

---

## Step 3: Set Up Local PostgreSQL Database

We'll use Docker to run PostgreSQL locally with pgvector extension.

### 3.1 Start PostgreSQL Container

```bash
# Start PostgreSQL with pgvector
docker compose up -d

# Wait 10-15 seconds, then verify it's running
docker ps
# Should see: agentic-rag-postgres
```

### 3.2 Verify Database is Ready

```bash
# Check logs to see when it's ready
docker logs agentic-rag-postgres

# Look for: "database system is ready to accept connections"
```

### 3.3 Create .env File for Database

```bash
# Create .env file
cat > .env << 'EOF'
# PostgreSQL Database (Local Docker)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentic_rag
EOF
```

---

## Step 4: Set Up Local Neo4j

We'll use Docker Compose to run Neo4j locally for the knowledge graph (it's already in docker-compose.yml).

### 4.1 Update Neo4j Password in docker-compose.yml

```bash
# Edit docker-compose.yml to set a secure password
# Replace 'neo4j_password_change_me' with your desired password
nano docker-compose.yml
# Or use sed to change it:
# sed -i 's/neo4j_password_change_me/your_secure_password/g' docker-compose.yml
```

**Important:** Choose a secure password and remember it!

### 4.2 Start Neo4j Container

```bash
# Start Neo4j (and PostgreSQL if not already running)
docker compose up -d

# Wait for Neo4j to start (30-60 seconds)
docker logs -f agentic-rag-neo4j
# Press Ctrl+C when you see "Started."
```

### 4.3 Add Neo4j Configuration to .env

```bash
# Add Neo4j config to .env (replace your_secure_password with the password you set in docker-compose.yml)
cat >> .env << 'EOF'

# Neo4j Configuration (Local)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
EOF
```

**Note:** Make sure to replace `your_secure_password` in the .env file with the actual password you set in docker-compose.yml!

---

## Step 5: Configure OpenAI for LLM and Embeddings

We'll use **OpenAI** for both text generation and embeddings using model 4.1.

### 5.1 Get OpenAI API Key

1. **Sign up or log in** to OpenAI: https://platform.openai.com
2. **Navigate to API Keys**: https://platform.openai.com/api-keys
3. **Create a new secret key**
4. **Copy the key** (starts with `sk-...`) - you won't be able to see it again!

### 5.2 Add OpenAI Configuration to .env

```bash
cat >> .env << 'EOF'

# LLM Provider Configuration (OpenAI - Model 4.1)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key-here
LLM_CHOICE=gpt-4.1-mini

# Embedding Configuration (OpenAI)
EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-api-key-here
EMBEDDING_MODEL=text-embedding-3-small

# Ingestion Configuration
INGESTION_LLM_CHOICE=gpt-4.1-mini
EOF
```

**Important:** Replace `sk-your-api-key-here` with your actual OpenAI API key in both places!

### 5.3 Verify OpenAI Configuration

```bash
# Check that API key is set (don't expose it!)
grep LLM_API_KEY .env | head -c 30
# Should show: LLM_API_KEY=sk-...
```

---

## Step 6: Complete .env Configuration

Add application settings:

```bash
cat >> .env << 'EOF'

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
APP_PORT=8058
EOF
```

### Verify .env File

```bash
# View your complete .env file (be careful not to expose secrets!)
cat .env

# Should contain:
# - DATABASE_URL
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# - LLM_PROVIDER, LLM_API_KEY, etc.
# - EMBEDDING_PROVIDER, EMBEDDING_API_KEY, etc.
```

---

## Step 7: Set Up Python Environment

### 7.1 Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# You should see (venv) in your prompt
```

### 7.2 Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# This may take a few minutes
```

---

## Step 8: Initialize Database Schema

### 8.1 Run Database Initialization

```bash
# Make sure venv is activated
source venv/bin/activate

# Initialize database schema
python init_database.py
```

**Expected output:**
```
============================================================
Database Initialization Script
============================================================

🔗 Connecting to database...
✅ Connected successfully!
📄 Reading schema from: ...
🔧 Executing schema SQL...
✅ Database schema initialized successfully!

📊 Created 4 tables:
   ✓ chunks
   ✓ documents
   ✓ messages
   ✓ sessions

🎉 Database is ready!
```

### 8.2 Verify Database Setup

```bash
# Test database connection
python -c "import asyncio; from agent.db_utils import test_connection; print('✅ Connected!' if asyncio.run(test_connection()) else '❌ Failed!')"
```

---

## Step 9: Prepare Documents for Ingestion

### 9.1 Check Data Folder

Your documents are already in the `data/` folder. Let's verify:

```bash
# Check what's in the data folder
ls -la data/

# You should see:
# - knowledge_bot_data.txt
# - knowledge_bot_data.xlsx
# - knowledge_bot_doc.pdf
# - meetings_minutes.txt
```

### 9.2 Supported File Formats

The ingestion pipeline supports these formats (no conversion needed!):
- ✅ `.txt` - Plain text files
- ✅ `.md` - Markdown files
- ✅ `.pdf` - PDF files (automatically parsed)
- ✅ `.xls`, `.xlsx` - Excel files (automatically parsed)
- ✅ `.csv` - CSV files

**All your files in the `data/` folder are ready to ingest!** No conversion needed.

---

## Step 10: Run Document Ingestion

**Important:** This step processes your documents from the `data/` folder and builds the knowledge graph. It can take 15-30 minutes for large documents.

### 10.1 Basic Ingestion

```bash
# Make sure venv is activated
source venv/bin/activate

# Run ingestion from data folder with verbose output
python -m ingestion.ingest --documents data --verbose
```

This will process all files in your `data/` folder:
- `knowledge_bot_data.txt`
- `knowledge_bot_data.xlsx`
- `knowledge_bot_doc.pdf`
- `meetings_minutes.txt`

### 10.2 Clean Re-ingestion (if needed)

If you want to start fresh and remove existing data:

```bash
# Clean existing data and re-ingest everything from data folder
python -m ingestion.ingest --documents data --clean --verbose
```

### 10.3 Fast Ingestion (Skip Knowledge Graph)

For faster testing (skips knowledge graph building):

```bash
python -m ingestion.ingest --documents data --chunk-size 800 --no-semantic --verbose
```

**What happens during ingestion:**
- Documents from `data/` folder are parsed (PDF, Excel, TXT automatically handled)
- Documents are chunked intelligently
- Embeddings are generated using OpenAI
- Entities and relationships are extracted
- Data is stored in PostgreSQL and Neo4j

---

## Step 11: Start the API Server

### 11.1 Start API (Terminal 1)

```bash
# Make sure venv is activated
source venv/bin/activate

# Start the FastAPI server
python -m agent.api
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8058
```

**Keep this terminal open!** The API server must be running.

### 11.2 Verify API is Running

In a new terminal:

```bash
# Test health endpoint
curl http://localhost:8058/health

# Should return: {"status":"healthy"}
```

---

## Step 12: Use the CLI Interface

### 12.1 Start CLI (Terminal 2)

Open a **new terminal** (keep API running in Terminal 1):

```bash
# Navigate to project directory
cd /home/talha/proxima/Graph_Rag/Graph_Rag

# Activate virtual environment
source venv/bin/activate

# Start CLI
python cli.py
```

**Expected output:**
```
🤖 Agentic RAG with Knowledge Graph CLI
============================================================
Connected to: http://localhost:8058
✓ API is healthy
Ready to chat!
```

### 12.2 Try Example Questions

Once the CLI is running, try these questions:

```
You: What projects are in the database?
You: Tell me about project PRJ-026
You: What happened in the November meeting?
You: Who is Kiran Williams?
```

---

## Step 13: Test the System

### 13.1 Health Check

```bash
curl http://localhost:8058/health
```

### 13.2 API Documentation

Open in browser: http://localhost:8058/docs

### 13.3 Test Chat Endpoint

```bash
curl -X POST "http://localhost:8058/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What projects are in the database?"}'
```

---

## 🎉 You're Done!

Your Graph RAG system is now running! Here's what you have:

- ✅ **Local PostgreSQL** database with pgvector (vector search) - running in Docker
- ✅ **Local Neo4j** knowledge graph (relationship tracking) - running in Docker
- ✅ **OpenAI GPT-4.1-mini** for text generation - via API
- ✅ **OpenAI text-embedding-3-small** for embeddings - via API
- ✅ Documents ingested and processed
- ✅ API server running on port 8058
- ✅ CLI interface ready for queries

**Databases run locally, OpenAI handles AI processing!**

---

## 📝 Daily Usage

### Start All Services

```bash
# 1. Start Docker containers (PostgreSQL and Neo4j)
cd /home/talha/proxima/Graph_Rag/Graph_Rag
docker compose up -d

# 2. Terminal 1: Start API
cd /home/talha/proxima/Graph_Rag/Graph_Rag
source venv/bin/activate
python -m agent.api

# 3. Terminal 2: Start CLI
cd /home/talha/proxima/Graph_Rag/Graph_Rag
source venv/bin/activate
python cli.py
```

**Note:** OpenAI API is accessed over the internet - no local service needed to start.

### Stop the System

```bash
# Stop API: Press Ctrl+C in Terminal 1
# Stop CLI: Type 'exit' or press Ctrl+C in Terminal 2
# Stop Docker containers (optional, if you want to free resources)
docker compose down
```

---

## 🛠️ Useful Commands

### Database Management

```bash
# Start PostgreSQL (if using Docker)
docker compose up -d

# Stop PostgreSQL
docker compose down

# View PostgreSQL logs
docker logs agentic-rag-postgres

# Access PostgreSQL CLI
docker exec -it agentic-rag-postgres psql -U postgres -d agentic_rag
```

### Neo4j Management

```bash
# Start Neo4j (via docker compose)
docker compose up -d neo4j

# Stop Neo4j
docker compose stop neo4j

# View Neo4j logs
docker logs agentic-rag-neo4j

# Access Neo4j Browser
# Open: http://localhost:7474
# Default login: neo4j / (your password from docker-compose.yml)
```

### OpenAI API Management

```bash
# Check OpenAI API key is configured
grep LLM_API_KEY .env

# Test OpenAI API connection (requires curl and jq)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $(grep LLM_API_KEY .env | cut -d'=' -f2)" | jq '.data[] | select(.id | contains("gpt-4.1"))'

# Check API usage (requires OpenAI account access)
# Visit: https://platform.openai.com/usage
```

### Add New Documents

```bash
# Copy new documents to data/ folder
cp /path/to/new/document.txt data/
# Or PDF, Excel, etc. - all formats are supported!

# Re-run ingestion from data folder
source venv/bin/activate
python -m ingestion.ingest --documents data --verbose

# Or to clean and re-ingest everything
python -m ingestion.ingest --documents data --clean --verbose
```

---

## 🆘 Troubleshooting

### Issue: Docker permission denied

**Solution:**
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Apply the group change (choose one):
# Option 1: Log out and log back in
# Option 2: Run this command:
newgrp docker

# Option 3: Use sudo (not recommended for daily use)
sudo docker compose up -d

# Verify you're in docker group
groups | grep docker
```

### Issue: "Connection refused" to PostgreSQL

**Solution:**
```bash
# Check if container is running
docker ps

# If not running, start it
docker compose up -d

# Check logs
docker logs agentic-rag-postgres
```

### Issue: "Connection refused" to Neo4j

**Solution:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# If not, start it
docker compose up -d neo4j

# Wait 30 seconds, then test
curl http://localhost:7474
```

### Issue: OpenAI API errors

**Solution:**
```bash
# Verify API key is correct
grep LLM_API_KEY .env

# Check API key has no extra spaces or quotes
# Should be: LLM_API_KEY=sk-...

# Test API key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check you have credits
# Visit: https://platform.openai.com/account/usage

# Verify model name is correct (gpt-4.1-mini)
grep LLM_CHOICE .env
```

### Issue: "Module not found" errors

**Solution:**
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "DATABASE_URL not found"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify DATABASE_URL is set
grep DATABASE_URL .env

# If missing, add it (see Step 3)
```

### Issue: Ingestion takes too long

**Solution:**
- Use `--no-semantic` flag to skip knowledge graph
- Use smaller chunk sizes: `--chunk-size 400`
- Process documents in batches

### Issue: Port 8058 already in use

**Solution:**
```bash
# Change port in .env
echo "APP_PORT=8059" >> .env

# Or find and kill process using port 8058
sudo lsof -ti:8058 | xargs kill -9
```

---

## 📚 Additional Resources

- **README.md** - Full project documentation
- **LOCAL_DB_SETUP.md** - Detailed local database setup
- **JSON_STORAGE_GUIDE.md** - Conversation storage guide
- **API Docs** - http://localhost:8058/docs (when API is running)

---

## ✅ Verification Checklist

Before considering setup complete, verify:

- [ ] Docker and Docker Compose are installed
- [ ] PostgreSQL container is running (`docker ps` shows `agentic-rag-postgres`)
- [ ] Neo4j container is running (`docker ps` shows `agentic-rag-neo4j`)
- [ ] OpenAI API key is configured in `.env` file
- [ ] OpenAI API key is valid (test with curl or check usage page)
- [ ] `.env` file is configured correctly with OpenAI settings (gpt-4.1-mini)
- [ ] Python virtual environment is activated
- [ ] Dependencies are installed (`pip list` shows required packages)
- [ ] Database schema is initialized (`python init_database.py` succeeded)
- [ ] Documents are ingested (check with a test query)
- [ ] API server starts without errors
- [ ] CLI connects to API successfully
- [ ] Can ask questions and get responses
- [ ] Databases are running locally (PostgreSQL and Neo4j)

---

**Need help?** Check the troubleshooting section above or review the main README.md file.

