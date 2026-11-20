"""
Default vector store backed by PostgreSQL + pgvector.

This adapter delegates reads to the existing ``agent.db_utils`` functions and the existing
``match_chunks`` / ``hybrid_search`` SQL functions, so its behavior is identical to the
current system. Writes replicate the exact SQL used by
``ingestion.ingest.DocumentIngestionPipeline._save_to_postgres`` so the benchmark can also
load chunks through the adapter. The production ingestion path is left unchanged.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from .base import BaseVectorStore, VectorRecord, chunk_attr

logger = logging.getLogger(__name__)


class PgVectorStore(BaseVectorStore):
    name = "pgvector"

    async def initialize(self) -> None:
        # Reuse the shared asyncpg pool used by the rest of the app.
        from ..db_utils import db_pool

        if db_pool.pool is None:
            await db_pool.initialize()

    async def close(self) -> None:
        # The pool is shared process-wide; the app lifecycle owns closing it.
        # Intentionally a no-op so the benchmark does not tear down a pool others use.
        return None

    async def add_document(
        self,
        title: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        from ..db_utils import db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (title, source, content, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id::text
                """,
                title,
                source,
                content,
                json.dumps(metadata or {}),
            )
            return row["id"]

    async def add_chunks(
        self,
        document_id: str,
        title: str,
        source: str,
        chunks: Sequence[Any],
    ) -> int:
        from ..db_utils import db_pool

        written = 0
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                for chunk in chunks:
                    embedding = chunk_attr(chunk, "embedding")
                    embedding_data = None
                    if embedding:
                        embedding_data = "[" + ",".join(map(str, embedding)) + "]"
                    await conn.execute(
                        """
                        INSERT INTO chunks
                            (document_id, content, embedding, chunk_index, metadata, token_count)
                        VALUES ($1::uuid, $2, $3::vector, $4, $5::jsonb, $6)
                        """,
                        document_id,
                        chunk_attr(chunk, "content", ""),
                        embedding_data,
                        chunk_attr(chunk, "index", 0),
                        json.dumps(chunk_attr(chunk, "metadata", {}) or {}),
                        chunk_attr(chunk, "token_count"),
                    )
                    written += 1
        return written

    async def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[VectorRecord]:
        # Delegate to the unchanged existing implementation.
        from ..db_utils import vector_search as _vector_search

        return await _vector_search(embedding=embedding, limit=limit)

    async def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3,
    ) -> List[VectorRecord]:
        from ..db_utils import hybrid_search as _hybrid_search

        return await _hybrid_search(
            embedding=embedding,
            query_text=query_text,
            limit=limit,
            text_weight=text_weight,
        )

    async def count(self) -> int:
        from ..db_utils import db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*)::int AS n FROM chunks")
            return int(row["n"])

    async def clear(self) -> None:
        from ..db_utils import db_pool

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM chunks")
                await conn.execute("DELETE FROM documents")

    async def iter_all_chunks(self) -> List[Dict[str, Any]]:
        """
        Read every stored chunk (with embedding) so it can be loaded into another backend.

        Returns dicts shaped like ``ChunkInput`` plus ``document_id``/``title``/``source``.
        Used by the benchmark's ``--load-from-pg`` option.
        """
        from ..db_utils import db_pool

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.id::text        AS chunk_id,
                    c.document_id::text AS document_id,
                    c.content         AS content,
                    c.chunk_index     AS chunk_index,
                    c.metadata        AS metadata,
                    c.token_count     AS token_count,
                    c.embedding::text AS embedding,
                    d.title           AS document_title,
                    d.source          AS document_source
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.document_id, c.chunk_index
                """
            )

        out: List[Dict[str, Any]] = []
        for r in rows:
            emb = _parse_pg_vector(r["embedding"])
            md = r["metadata"]
            if isinstance(md, str):
                try:
                    md = json.loads(md)
                except Exception:
                    md = {}
            out.append(
                {
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "content": r["content"],
                    "index": r["chunk_index"],
                    "metadata": md or {},
                    "token_count": r["token_count"],
                    "embedding": emb,
                    "document_title": r["document_title"],
                    "document_source": r["document_source"],
                }
            )
        return out


def _parse_pg_vector(text: Optional[str]) -> List[float]:
    """Parse pgvector text form ``[1.0,2.0,...]`` into a list of floats."""
    if not text:
        return []
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return []
    return [float(x) for x in text.split(",") if x != ""]
