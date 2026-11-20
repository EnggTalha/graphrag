"""
Factory for creating vector stores by name, with env-based defaults.

Optional backends (Qdrant, ChromaDB) are imported lazily inside their branch so that the
core app and the pgvector backend keep working even when those libraries are not installed.
"""

import os
from typing import Any, Optional

from .base import DEFAULT_DIMENSION, BaseVectorStore

VALID_BACKENDS = ("pgvector", "qdrant", "chroma")


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def create_vector_store(
    name: Optional[str] = None,
    dimension: Optional[int] = None,
    **settings: Any,
) -> BaseVectorStore:
    """
    Create a vector store.

    Args:
        name: Backend name (pgvector | qdrant | chroma). Defaults to the ``VECTOR_BACKEND``
            env var, then "pgvector".
        dimension: Embedding dimension. Defaults to ``EMBEDDING_DIMENSION`` env or 384.
        **settings: Backend-specific overrides (e.g. ``path``, ``in_memory``).

    Returns:
        A concrete ``BaseVectorStore``.
    """
    name = (name or os.getenv("VECTOR_BACKEND", "pgvector")).strip().lower()
    if dimension is None:
        dimension = int(os.getenv("EMBEDDING_DIMENSION", str(DEFAULT_DIMENSION)))

    if name == "pgvector":
        from .pgvector_store import PgVectorStore

        return PgVectorStore(dimension=dimension)

    if name == "qdrant":
        from .qdrant_store import QdrantStore

        path = settings.get("path", os.getenv("QDRANT_PATH", "./data/qdrant"))
        in_memory = settings.get(
            "in_memory", _as_bool(os.getenv("QDRANT_IN_MEMORY"), False)
        )
        return QdrantStore(dimension=dimension, path=path, in_memory=in_memory)

    if name == "chroma":
        from .chroma_store import ChromaStore

        path = settings.get("path", os.getenv("CHROMA_PATH", "./data/chroma"))
        return ChromaStore(dimension=dimension, path=path)

    raise ValueError(
        f"Unknown vector backend '{name}'. Valid options: {', '.join(VALID_BACKENDS)}"
    )
