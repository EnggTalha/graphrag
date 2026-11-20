# Design: Modular Vector DB Adapter + Multi-LLM Benchmark

## Guiding constraints

- **Do not break existing functionality.** The current pgvector path
  (`agent/db_utils.vector_search` / `hybrid_search`, `ingestion/ingest._save_to_postgres`,
  `agent/tools.py`) stays callable and behaves identically by default.
- **Neo4j unchanged.** We only read graph results through existing
  `agent/graph_utils.search_knowledge_graph` and friends.
- **Match the existing result contract** so no mapping in `agent/tools.py` changes.

## Current state (verified)

- Embeddings: `all-MiniLM-L6-v2`, 384-dim, local SentenceTransformer
  (`agent/providers.get_embedding_client`). Three call sites embed text; the benchmark
  reuses `agent/tools.generate_embedding`.
- pgvector reads: `agent/db_utils.vector_search(embedding, limit)` →
  `SELECT * FROM match_chunks($1::vector,$2)`; `hybrid_search(embedding, query_text, limit,
  text_weight)` → `SELECT * FROM hybrid_search(...)`. Result dict keys are the contract.
- pgvector writes: `ingestion/ingest._save_to_postgres` inserts into `documents` then
  `chunks (document_id, content, embedding, chunk_index, metadata, token_count)`.
- LLM: `agent/providers.get_llm_model(model_choice)` builds
  `OpenAIModel(model_name=llm_choice, provider=OpenAIProvider(base_url=f"{OLLAMA_BASE_URL}/v1"))`.
  pydantic-ai `result.usage()` exposes token counts but is currently unused.
- Graph: `agent/graph_utils` Neo4j client; `search_knowledge_graph(query)` returns episode
  dicts. Left untouched.

## Architecture

```
agent/vector_store/
  __init__.py          # exports BaseVectorStore, VectorRecord, create_vector_store
  base.py              # BaseVectorStore ABC + typed result contract
  pgvector_store.py    # default; wraps existing db_pool + match_chunks/hybrid_search SQL
  qdrant_store.py      # qdrant-client local path / :memory:
  chroma_store.py      # chromadb PersistentClient
  factory.py           # create_vector_store(name, **settings) + env resolution

benchmark/
  __init__.py
  config.py            # load backend list + LLM list from env/args
  questions.py         # load data/eval_questions.json
  llm_runner.py        # generate(context, question, model) -> answer + latency + tokens
  retrieval.py         # run vector/graph/hybrid against a given store; measure latency
  runner.py            # orchestrates, writes results/comparison_summary.csv
  __main__.py          # `python -m benchmark` entry (argparse)

data/eval_questions.json   # sample questions
results/                   # output dir (gitignored except .gitkeep)
```

### Why these seams

The adapter seam is the `vector_search` / `hybrid_search` pair plus the chunk write.
Wrapping exactly those keeps `agent/tools.py` → `ChunkResult` mapping and `agent/agent.py`
tools unaffected. pgvector adapter calls the existing `db_utils` functions directly, so the
default path is provably unchanged.

## Component design

### BaseVectorStore (base.py)

```python
class VectorRecord(TypedDict, total=False):
    chunk_id: str
    document_id: str
    content: str
    similarity: float          # vector_search
    combined_score: float      # hybrid_search
    vector_similarity: float   # hybrid_search
    text_similarity: float     # hybrid_search
    metadata: dict
    document_title: str
    document_source: str

class BaseVectorStore(ABC):
    name: str
    dimension: int
    async def initialize(self) -> None
    async def close(self) -> None
    async def add_document(self, title, source, content, metadata) -> str   # returns doc id
    async def add_chunks(self, document_id, title, source, chunks) -> int   # chunks: objs/dicts with content, index, embedding, metadata, token_count
    async def vector_search(self, embedding: list[float], limit: int = 10) -> list[VectorRecord]
    async def hybrid_search(self, embedding, query_text, limit=10, text_weight=0.3) -> list[VectorRecord]
    async def count(self) -> int
    async def clear(self) -> None
```

All methods are `async` to match the existing asyncpg/neo4j codebase. Synchronous client
libraries (qdrant, chroma) are wrapped with `asyncio.to_thread`.

### pgvector_store.py
- Reuses `agent.db_utils.db_pool`, `initialize_database`, `vector_search`, `hybrid_search`.
- `add_document` / `add_chunks` replicate the exact SQL from `_save_to_postgres` (so the
  benchmark can also load via the adapter) but the production ingestion path keeps calling
  `_save_to_postgres` directly — unchanged.
- `vector_search`/`hybrid_search` simply `return await db_utils.vector_search(...)` etc.
  Guarantees identical behavior.

### qdrant_store.py
- `QdrantClient(path=QDRANT_PATH)` or `location=":memory:"`.
- Collection `graphrag_chunks`, `VectorParams(size=dimension, distance=Distance.COSINE)`.
- Point id = chunk uuid; payload = content, document_id, document_title, document_source,
  chunk_index, metadata, token_count.
- `vector_search`: `client.search(...)`; similarity = cosine score (already 0..1-ish; clamp).
- `hybrid_search`: run vector search for `max(limit*4, 20)` candidates, compute a text score
  client-side (normalized token-overlap / simple BM25-lite over candidate content), then
  `combined = vec*(1-text_weight) + text*text_weight`; return top `limit` with all contract keys.
- Wrapped in `asyncio.to_thread`.

### chroma_store.py
- `chromadb.PersistentClient(path=CHROMA_PATH)`, collection `graphrag_chunks`
  with `metadata={"hnsw:space": "cosine"}`.
- `add` with ids, embeddings, documents (content), metadatas (flattened scalars; nested
  metadata JSON-encoded under `metadata_json`).
- `vector_search`: `collection.query(query_embeddings=[...], n_results=limit)`; convert
  Chroma cosine distance → similarity `1 - distance` (clamp to [0,1]).
- `hybrid_search`: same client-side blend approach as Qdrant for a consistent contract.
- Wrapped in `asyncio.to_thread`.

### factory.py
```python
def create_vector_store(name=None, dimension=384, **settings) -> BaseVectorStore
```
- `name` defaults to `os.getenv("VECTOR_BACKEND", "pgvector")`.
- Lazy-imports qdrant/chroma modules inside their branches so missing optional deps only
  error when that backend is selected (R6).
- Reads `QDRANT_PATH` (default `./data/qdrant`), `QDRANT_IN_MEMORY`, `CHROMA_PATH`
  (default `./data/chroma`).

## Benchmark design

### questions.py
Loads `data/eval_questions.json` (list of objects). Normalizes each to
`{id, question, expected?, notes?}`; auto-assigns `id` by index when missing.

### retrieval.py
- `embed(query)` via `agent.tools.generate_embedding` (one embedding reused across modes
  and backends for a question).
- `run_vector(store, embedding, limit)`, `run_hybrid(store, embedding, query, limit)`,
  `run_graph(query)` (calls `agent.graph_utils.search_knowledge_graph`).
- Each returns `(records, latency_ms)` using `time.perf_counter()`.
- Builds a context string from the top chunks (content truncated) shared with the LLM step.

### llm_runner.py
- `build_model(model_name)` → `agent.providers.get_llm_model(model_name)` (Ollama /
  OpenAI-compatible via base URL).
- Uses a minimal pydantic-ai `Agent(model, system_prompt=...)` per model (cached), calls
  `await agent.run(prompt)`, captures `result.output`, and `result.usage()` for
  `request_tokens`/`response_tokens`/`total_tokens` (guarded; blanks if unavailable).
- Returns `{answer, generation_latency_ms, prompt_tokens, completion_tokens, total_tokens}`.
- The prompt embeds the SAME retrieved context for every model so comparisons are fair.

### runner.py / __main__.py
Flow:
```
backends = resolve from --backends / VECTOR_BACKEND (default pgvector)
llms     = resolve from --llms / BENCHMARK_LLMS (default LLM_CHOICE)
questions = load data/eval_questions.json
for backend in backends:
    store = create_vector_store(backend); await store.initialize()
    (optional) if --load-from-pg, copy chunks from pgvector into this store
    for q in questions:
        emb = embed(q)
        for mode in [vector, graph, hybrid]:
            records, ret_ms = run_mode(...)
            context = build_context(records)   # graph context for graph mode
            for llm in llms:
                gen = llm_runner.generate(context, q, llm)
                write_row(...)
    await store.close()
write results/comparison_summary.csv
```
- `--load-from-pg` reads existing chunks from pgvector and upserts them into the selected
  backend so "the same embedded chunks" run against each DB (R8.4). For pgvector itself this
  is a no-op.
- CLI flags: `--backends`, `--llms`, `--questions`, `--output`, `--limit`, `--text-weight`,
  `--load-from-pg`, `--modes`, `--max-questions`.
- Robust per-cell try/except → `error` column; run continues (R10.3).

## Config / env additions (additive, non-breaking)
- `VECTOR_BACKEND=pgvector` (pgvector|qdrant|chroma)
- `QDRANT_PATH=./data/qdrant`, `QDRANT_IN_MEMORY=false`
- `CHROMA_PATH=./data/chroma`
- `BENCHMARK_LLMS=mistral` (comma-separated; e.g. `mistral,llama3`)
- `BENCHMARK_LIMIT=5`
- Existing vars reused: `DATABASE_URL`, `OLLAMA_BASE_URL`, `LLM_CHOICE`, `EMBEDDING_MODEL`,
  `NEO4J_*`.

## Dependencies
Add to `requirements.txt` (optional, for benchmarking): `qdrant-client`, `chromadb`.
pgvector path needs none of these.

## Testing / verification strategy
Full end-to-end requires Postgres+Neo4j+Ollama, unavailable in this sandbox. So:
- **Static**: `python -m py_compile` all new modules; import the package with optional deps
  absent to prove graceful import (R6, R11).
- **Behavioral smoke**: a self-contained check that exercises the Qdrant and Chroma adapters
  in `:memory:` / temp-dir mode with synthetic 384-dim vectors (if the libs are installed),
  asserting the result contract keys. Skipped cleanly if libs/not installed.
- **No-regression**: confirm existing modules still import and pgvector adapter only
  delegates to unchanged `db_utils` functions.

## Risks
- Chroma/Qdrant hybrid scoring is client-side and not identical to Postgres full-text; this
  is acceptable and documented — the goal is comparable, reproducible latency/answers, not
  identical ranking math across engines.
- `result.usage()` shape varies by pydantic-ai version; access is defensive.
