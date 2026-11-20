"""
ChromaDB vector store adapter (persistent local directory).

Uses ``chromadb.PersistentClient`` so data lives in a local directory with no external
service. The client is synchronous; calls are offloaded to threads. Chroma metadata values
must be scalars, so nested metadata is JSON-encoded under ``metadata_json``. Hybrid search
blends the cosine similarity with a client-side keyword score to match the result contract.
"""

import asyncio
import json
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


class ChromaStore(BaseVectorStore):
    name = "chroma"

    def __init__(self, dimension: int = 384, path: Optional[str] = None) -> None:
        super().__init__(dimension=dimension)
        self.path = path or "./data/chroma"
        self._client = None
        self._collection = None

    async def initialize(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - exercised only when selected
            raise ImportError(
                "The 'chroma' backend requires chromadb. "
                "Install it with: pip install chromadb"
            ) from exc

        def _build():
            client = chromadb.PersistentClient(path=self.path)
            collection = client.get_or_create_collection(
                name=COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            return client, collection

        self._client, self._collection = await asyncio.to_thread(_build)

    async def close(self) -> None:
        # PersistentClient persists on write; nothing to close explicitly.
        self._collection = None
        self._client = None

    async def add_document(
        self,
        title: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return str(uuid.uuid4())

    async def add_chunks(
        self,
        document_id: str,
        title: str,
        source: str,
        chunks: Sequence[Any],
    ) -> int:
        await self.initialize()
        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            embedding = chunk_attr(chunk, "embedding")
            if not embedding:
                continue
            chunk_id = str(chunk_attr(chunk, "chunk_id") or uuid.uuid4())
            ids.append(chunk_id)
            embeddings.append(list(embedding))
            documents.append(chunk_attr(chunk, "content", ""))
            metadatas.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "chunk_index": chunk_attr(chunk, "index", 0),
                    "token_count": chunk_attr(chunk, "token_count") or 0,
                    "document_title": title or "",
                    "document_source": source or "",
                    "metadata_json": json.dumps(chunk_attr(chunk, "metadata", {}) or {}),
                }
            )

        if not ids:
            return 0

        await asyncio.to_thread(
            self._collection.add,
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(ids)

    async def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[VectorRecord]:
        await self.initialize()
        res = await asyncio.to_thread(
            self._collection.query,
            query_embeddings=[list(embedding)],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        records: List[VectorRecord] = []
        for doc, meta, dist in _iter_chroma_rows(res):
            rec = _meta_to_record(meta, doc)
            rec["similarity"] = _distance_to_similarity(dist)
            records.append(rec)
        return records

    async def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3,
    ) -> List[VectorRecord]:
        await self.initialize()
        candidate_n = max(limit * 4, 20)
        res = await asyncio.to_thread(
            self._collection.query,
            query_embeddings=[list(embedding)],
            n_results=candidate_n,
            include=["documents", "metadatas", "distances"],
        )
        records: List[VectorRecord] = []
        for doc, meta, dist in _iter_chroma_rows(res):
            vec_sim = _distance_to_similarity(dist)
            text_sim = text_overlap_score(query_text, doc or "")
            combined = vec_sim * (1.0 - text_weight) + text_sim * text_weight
            rec = _meta_to_record(meta, doc)
            rec["vector_similarity"] = vec_sim
            rec["text_similarity"] = text_sim
            rec["combined_score"] = combined
            records.append(rec)
        records.sort(key=lambda r: r.get("combined_score", 0.0), reverse=True)
        return records[:limit]

    async def count(self) -> int:
        await self.initialize()
        return int(await asyncio.to_thread(self._collection.count))

    async def clear(self) -> None:
        await self.initialize()

        def _recreate():
            self._client.delete_collection(name=COLLECTION)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION, metadata={"hnsw:space": "cosine"}
            )

        await asyncio.to_thread(_recreate)


def _distance_to_similarity(distance: Optional[float]) -> float:
    """Chroma returns cosine distance (0 best). Convert to similarity in [0, 1]."""
    if distance is None:
        return 0.0
    return clamp01(1.0 - float(distance))


def _iter_chroma_rows(res: Dict[str, Any]):
    """Yield (document, metadata, distance) for the single-query Chroma response."""
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i in range(len(docs)):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        yield docs[i], meta or {}, dist


def _meta_to_record(meta: Dict[str, Any], content: str) -> VectorRecord:
    raw_meta = meta.get("metadata_json")
    try:
        nested = json.loads(raw_meta) if raw_meta else {}
    except Exception:
        nested = {}
    return {
        "chunk_id": meta.get("chunk_id", ""),
        "document_id": meta.get("document_id", ""),
        "content": content or "",
        "metadata": nested,
        "document_title": meta.get("document_title") or None,
        "document_source": meta.get("document_source") or None,
    }
