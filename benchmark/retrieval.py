"""
Retrieval benchmarking: run vector-only, graph-only, and hybrid retrieval and measure
latency. Vector/hybrid run against a supplied vector store; graph uses the existing,
unchanged Neo4j path.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from agent.vector_store import BaseVectorStore

logger = logging.getLogger(__name__)

# Max characters of a chunk's content included in the shared LLM context.
MAX_CHUNK_CHARS = 1200


@dataclass
class RetrievalOutcome:
    mode: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str = ""

    @property
    def num_results(self) -> int:
        return len(self.records)


async def embed_query(query: str) -> List[float]:
    """Embed the query once; reused across modes and backends for one question."""
    from agent.tools import generate_embedding

    return await generate_embedding(query)


async def run_vector(
    store: BaseVectorStore, embedding: List[float], limit: int
) -> RetrievalOutcome:
    start = time.perf_counter()
    try:
        records = await store.vector_search(embedding=embedding, limit=limit)
        elapsed = (time.perf_counter() - start) * 1000.0
        return RetrievalOutcome("vector", list(records), elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.warning("Vector retrieval failed: %s", exc)
        return RetrievalOutcome("vector", [], elapsed, str(exc))


async def run_hybrid(
    store: BaseVectorStore,
    embedding: List[float],
    query_text: str,
    limit: int,
    text_weight: float,
) -> RetrievalOutcome:
    start = time.perf_counter()
    try:
        records = await store.hybrid_search(
            embedding=embedding,
            query_text=query_text,
            limit=limit,
            text_weight=text_weight,
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        return RetrievalOutcome("hybrid", list(records), elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.warning("Hybrid retrieval failed: %s", exc)
        return RetrievalOutcome("hybrid", [], elapsed, str(exc))


async def run_graph(query_text: str, limit: int) -> RetrievalOutcome:
    """Graph-only retrieval via the unchanged Neo4j knowledge-graph path."""
    start = time.perf_counter()
    try:
        from agent.graph_utils import graph_client

        records = await graph_client.search(query_text, limit=limit)
        elapsed = (time.perf_counter() - start) * 1000.0
        return RetrievalOutcome("graph", list(records), elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.warning("Graph retrieval failed: %s", exc)
        return RetrievalOutcome("graph", [], elapsed, str(exc))


def build_context(outcome: RetrievalOutcome) -> str:
    """
    Build a single context string from retrieved records. The same string is passed to
    every LLM so generation comparisons are fair.
    """
    parts: List[str] = []
    for i, rec in enumerate(outcome.records, start=1):
        # Vector/hybrid records use 'content'; graph records also use 'content'.
        content = (rec.get("content") or "").strip()
        if not content:
            continue
        if len(content) > MAX_CHUNK_CHARS:
            content = content[:MAX_CHUNK_CHARS] + " ..."
        title = rec.get("document_title") or rec.get("source") or ""
        header = f"[{i}] {title}".strip()
        parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)
