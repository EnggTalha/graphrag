"""
Qdrant vector store adapter (local on-disk path or in-memory).

Uses ``qdrant-client`` embedded mode, so no external server is required. The client library
is synchronous; calls are offloaded to threads to keep the async interface. Hybrid search
blends the native cosine score with a dependency-free client-side keyword score so the
result contract matches the pgvector backend.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    BaseVectorStore,
    VectorRecord,
    chunk_attr,
    clamp01,
    text_overlap_score,
)

logger = logging.getLogger(__name__)

COLLECTION = "graphrag_chunks"


class QdrantStore(BaseVectorStore):
    name = "qdrant"

    def __init__(
        self,
        dimension: int = 384,
        path: Optional[str] = None,
        in_memory: bool = False,
    ) -> None:
        super().__init__(dimension=dimension)
        self.path = path
        self.in_memory = in_memory
        self._client = None
        self._models = None

    async def initialize(self) -> None:
        if self._client is not None:
            return
        try:
            from qdrant_client import QdrantClient, models
        except ImportError as exc:  # pragma: no cover - exercised only when selected
            raise ImportError(
                "The 'qdrant' backend requires qdrant-client. "
                "Install it with: pip install qdrant-client"
            ) from exc

        self._models = models

        def _build():
            if self.in_memory:
                client = QdrantClient(location=":memory:")
            else:
                client = QdrantClient(path=self.path or "./data/qdrant")
            existing = {c.name for c in client.get_collections().collections}
            if COLLECTION not in existing:
                client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=models.VectorParams(
                        size=self.dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
            return client

        self._client = await asyncio.to_thread(_build)

    async def close(self) -> None:
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None

    async def add_document(
        self,
        title: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        # Qdrant has no separate document table; document id is generated here and
        # carried in each chunk payload.
        return str(uuid.uuid4())

    async def add_chunks(
        self,
        document_id: str,
        title: str,
        source: str,
        chunks: Sequence[Any],
    ) -> int:
        await self.initialize()
        models = self._models
        points = []
        for chunk in chunks:
            embedding = chunk_attr(chunk, "embedding")
            if not embedding:
                continue
            raw_id = chunk_attr(chunk, "chunk_id") or str(uuid.uuid4())
            point_id = _as_point_id(raw_id)
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=list(embedding),
                    payload={
                        "chunk_id": str(raw_id),
                        "document_id": document_id,
                        "content": chunk_attr(chunk, "content", ""),
                        "chunk_index": chunk_attr(chunk, "index", 0),
                        "metadata": chunk_attr(chunk, "metadata", {}) or {},
                        "token_count": chunk_attr(chunk, "token_count"),
                        "document_title": title,
                        "document_source": source,
                    },
                )
            )
        if not points:
            return 0
        await asyncio.to_thread(
            self._client.upsert, collection_name=COLLECTION, points=points
        )
        return len(points)

    async def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[VectorRecord]:
        await self.initialize()
        hits = await asyncio.to_thread(
            self._client.search,
            collection_name=COLLECTION,
            query_vector=list(embedding),
            limit=limit,
            with_payload=True,
        )
        return [_hit_to_record(h) for h in hits]

    async def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3,
    ) -> List[VectorRecord]:
        await self.initialize()
        candidate_n = max(limit * 4, 20)
        hits = await asyncio.to_thread(
            self._client.search,
            collection_name=COLLECTION,
            query_vector=list(embedding),
            limit=candidate_n,
            with_payload=True,
        )
        records: List[VectorRecord] = []
        for h in hits:
            payload = h.payload or {}
            vec_sim = clamp01(h.score)
            text_sim = text_overlap_score(query_text, payload.get("content", ""))
            combined = vec_sim * (1.0 - text_weight) + text_sim * text_weight
            rec = _payload_to_record(payload)
            rec["vector_similarity"] = vec_sim
            rec["text_similarity"] = text_sim
            rec["combined_score"] = combined
            records.append(rec)
        records.sort(key=lambda r: r.get("combined_score", 0.0), reverse=True)
        return records[:limit]

    async def count(self) -> int:
        await self.initialize()
        result = await asyncio.to_thread(
            self._client.count, collection_name=COLLECTION, exact=True
        )
        return int(result.count)

    async def clear(self) -> None:
        await self.initialize()
        models = self._models

        def _recreate():
            self._client.delete_collection(collection_name=COLLECTION)
            self._client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(
                    size=self.dimension, distance=models.Distance.COSINE
                ),
            )

        await asyncio.to_thread(_recreate)


def _as_point_id(raw_id: Any):
    """Qdrant point ids must be int or UUID; coerce arbitrary chunk ids to a UUID."""
    try:
        return str(uuid.UUID(str(raw_id)))
    except (ValueError, AttributeError, TypeError):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(raw_id)))


def _payload_to_record(payload: Dict[str, Any]) -> VectorRecord:
    return {
        "chunk_id": payload.get("chunk_id", ""),
        "document_id": payload.get("document_id", ""),
        "content": payload.get("content", ""),
        "metadata": payload.get("metadata", {}) or {},
        "document_title": payload.get("document_title"),
        "document_source": payload.get("document_source"),
    }


def _hit_to_record(hit) -> VectorRecord:
    rec = _payload_to_record(hit.payload or {})
    rec["similarity"] = clamp01(hit.score)
    return rec
