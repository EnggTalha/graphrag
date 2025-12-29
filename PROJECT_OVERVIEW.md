# 📊 Graph RAG Project Overview

## What This Project Does

This system ingests documents (PDF, Excel, TXT), splits them into semantic chunks, generates vector embeddings using OpenAI, and builds a knowledge graph in Neo4j. Users can query the system using natural language, and the AI agent searches both the vector database (for semantic similarity) and the knowledge graph (for relationships) to provide intelligent answers.

## Key Components

- **LLM (OpenAI GPT-4.1-mini)**: Generates responses and extracts entities/relationships
- **Chunks**: Documents split into semantic pieces for better retrieval
- **Vector Embeddings**: 1536-dimensional vectors stored in PostgreSQL for similarity search
- **Knowledge Graph (Neo4j)**: Stores entities and relationships for graph traversal
- **Hybrid Search**: Combines vector similarity + graph relationships for better answers

## System Flow

```
┌─────────────┐
│  Documents  │  (PDF, Excel, TXT files in data/ folder)
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  File Parser    │  → Extracts text from various formats
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Chunker        │  → Splits into semantic chunks
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

## Data Flow Summary

1. **Ingestion**: Documents → Chunks → Embeddings + Entities
2. **Storage**: Embeddings → PostgreSQL | Entities/Relations → Neo4j
3. **Query**: User Question → Agent → Vector/Graph Search → LLM → Answer

