# Graph-RAG - Open Source Hybrid Search with Knowledge Graphs

A completely **free and open source** Retrieval-Augmented Generation (RAG) system that combines **Vector Search** (PostgreSQL with pgvector) and **Knowledge Graphs** (Neo4j) for semantic understanding and context-aware question answering.

## 🎯 Key Features

- **100% Open Source**: MIT License, free forever
- **Hybrid Search**: Vector embeddings + knowledge graph traversal
- **Free LLM Models**: Use Ollama locally or any API provider
- **Auto-Ingestion**: Watch directories and automatically process documents
- **Knowledge Extraction**: Extract entities and relationships automatically
- **REST API**: FastAPI-based endpoints for integration
- **CLI Interface**: Interactive command-line chat
- **Docker Ready**: Pre-configured containerized setup

## 📚 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Setup and installation guide

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Optional: Ollama for free local LLM

### 1. Clone and Setup

```bash
git clone https://github.com/EnggTalha/Graph_Rag.git
cd Graph_Rag
```

### 2. Start Docker Services

```bash
docker compose up -d
```

### 3. Install Python Dependencies

```bash
conda create -n graph_rag python=3.11 -y
conda activate graph_rag
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env to set your LLM provider
# Default: uses local Ollama (free, no API key needed)
```

### 5. Initialize Database

```bash
python init_database.py
```

### 6. Start Using

**Interactive CLI:**
```bash
python cli.py
```

**REST API Server:**
```bash
python -m agent.api
# Visit http://localhost:8000/docs for API documentation
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI (Python) |
| **Vector DB** | PostgreSQL + pgvector |
| **Graph DB** | Neo4j |
| **LLM Models** | Ollama (local), OpenAI, Anthropic, HuggingFace |
| **Embeddings** | HuggingFace (free) or OpenAI |
| **Deployment** | Docker & Docker Compose |

## 📁 Project Structure

```
Graph_Rag/
├── agent/              # Core RAG agent and API
├── ingestion/          # Document processing pipeline
├── frontend/           # Web interface
├── data/               # Your documents go here
├── sql/                # Database schemas
├── docker-compose.yml  # Service configuration
├── cli.py              # Interactive CLI
└── requirements.txt    # Python dependencies
```

## 📖 Common Commands

```bash
# Start services
docker compose up -d

# Ingest documents
python -m ingestion.ingest --documents ./data --watch --verbose

# Start API server
python -m agent.api

# Start CLI
python cli.py

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## 🤖 Using Free Local Models (Ollama)

No API keys needed! Run everything on your machine:

```bash
# Install Ollama from https://ollama.ai

# Download a free model
ollama pull mistral

# In .env, set:
LLM_PROVIDER=ollama
LLM_MODEL=mistral

# Start using
python cli.py
```

## 💰 Using Commercial APIs (Optional)

If you prefer paid providers with more powerful models:

```bash
# In .env, set:
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-your-key-here
```

Supported providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- HuggingFace (free cloud models)
- Any OpenAI-compatible API

## 📋 Supported File Formats

- **Text**: `.txt`, `.md`, `.markdown`, `.rst`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Data**: `.json`, `.csv`, `.xlsx`
- **Code**: `.py`, `.js`, `.ts`, etc.

## 🔗 API Documentation

Once API server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🐛 Troubleshooting

**Docker services won't start:**
```bash
# Check if ports are in use
lsof -i :5432    # PostgreSQL
lsof -i :7687    # Neo4j
lsof -i :6379    # Redis

# View logs
docker compose logs
```

**Import errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Database connection issues:**
```bash
# Check database is initialized
python init_database.py

# View database logs
docker compose logs postgres
```

## 📞 Support

For issues and questions:
- Check [INSTALLATION.md](INSTALLATION.md) for detailed setup
- Review docker compose logs: `docker compose logs`
- Check .env configuration

## 📄 License

MIT License - See LICENSE file for details

## 🎉 Getting Started

See [INSTALLATION.md](INSTALLATION.md) for complete setup instructions for all platforms (Linux, macOS, Windows, WSL2).

---

Built with ❤️ using FastAPI, PostgreSQL, Neo4j, and Ollama.
