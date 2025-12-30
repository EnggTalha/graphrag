# 📊 Graph RAG Project Overview

## What This Project Does

This system ingests documents (PDF, Word, Excel, TXT, CSV, Markdown), splits them into semantic chunks, generates vector embeddings using OpenAI, and builds a knowledge graph in Neo4j. Users can query the system using natural language, and the AI agent searches both the vector database (for semantic similarity) and the knowledge graph (for relationships) to provide intelligent answers.

**New Feature**: Auto-Ingestion API automatically watches for new files and ingests them in real-time - no manual intervention needed!

## Key Components

- **LLM (OpenAI GPT-4.1-mini)**: Generates responses and extracts entities/relationships
- **Chunks**: Documents split into semantic pieces for better retrieval
- **Vector Embeddings**: 1536-dimensional vectors stored in PostgreSQL for similarity search
- **Knowledge Graph (Neo4j)**: Stores entities and relationships for graph traversal
- **Hybrid Search**: Combines vector similarity + graph relationships for better answers
- **Auto-Ingestion API**: Continuously watches `data/` folder and auto-ingests new files
- **Main API Server**: Handles queries and chat (port 8058)
- **Auto-Ingestion API**: Watches files and manages ingestion (port 8059)

## System Flow

```
┌─────────────┐
│  Documents  │  (PDF, Word, Excel, TXT, CSV, MD files in data/ folder)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│   Auto-Ingestion API (Port 8059)    │
│  • Watches data/ folder              │
│  • Detects new files automatically   │
│  • Queues files for processing       │
│  • Tracks ingestion history          │
└──────┬───────────────────────────────┘
       │
       ▼
┌─────────────────┐
│  File Parser    │  → Extracts text from PDF, Word, Excel, TXT, CSV, MD
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Chunker        │  → Splits into semantic chunks
│                 │  → Detects tabular data (Excel/CSV)
│                 │  → Uses fast simple chunking for tables
└──────┬──────────┘
       │
       ├─────────────────┬─────────────────┐
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Embeddings  │  │  LLM Extract │  │  Store Docs │
│  (OpenAI)    │  │  Entities    │  │  & Chunks   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Neo4j     │  │  PostgreSQL  │
│  (Vectors)   │  │ (Knowledge   │  │  (Metadata)  │
│              │  │    Graph)    │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │   User Query     │
              │  "What is...?"   │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Main API       │
              │   (Port 8058)    │
              │   AI Agent       │
              │  (Pydantic AI)   │
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Vector Search│ │ Graph Search │ │ Hybrid      │
│ (PostgreSQL) │ │   (Neo4j)    │ │  Search     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  LLM Response    │
              │  (GPT-4.1-mini)  │
              └──────────────────┘
```

## 🚀 Key Features

### 1. **Automatic File Ingestion**
- **Auto-Ingestion API** continuously watches the `data/` folder
- New files are automatically detected and ingested
- No manual intervention needed
- Supports: `.txt`, `.md`, `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.csv`
- Queue system handles multiple files efficiently

### 2. **Intelligent Document Processing**
- **Semantic Chunking**: Uses LLM to split documents intelligently
- **Tabular Data Detection**: Automatically detects Excel/CSV files for faster processing
- **Duplicate Prevention**: Skips already ingested files
- **Progress Tracking**: Detailed logging with time estimates
- **Error Handling**: Continues processing even if one file fails

### 3. **Hybrid Search**
- **Vector Search**: Semantic similarity search in PostgreSQL
- **Graph Search**: Relationship traversal in Neo4j
- **Hybrid Mode**: Combines both for comprehensive results

### 4. **Knowledge Graph**
- **Entity Extraction**: Automatically extracts entities from documents
- **Relationship Mapping**: Builds connections between entities
- **Temporal Data**: Tracks relationships over time
- **Graph Visualization**: View in Neo4j Browser (http://localhost:7474)

### 5. **REST APIs**
- **Main API** (port 8058): Chat, search, and query endpoints
- **Auto-Ingestion API** (port 8059): File watching, ingestion control, history

## Data Flow Summary

1. **Document Addition**: User adds files to `data/` folder
2. **Auto-Detection**: Auto-Ingestion API detects new files automatically
3. **Processing**: Ingestion pipeline processes files:
   - Parses file content (PDF, Excel, TXT, etc.)
   - Creates semantic chunks
   - Generates embeddings (OpenAI)
   - Extracts entities and relationships
4. **Storage**: 
   - Chunks + embeddings → PostgreSQL
   - Entities + relationships → Neo4j
5. **Query**: User asks questions via CLI
6. **Search**: AI Agent searches both databases
7. **Response**: LLM synthesizes answer from retrieved information

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Databases**: PostgreSQL (with pgvector), Neo4j
- **LLM**: OpenAI GPT-4.1-mini
- **Embeddings**: OpenAI text-embedding-3-small
- **Knowledge Graph**: Graphiti
- **File Watching**: Watchdog
- **Document Parsing**: pdfplumber, pandas, openpyxl, python-docx
- **Deployment**: Docker, Docker Compose

## 📚 Documentation Files

- `HOW_TO_RUN.md` - Quick start guide
- `SETUP_LINUX.md` - Detailed Linux setup
- `AUTO_INGESTION_GUIDE.md` - Auto-ingestion API guide
- `CHECK_DATA.md` - How to verify ingested data
- `INGESTION_IMPROVEMENTS.md` - Ingestion features
- `LOGGING_IMPROVEMENTS.md` - Logging details
- `QUICK_START.md` - Quick reference

## 🎯 Use Cases

- **Knowledge Base Q&A**: Ask questions about your documents
- **Document Search**: Find relevant information quickly
- **Relationship Discovery**: Explore connections between entities
- **Continuous Updates**: Automatically process new documents as they arrive
- **Research Assistant**: Get insights from large document collections

## 🔄 Auto-Ingestion Workflow

```
1. User adds file to data/ folder
   ↓
2. Auto-Ingestion API detects new file
   ↓
3. File added to ingestion queue
   ↓
4. Background processor ingests file:
   - Parse document
   - Create chunks
   - Generate embeddings
   - Extract entities
   - Build knowledge graph
   ↓
5. Data stored in PostgreSQL & Neo4j
   ↓
6. File immediately searchable via API
```

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Sources                          │
│  (PDF, Excel, TXT, MD, CSV files in data/ folder)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Auto-Ingestion API (Port 8059)                 │
│  • Watches data/ folder for new files                       │
│  • Automatically triggers ingestion                         │
│  • Queue system for multiple files                          │
│  • History tracking                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Ingestion Pipeline                             │
│  • File Parsing (PDF, Word, Excel, TXT, CSV, MD)            │
│  • Semantic Chunking                                        │
│  • Embedding Generation (OpenAI)                           │
│  • Entity & Relationship Extraction                        │
└──────┬──────────────────────────────┬───────────────────────┘
       │                              │
       ▼                              ▼
┌──────────────┐              ┌──────────────┐
│ PostgreSQL   │              │    Neo4j     │
│ (Vector DB)  │              │ (Graph DB)   │
│              │              │              │
│ • Chunks     │              │ • Entities   │
│ • Embeddings │              │ • Relations  │
└──────┬───────┘              └──────┬───────┘
       │                              │
       └──────────┬───────────────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │   Main API (8058)    │
       │  • Chat endpoints    │
       │  • Search tools      │
       │  • AI Agent          │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │   CLI Interface      │
       │  • Interactive chat  │
       │  • Query system      │
       └──────────────────────┘
```
