# Graph RAG with Knowledge Graph

Intelligent Q/A system that combines **Vector Search** (PostgreSQL with pgvector) and a **Knowledge Graph** (Neo4j) to provide comprehensive insights from your documents.

## 📚 Documentation

- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - System architecture and how it works
- **[HOW_TO_RUN.md](HOW_TO_RUN.md)** - Quick start guide
- **[SETUP_LINUX.md](SETUP_LINUX.md)** - Complete Linux setup with Docker

## 🚀 Quick Start

### 1. Start Docker Containers

```bash
docker compose up -d
```

### 2. Run Ingestion (Continuous Mode)

```bash
conda activate Talha
python -m ingestion.ingest --documents data --watch --verbose
```

This will:
- Process existing files
- Keep running and watch for new files
- Auto-ingest new files automatically

### 3. Start API & CLI

**Terminal 1: API Server**
```bash
python -m agent.api
```

**Terminal 2: CLI**
```bash
python cli.py
```

## 📋 Supported File Formats

- **Text**: `.txt`, `.md`, `.markdown`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Spreadsheets**: `.xls`, `.xlsx`, `.csv`

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Databases**: PostgreSQL (with pgvector), Neo4j
- **LLM**: OpenAI GPT-4.1-mini
- **Embeddings**: OpenAI text-embedding-3-small
- **Knowledge Graph**: Graphiti
- **Deployment**: Docker, Docker Compose

## 📖 Features

- ✅ **Automatic File Ingestion** - Watches `data/` folder and auto-ingests new files
- ✅ **Hybrid Search** - Combines vector similarity + graph relationships
- ✅ **Knowledge Graph** - Tracks entities and relationships over time
- ✅ **Continuous Mode** - Keeps running and watching for new files
- ✅ **Multiple Formats** - Supports PDF, Word, Excel, CSV, TXT, Markdown

## 📝 Requirements

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- See `requirements.txt` for Python dependencies

## 🔧 Installation

See **[SETUP_LINUX.md](SETUP_LINUX.md)** for complete setup instructions.

## 📊 Project Structure

```
├── agent/              # AI agent and API
├── ingestion/          # Document processing
├── data/              # Your documents (PDF, Word, Excel, etc.)
├── docker-compose.yml # Docker configuration
└── requirements.txt   # Python dependencies
```

## 🎯 Usage

### Continuous Ingestion (Recommended)

```bash
# Watches data/ folder and auto-ingests new files
python -m ingestion.ingest --documents data --watch --verbose
```

### One-Time Ingestion

```bash
# Process files once and exit
python -m ingestion.ingest --documents data --verbose
```

### Check Data Status

```bash
python check_data.py
```

## 📚 More Information

- **System Overview**: See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- **How to Run**: See [HOW_TO_RUN.md](HOW_TO_RUN.md)
- **Setup Guide**: See [SETUP_LINUX.md](SETUP_LINUX.md)

---

Built with ❤️ using Pydantic AI, FastAPI, PostgreSQL, and Neo4j.
