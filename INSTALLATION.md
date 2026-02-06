# Installation & Setup Guide

Complete setup guide for Graph-RAG on all platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start-5-minutes)
3. [Detailed Installation](#detailed-installation)
4. [Platform-Specific Setup](#platform-specific-setup)
5. [Configuration](#configuration)
6. [Verify Installation](#verify-installation)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Check that you have everything:

```bash
# Python 3.11+
python --version

# Docker
docker --version

# Docker Compose
docker compose version
```

If you're missing any, see [Platform-Specific Setup](#platform-specific-setup) below.

---

## Quick Start (5 minutes)

### For Impatient Users

```bash
# 1. Clone
git clone https://github.com/EnggTalha/Graph_Rag.git
cd Graph_Rag

# 2. Create Python environment
conda create -n graph_rag python=3.11 -y && conda activate graph_rag

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start services
docker compose up -d

# 5. Initialize database
python init_database.py

# 6. Configure environment
cp .env.example .env
# Edit .env if needed (default uses free Ollama)

# 7. Ready to use!
python cli.py
```

---

## Detailed Installation

### Step 1: Install Prerequisites

#### Python 3.11

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
python3.11 --version
```

**macOS:**
```bash
brew install python@3.11
python3.11 --version
```

**Windows:**
Download from https://www.python.org/downloads/ and run installer.

#### Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
```

**macOS:**
```bash
brew install docker docker-compose
# Or download Docker Desktop from https://www.docker.com/products/docker-desktop
```

**Windows:**
Download Docker Desktop from https://www.docker.com/products/docker-desktop

**WSL2:**
```bash
# Install Docker on WSL2
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### Ollama (Free Local LLM - Optional but Recommended)

Visit https://ollama.ai and download for your platform.

After install:
```bash
# Download a free model
ollama pull mistral

# Verify
ollama run mistral "Say hello"
```

### Step 2: Clone Repository

```bash
git clone https://github.com/EnggTalha/Graph_Rag.git
cd Graph_Rag
```

### Step 3: Create Python Environment

#### Using Conda (Recommended)

```bash
# Create environment
conda create -n graph_rag python=3.11 -y

# Activate
conda activate graph_rag

# Verify
python --version  # Should be 3.11.x
```

#### Using venv

```bash
# Create environment
python3.11 -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### Step 4: Install Dependencies

```bash
# Make sure environment is activated
conda activate graph_rag  # or source venv/bin/activate

# Install
pip install -r requirements.txt

# Verify
python -c "import fastapi; import neo4j; print('✅ Dependencies installed')"
```

### Step 5: Start Docker Services

```bash
# Start services
docker compose up -d

# Verify they're running
docker compose ps

# Should see:
# postgres  - Up
# neo4j     - Up  
# redis     - Up
```

If services fail to start:
```bash
# Check logs
docker compose logs

# Check if ports are available
lsof -i :5432  # PostgreSQL
lsof -i :7687  # Neo4j
lsof -i :6379  # Redis
```

### Step 6: Initialize Database

```bash
# Create database schema
python init_database.py

# Expected output:
# ✅ PostgreSQL connection successful
# ✅ Neo4j connection successful
# ✅ Database initialized
```

### Step 7: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit if needed
nano .env
# or
vim .env
# or
code .env  # VS Code
```

See [Configuration](#configuration) section below for options.

### Step 8: Test Installation

```bash
# Start CLI
python cli.py

# You should see:
# 🤖 Welcome to Graph-RAG CLI!
# >

# Test with a simple query
> Hello

# Type 'quit' or 'exit' to exit
> quit
```

---

## Platform-Specific Setup

### Linux (Ubuntu 20.04+, Debian 11+)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, Docker, etc.
sudo apt install python3.11 python3.11-venv python3-pip docker.io docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
python3.11 --version
docker --version
docker compose version

# Continue with main installation
```

### macOS (Intel & Apple Silicon)

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 docker docker-compose

# Verify
python3.11 --version
docker --version

# Download Docker Desktop from https://www.docker.com/products/docker-desktop

# Continue with main installation
```

### Windows (Native)

1. Download Python 3.11 from https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH"
   - ✅ Click "Install Now"

2. Download Docker Desktop from https://www.docker.com/products/docker-desktop
   - Run installer
   - Enable WSL2 integration

3. Open PowerShell and verify:
```powershell
python --version
docker --version
docker compose version
```

4. Continue with main installation

### Windows WSL2 (Recommended for Windows)

```bash
# In WSL2 terminal
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
python --version
docker --version

# Continue with main installation
```

---

## Configuration

### .env Options

#### Option 1: Free Local (Default - Recommended)

No API keys needed, runs 100% locally:

```bash
LLM_PROVIDER=ollama
LLM_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Make sure Ollama is running:
```bash
ollama serve  # In another terminal
```

#### Option 2: Free HuggingFace

No API keys needed, models downloaded from cloud:

```bash
LLM_PROVIDER=huggingface
EMBEDDING_PROVIDER=huggingface
```

#### Option 3: OpenAI (Paid)

Get API key from https://platform.openai.com/api-keys

```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-your-actual-key-here
LLM_CHOICE=gpt-4-turbo
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-proj-your-actual-key-here
EMBEDDING_MODEL=text-embedding-3-small
```

#### Option 4: Anthropic (Paid)

Get API key from https://console.anthropic.com

```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your-actual-key-here
LLM_CHOICE=claude-3-5-sonnet-20241022
EMBEDDING_PROVIDER=huggingface  # Use free embeddings
```

### Database Configuration

Usually don't need to change these (Docker defaults):

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/graph_rag
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=neo4j_password_change_me
```

### Application Settings

```bash
APP_ENV=development        # or: staging, production
APP_PORT=8000             # API server port
LOG_LEVEL=INFO            # or: DEBUG, WARNING, ERROR
```

---

## Verify Installation

### Check Services Are Running

```bash
docker compose ps

# Should show:
# NAME       STATUS
# postgres   Up
# neo4j      Up
# redis      Up
```

### Check Python Setup

```bash
python -c "import fastapi, neo4j, sqlalchemy; print('✅ All imports work')"
```

### Test CLI

```bash
python cli.py

# Should start interactive session:
# 🤖 Welcome to Graph-RAG CLI!
# >

# Type: quit
```

### Test API (Optional)

```bash
# Terminal 1: Start API
python -m agent.api

# Terminal 2: Send request
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "hello", "top_k": 5}'
```

---

## Troubleshooting

### Docker Services Won't Start

```bash
# Check what's using the ports
lsof -i :5432
lsof -i :7687
lsof -i :6379

# Kill service if needed
kill -9 <PID>

# Or change ports in docker-compose.yml

# Try again
docker compose down
docker compose up -d
```

### Python Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall --no-cache-dir

# Verify environment is activated
conda activate graph_rag  # or source venv/bin/activate
python --version
```

### Database Connection Error

```bash
# Initialize database again
python init_database.py

# Check if postgres is healthy
docker compose logs postgres

# Try restarting
docker compose restart postgres
```

### Ollama Not Found

```bash
# Check if Ollama is installed
ollama --version

# If not, install from https://ollama.ai

# Start Ollama service
ollama serve

# In another terminal, download model
ollama pull mistral
```

### Model Download Fails

```bash
# If downloading models fails, try:

# 1. Check internet connection
ping google.com

# 2. For Ollama, download manually
ollama pull mistral --insecure

# 3. For HuggingFace, check cache
export HF_HOME=/path/to/cache
python cli.py

# 4. Check disk space
df -h
```

### Can't Connect to API

```bash
# Check if API is running
curl http://localhost:8000/docs

# Check logs
docker compose logs

# Restart services
docker compose restart

# Check firewall
sudo ufw allow 8000
```

---

## Next Steps

1. **Add Documents**: Copy your files to `data/` folder
2. **Start Ingestion**: `python -m ingestion.ingest --documents ./data --watch --verbose`
3. **Ask Questions**: `python cli.py`
4. **Use API**: Visit http://localhost:8000/docs for interactive API docs

---

## Getting Help

- Check logs: `docker compose logs`
- Check config: `cat .env`
- Review this guide section by section
- Check GitHub issues

---

Built with ❤️ using FastAPI, PostgreSQL, Neo4j, and Ollama.
