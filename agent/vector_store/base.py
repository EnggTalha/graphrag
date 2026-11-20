"""
Abstract base interface for swappable vector stores.

All concrete backends (pgvector, Qdrant, ChromaDB) implement this interface so the
same embedded chunks can be stored in and queried from any backend one at a time,
while keeping the result contract identical to what ``agent/tools.py`` already consumes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, TypedDict


# Default embedding dimension for all-MiniLM-L6-v2 (the model used across this project).
DEFAULT_DIMENSION = 384


class VectorRecord(TypedDict, total=False):
    """
    Result contract returned by all vector stores.

    ``vector_search`` populates ``similarity``; ``hybrid_search`` additionally populates
    ``combined_score``, ``vector_similarity`` and ``text_similarity``. These keys match the
    dict shapes produced by the existing ``agent/db_utils`` functions, so downstream
    mapping in ``agent/tools.py`` works unchanged regardless of backend.
    """

    chunk_id: str
    document_id: str
    content: str
    similarity: float
    combined_score: float
    vector_similarity: float
    text_similarity: float
    metadata: Dict[str, Any]
    document_title: Optional[str]
    document_source: Optional[str]


class ChunkInput(TypedDict, total=False):
    """Normalized shape accepted by ``add_chunks``."""

    chunk_id: str
    content: str
    index: int
    embedding: List[float]
    metadata: Dict[str, Any]
    token_count: Optional[int]


class BaseVectorStore(ABC):
    """Abstract vector store. All methods are async to match the asyncpg/neo4j codebase."""

    #: Human-readable backend name, e.g. "pgvector", "qdrant", "chroma".
    name: str = "base"

    def __init__(self, dimension: int = DEFAULT_DIMENSION) -> None:
        self.dimension = dimension

    @abstractmethod
    async def initialize(self) -> None:
        """Open connections / create collections. Safe to call more than once."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""

    @abstractmethod
    async def add_document(
        self,
        title: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist a document and return its id (UUID string)."""

    @abstractmethod
    async def add_chunks(
        self,
        document_id: str,
        title: str,
        source: str,
        chunks: Sequence[Any],
    ) -> int:
        """
        Persist chunk embeddings for a document.

        ``chunks`` may be objects (with ``.content``, ``.index``, ``.embedding``,
        ``.metadata``, ``.token_count``) or dicts with the same keys. Returns the number
        of chunks written.
        """

    @abstractmethod
    async def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[VectorRecord]:
        """Pure vector similarity search ordered best-first."""

    @abstractmethod
    async def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3,
    ) -> List[VectorRecord]:
        """Combined vector + keyword search ordered best-first."""

    @abstractmethod
    async def count(self) -> int:
        """Return the number of stored chunks."""

    @abstractmethod
    async def clear(self) -> None:
        """Delete all stored chunks/documents for this backend."""


# -- helpers shared by concrete adapters -------------------------------------------------


def chunk_attr(chunk: Any, name: str, default: Any = None) -> Any:
    """Read ``name`` from a chunk whether it is an object or a dict."""
    if isinstance(chunk, dict):
        return chunk.get(name, default)
    return getattr(chunk, name, default)


def clamp01(value: float) -> float:
    """Clamp a score into [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def text_overlap_score(query_text: str, content: str) -> float:
    """
    Lightweight, dependency-free keyword relevance in [0, 1].

    Used by backends without native full-text scoring (Qdrant, Chroma) so their
    ``hybrid_search`` can return the same contract as pgvector. Not meant to replicate
    Postgres ``ts_rank_cd`` exactly, only to provide a comparable, reproducible blend.
    """
    if not query_text or not content:
        return 0.0
    q_tokens = {t for t in _tokenize(query_text) if len(t) > 2}
    if not q_tokens:
        return 0.0
    c_tokens = _tokenize(content)
    if not c_tokens:
        return 0.0
    c_set = set(c_tokens)
    matched = sum(1 for t in q_tokens if t in c_set)
    return clamp01(matched / len(q_tokens))


def _tokenize(text: str) -> List[str]:
    out: List[str] = []
    token = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            out.append("".join(token))
            token = []
    if token:
        out.append("".join(token))
    return out
