"""
Swappable vector-store adapters.

Public API:
    BaseVectorStore  - abstract interface all backends implement
    VectorRecord     - result contract (matches existing agent/db_utils dict shapes)
    create_vector_store(name, dimension, **settings) - factory (default: pgvector)

Optional backends (qdrant, chroma) are imported lazily by the factory, so importing this
package never requires qdrant-client or chromadb to be installed.
"""

from .base import DEFAULT_DIMENSION, BaseVectorStore, VectorRecord
from .factory import VALID_BACKENDS, create_vector_store

__all__ = [
    "BaseVectorStore",
    "VectorRecord",
    "DEFAULT_DIMENSION",
    "VALID_BACKENDS",
    "create_vector_store",
]
