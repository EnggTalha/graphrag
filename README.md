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
│   └── vector_store/   # Swappable vector DB adapters (pgvector/qdrant/chroma)
├── benchmark/          # Vector DB + multi-LLM comparison runner
├── ingestion/          # Document processing pipeline
├── frontend/           # Web interface
├── data/               # Your documents + data/eval_questions.json
├── results/            # Benchmark output (comparison_summary.csv)
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

# Run the benchmark (vector DB + LLM comparison -> results/comparison_summary.csv)
python -m benchmark --backends pgvector qdrant chroma --load-from-pg --llms mistral llama3

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## 📊 Benchmarking: Vector DB & Multi-LLM Comparison

The `benchmark/` suite compares vector-DB backends and LLMs over a fixed set of evaluation
questions. It runs **vector-only**, **graph-only**, and **hybrid** retrieval, records
retrieval latency (ms) per vector DB, then passes the **same retrieved context** to each
configured LLM and logs generation latency (ms), token usage, and the answer into
`results/comparison_summary.csv`.

Supported vector backends (swappable via a `BaseVectorStore` interface, pgvector is the
default): **pgvector** (PostgreSQL), **Qdrant** (local path or in-memory), **ChromaDB**
(persistent local directory). Neo4j knowledge-graph retrieval is unchanged.

### Prerequisites

```bash
# Core services + an LLM must be reachable (same as normal usage)
docker compose up -d                      # PostgreSQL (pgvector) + Neo4j
ollama pull mistral                       # at least one LLM (or configure an API in .env)

# Install optional benchmark adapters (only needed for Qdrant/Chroma)
pip install qdrant-client chromadb

# Make sure documents are already ingested so the vector DB has chunks
python -m ingestion.ingest --documents ./data
```

Questions live in `data/eval_questions.json` (edit or replace with your own).

### 1. Vector DB comparison

Run the **same embedded chunks** against each vector DB, one at a time. `--load-from-pg`
copies the chunks already stored in pgvector into Qdrant and ChromaDB so the comparison is
fair (it is a no-op for pgvector):

```bash
python -m benchmark \
  --backends pgvector qdrant chroma \
  --load-from-pg \
  --llms mistral \
  --output results/comparison_summary.csv
```

Each backend contributes rows for every question × mode (`vector`, `graph`, `hybrid`) with
its `retrieval_latency_ms`.

### 2. Multi-LLM comparison

Compare several LLMs on identical retrieved context (local Ollama models and/or
OpenAI-compatible APIs configured in `.env`):

```bash
python -m benchmark \
  --backends pgvector \
  --llms mistral llama3 \
  --output results/comparison_summary.csv
```

### 3. Combined comparison (all backends × all LLMs)

```bash
python -m benchmark \
  --backends pgvector qdrant chroma --load-from-pg \
  --llms mistral llama3 \
  --modes vector graph hybrid \
  --output results/comparison_summary.csv
```

### Output

`results/comparison_summary.csv` columns:

| Column | Meaning |
|--------|---------|
| `backend` | Vector DB used (pgvector / qdrant / chroma) |
| `mode` | Retrieval mode (vector / graph / hybrid) |
| `question_id`, `question` | The evaluation question |
| `llm_model` | LLM that generated the answer |
| `retrieval_latency_ms` | Retrieval time for that backend+mode |
| `generation_latency_ms` | LLM generation time |
| `prompt_tokens`, `completion_tokens`, `total_tokens` | Token usage (blank if unreported) |
| `num_context_chunks` | Chunks included in the shared context |
| `answer` | Generated answer |
| `error` | Any per-cell error (run continues on failure) |

### Useful flags

```bash
python -m benchmark --help
#   --backends {pgvector,qdrant,chroma} ...
#   --llms MODEL [MODEL ...]
#   --modes {vector,graph,hybrid} ...
#   --questions PATH        (default: data/eval_questions.json)
#   --output PATH           (default: results/comparison_summary.csv)
#   --limit N               (max results per retrieval, default 5)
#   --text-weight FLOAT     (hybrid text weight 0-1, default 0.3)
#   --load-from-pg          (copy pgvector chunks into the selected backend)
#   --max-questions N       (quick run on first N questions)
```

Relevant `.env` settings: `VECTOR_BACKEND`, `EMBEDDING_DIMENSION`, `QDRANT_PATH`,
`QDRANT_IN_MEMORY`, `CHROMA_PATH`, `BENCHMARK_LLMS`, `BENCHMARK_LIMIT` (see `.env.example`).

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
