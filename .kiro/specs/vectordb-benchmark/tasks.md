# Tasks: Modular Vector DB Adapter + Multi-LLM Benchmark

- [ ] 1. Vector store package scaffold and interface
  - Create `agent/vector_store/__init__.py`, `base.py` with `BaseVectorStore` ABC and
    `VectorRecord` contract.
  - _Requirements: R1_

- [ ] 2. pgvector adapter (default, no behavior change)
  - `agent/vector_store/pgvector_store.py` delegating to existing `agent/db_utils`
    functions and SQL; `add_document`/`add_chunks` replicate `_save_to_postgres` SQL.
  - _Requirements: R2_

- [ ] 3. Qdrant local adapter
  - `agent/vector_store/qdrant_store.py` using `qdrant-client` (path / `:memory:`),
    cosine collection sized to dimension, contract-compliant vector + hybrid search.
  - _Requirements: R3_

- [ ] 4. ChromaDB persistent adapter
  - `agent/vector_store/chroma_store.py` using `PersistentClient`, cosine space,
    contract-compliant vector + hybrid search.
  - _Requirements: R4_

- [ ] 5. Factory and env-based selection with graceful optional-dep handling
  - `agent/vector_store/factory.py::create_vector_store(name, dimension, **settings)`
    with lazy imports; `VECTOR_BACKEND`, `QDRANT_PATH`, `CHROMA_PATH` env.
  - _Requirements: R5, R6_

- [ ] 6. Evaluation questions file + loader
  - Sample `data/eval_questions.json`; `benchmark/questions.py` loader/normalizer.
  - _Requirements: R7_

- [ ] 7. Retrieval benchmarking (vector/graph/hybrid + latency)
  - `benchmark/retrieval.py`: shared embedding, three modes, `perf_counter` latency,
    graph via unchanged Neo4j path, shared context builder.
  - _Requirements: R8_

- [ ] 8. Multi-LLM generation benchmarking
  - `benchmark/llm_runner.py`: model build via `get_llm_model`, identical-context prompt,
    latency + token usage capture (defensive `result.usage()`).
  - _Requirements: R9_

- [ ] 9. Runner + CSV output + CLI
  - `benchmark/config.py`, `benchmark/runner.py`, `benchmark/__main__.py`; iterate
    backends×questions×modes×LLMs; `--load-from-pg`; write `results/comparison_summary.csv`;
    per-cell error isolation.
  - _Requirements: R8, R9, R10, R5_

- [ ] 10. Dependencies, env example, results dir
  - Add `qdrant-client`, `chromadb` to `requirements.txt` (optional section); add new vars
    to `.env.example`; add `results/.gitkeep`.
  - _Requirements: R11.2, R5.2_

- [ ] 11. Documentation
  - Update `README.md` with exact Vector DB comparison and LLM comparison commands.
  - _Requirements: R11.3_

- [ ] 12. Verification
  - `py_compile` all new modules; import package with optional deps absent; in-memory
    adapter smoke check for contract keys (skips if libs missing); confirm existing
    modules still import.
  - _Requirements: R11.1, R6_
