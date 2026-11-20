# Requirements: Modular Vector DB Adapter + Multi-LLM Benchmark

## Overview

Add a modular benchmarking extension to the Graph-RAG system without removing or
altering existing functionality. The extension has three parts:

1. A swappable vector-store abstraction so the same embedded chunks can run against
   PostgreSQL+pgvector (default), Qdrant (local/in-memory), and ChromaDB (persistent
   local directory), one backend at a time.
2. A benchmark runner that evaluates vector-only, graph-only, and hybrid retrieval
   across each configured vector DB and each configured LLM, recording latency,
   token usage, and answers.
3. Documentation describing the exact commands to run both comparisons.

Neo4j knowledge-graph retrieval must remain unchanged.

## Terminology

- **Vector store / vector DB**: the backend that stores chunk embeddings and serves
  similarity search (pgvector today; Qdrant and ChromaDB added here).
- **Chunk**: a text segment with an embedding (384-dim `all-MiniLM-L6-v2`), content,
  chunk index, token count, and metadata, belonging to a document.
- **Retrieval mode**: one of `vector`, `graph`, `hybrid`.
- **Backend / adapter**: a concrete implementation of the `BaseVectorStore` interface.

## Requirements

### R1 — BaseVectorStore interface
**User story:** As a developer, I want a single vector-store interface so I can swap
backends without touching retrieval or ingestion call sites.

Acceptance criteria:
1. WHEN the system needs to write or read chunk vectors THEN it SHALL go through a
   `BaseVectorStore` abstract interface that defines, at minimum:
   `initialize()`, `close()`, `add_document(...)`, `add_chunks(...)`,
   `vector_search(embedding, limit)`, `hybrid_search(embedding, query_text, limit, text_weight)`,
   `count()`, and `clear()`.
2. The interface SHALL define a stable result contract: `vector_search` returns records
   with keys `chunk_id, document_id, content, similarity, metadata, document_title, document_source`;
   `hybrid_search` returns those plus `combined_score, vector_similarity, text_similarity`.
   This matches the dict shapes already consumed by `agent/tools.py`.
3. The interface SHALL accept embeddings as `List[float]` of the configured dimension
   (default 384) and SHALL not hardcode a provider.

### R2 — pgvector adapter is the default and preserves current behavior
**User story:** As an existing user, I want nothing to change by default.

Acceptance criteria:
1. WHEN no backend is configured THEN the system SHALL use the pgvector backend.
2. The pgvector backend SHALL delegate to the existing `match_chunks` / `hybrid_search`
   SQL functions and existing `documents`/`chunks` tables, producing identical results
   to today.
3. Existing modules (`agent/db_utils.py`, `agent/tools.py`, `ingestion/ingest.py`) SHALL
   continue to work; the pgvector adapter SHALL reuse the existing `db_pool` and SQL.
4. No existing public function SHALL be deleted or have its signature broken.

### R3 — Qdrant local adapter
**User story:** As a developer, I want to benchmark Qdrant locally without a server.

Acceptance criteria:
1. The Qdrant adapter SHALL support local on-disk storage (`path=...`) and in-memory
   (`:memory:`) modes via `qdrant-client`, requiring no external service.
2. It SHALL create a collection sized to the embedding dimension with cosine distance.
3. It SHALL implement `vector_search` and a `hybrid_search` that returns the same record
   keys as R1.2 (text component may be computed client-side so the contract holds even
   where the backend lacks native full-text scoring).
4. It SHALL store enough payload (content, document_id, title, source, chunk_index,
   metadata) to reconstruct the result contract.

### R4 — ChromaDB persistent adapter
**User story:** As a developer, I want to benchmark ChromaDB with a persistent local dir.

Acceptance criteria:
1. The ChromaDB adapter SHALL use a `PersistentClient` pointed at a configurable local
   directory and require no external service.
2. It SHALL use cosine space and store the same payload as R3.4.
3. It SHALL implement `vector_search` and `hybrid_search` with the R1.2 contract.

### R5 — Backend selection / factory
**User story:** As an operator, I want to pick a backend by name.

Acceptance criteria:
1. A factory SHALL create a `BaseVectorStore` from a backend name
   (`pgvector` | `qdrant` | `chroma`) plus optional settings, defaulting to `pgvector`.
2. Backend name and per-backend settings (paths, dimension) SHALL be configurable via
   environment variables (e.g. `VECTOR_BACKEND`, `QDRANT_PATH`, `CHROMA_PATH`) with
   sensible defaults, without breaking existing env usage.
3. The benchmark SHALL be able to iterate configured backends one at a time, loading the
   same embedded chunks into each.

### R6 — Missing optional dependencies degrade gracefully
Acceptance criteria:
1. IF `qdrant-client` or `chromadb` is not installed THEN importing the core app and
   running pgvector SHALL still work, and the missing backend SHALL raise a clear,
   actionable error only when that backend is actually selected.

### R7 — Evaluation question set
**User story:** As an evaluator, I want to define questions in a JSON file.

Acceptance criteria:
1. The runner SHALL load questions from `data/eval_questions.json`.
2. Each entry SHALL support at least a `question` string and an optional `id` and
   optional `expected`/`notes` field; unknown fields SHALL be ignored.
3. A sample `data/eval_questions.json` SHALL be provided.

### R8 — Retrieval benchmark across modes and backends
**User story:** As an evaluator, I want per-backend retrieval latency for each mode.

Acceptance criteria:
1. For each configured vector backend and each question, the runner SHALL run
   `vector`-only, `graph`-only, and `hybrid` retrieval.
2. It SHALL measure retrieval latency in milliseconds per (backend, mode, question).
3. Graph retrieval SHALL use the existing Neo4j path unchanged; graph latency is recorded
   independent of the vector backend (the same graph store serves all rows).
4. The same embedded chunks SHALL be used across backends so comparisons are fair.

### R9 — Multi-LLM generation benchmark
**User story:** As an evaluator, I want to compare LLMs on identical retrieved context.

Acceptance criteria:
1. The runner SHALL read a configurable list of LLMs (local Ollama models such as
   `mistral`/`llama3` and OpenAI-compatible APIs via `.env`).
2. For each (backend, mode, question, LLM), the runner SHALL build a prompt from the SAME
   retrieved context and call the LLM.
3. It SHALL record generation latency (ms), token usage (prompt/response/total when the
   provider reports it; blank/0 otherwise), and the generated answer.
4. LLM selection SHALL reuse the existing `OpenAIProvider`/`OpenAIModel` wiring so Ollama
   and OpenAI-compatible endpoints both work via base URL + model name.

### R10 — Results output
Acceptance criteria:
1. The runner SHALL write `results/comparison_summary.csv`.
2. Each row SHALL include at least: `backend, mode, question_id, question, llm_model,
   retrieval_latency_ms, generation_latency_ms, prompt_tokens, completion_tokens,
   total_tokens, num_context_chunks, answer, error`.
3. The runner SHALL not crash the whole run on a single failing cell; it SHALL record the
   error in that row and continue.

### R11 — Non-functional
Acceptance criteria:
1. The extension SHALL live under `agent/vector_store/` and `benchmark/` and SHALL not
   require changes that break `python -m agent.api`, `python cli.py`, or
   `python -m ingestion.ingest`.
2. New third-party deps (`qdrant-client`, `chromadb`) SHALL be added to
   `requirements.txt` and documented as optional for benchmarking.
3. README SHALL document the exact commands to run the Vector DB comparison and the LLM
   comparison.
