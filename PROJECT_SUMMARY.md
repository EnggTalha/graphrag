# 🏢 Real Estate Q/A RAG System - Project Summary

## 📊 System Architecture Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                               │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   CLI Chat   │         │  FastAPI     │                      │
│  │  (cli.py)    │         │  Server      │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
└─────────┼────────────────────────┼─────────────────────────────┘
           │                        │
           └──────────┬─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              PYDANTIC AI AGENT (agent/agent.py)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Intelligent Tool Selection                            │  │
│  │  • OpenAI GPT-4o-mini                                     │  │
│  │  • Context-Aware Decision Making                          │  │
│  └───────┬───────────────────────┬──────────────────────────┘  │
└──────────┼───────────────────────┼──────────────────────────────┘
           │                       │
    ┌──────┘                       └──────┐
    ▼                                      ▼
┌──────────────────┐            ┌──────────────────┐
│   PostgreSQL     │            │      Neo4j       │
│   + pgvector     │            │   + Graphiti     │
│                  │            │                  │
│  Vector Search   │            │  Knowledge Graph │
│  • Semantic      │            │  • Entities      │
│  • Similarity    │            │  • Relationships │
│  • Embeddings    │            │  • Temporal      │
└──────────────────┘            └──────────────────┘
           │                              │
           └──────────┬───────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              DOCUMENT INGESTION PIPELINE                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Parse Documents (.txt, .md, .pdf, .xls, .csv)        │  │
│  │  2. Semantic Chunking                                     │  │
│  │  3. Generate Embeddings (OpenAI)                          │  │
│  │  4. Extract Entities & Relationships                      │  │
│  │  5. Store in PostgreSQL (Vector DB)                       │  │
│  │  6. Build Knowledge Graph in Neo4j                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔑 Key Definitions

### **RAG (Retrieval-Augmented Generation)**
- **What**: AI system that retrieves relevant documents before generating answers
- **Why**: Provides accurate, source-based responses instead of generic AI answers
- **How**: Searches your documents using semantic similarity

### **Vector Database (PostgreSQL + pgvector)**
- **What**: Stores document chunks as numerical vectors (embeddings)
- **Purpose**: Fast semantic search - finds documents by meaning, not keywords
- **Example**: Query "meeting about project delays" finds relevant meeting minutes

### **Knowledge Graph (Neo4j + Graphiti)**
- **What**: Stores entities (people, projects, properties) and their relationships
- **Purpose**: Understands connections between data points
- **Example**: "Who worked on Project X?" → Finds people connected to that project

### **Semantic Chunking**
- **What**: Intelligent document splitting that keeps related content together
- **Why**: Better context than simple text splitting
- **Result**: Chunks that make sense as standalone units

### **Embeddings**
- **What**: Numerical representations of text (vectors)
- **Purpose**: Enables similarity search - similar texts have similar vectors
- **Model**: OpenAI `text-embedding-3-small` (1536 dimensions)

### **Graphiti**
- **What**: Framework for building temporal knowledge graphs
- **Purpose**: Automatically extracts entities and relationships from text
- **Output**: Graph of connected entities with time-based information

## 🎯 What This System Does

### **Input**
- Real estate project documents
- Meeting minutes
- Property data
- Excel/PDF/CSV files

### **Processing**
1. **Chunks** documents intelligently
2. **Generates** embeddings for semantic search
3. **Extracts** entities (people, projects, properties)
4. **Builds** relationship graph
5. **Stores** in dual database system

### **Output**
- **Accurate Answers**: Based on your actual documents
- **Relationship Insights**: "Who worked with whom on what project?"
- **Temporal Context**: "What decisions were made in November?"
- **Source Citations**: Knows which document provided the answer

## 🔄 Data Flow

```
Documents → Chunking → Embeddings → PostgreSQL (Vector Search)
                ↓
         Entity Extraction → Knowledge Graph → Neo4j (Relationships)
                ↓
         User Query → Agent → Searches Both → Combined Answer
```

## 📦 Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI Agent** | Pydantic AI | Intelligent tool selection & reasoning |
| **LLM** | OpenAI GPT-4o-mini | Understanding queries & generating answers |
| **Vector DB** | PostgreSQL + pgvector | Semantic document search |
| **Graph DB** | Neo4j + Graphiti | Entity & relationship storage |
| **API** | FastAPI | RESTful API with streaming |
| **CLI** | Python CLI | Command-line interface |

## 🚀 Quick Start

```bash
# 1. Setup
python init_database.py              # Initialize PostgreSQL
python -m ingestion.ingest --clean   # Ingest documents

# 2. Run
python -m agent.api                  # Start API server
python cli.py                        # Start CLI chat
```

## 💡 Use Cases

✅ **"What projects are in our database?"**
- Searches vector DB for project mentions

✅ **"Who attended the November 6th meeting?"**
- Uses knowledge graph to find meeting participants

✅ **"What is the relationship between Project X and Project Y?"**
- Traverses graph to find connections

✅ **"Show me all decisions made about property ABC"**
- Combines vector search + graph traversal

## 📈 System Capabilities

- ✅ **Multi-format Support**: .txt, .md, .pdf, .xls, .xlsx, .csv
- ✅ **Hybrid Search**: Vector + Graph for comprehensive results
- ✅ **Conversation History**: JSON-based storage (no PostgreSQL needed)
- ✅ **Streaming Responses**: Real-time answer generation
- ✅ **Source Citations**: Knows which documents provided answers
- ✅ **Temporal Awareness**: Understands time-based relationships

## 🎓 Technical Stack

```
Frontend:    CLI / FastAPI
Agent:       Pydantic AI
LLM:         OpenAI GPT-4o-mini
Embeddings:  OpenAI text-embedding-3-small
Vector DB:   PostgreSQL + pgvector
Graph DB:    Neo4j + Graphiti
Storage:     JSON (conversations)
```

---

**Project Location**: `D:\Novatech\Graph RAG\ottomator-agents\agentic-rag-knowledge-graph`  
**Last Updated**: December 23, 2025
