"""
Knowledge management components for semantic bug detection.

This package contains:
- KnowledgeBase: Manages bug pattern knowledge base
- EmbeddingModel: Generates embeddings for semantic similarity
- VectorStore: Stores and searches embeddings
"""

from typing import TYPE_CHECKING

from .knowledge_base import KnowledgeBase, BugPattern, KnowledgeBaseStats

if TYPE_CHECKING:
    from .embedding_model import EmbeddingModel
    from .vector_store import VectorStore, SearchResult, VectorStoreStats

__all__ = [
    "KnowledgeBase",
    "BugPattern",
    "KnowledgeBaseStats",
    "EmbeddingModel",
    "VectorStore",
    "SearchResult",
    "VectorStoreStats",
]


def __getattr__(name):
    """Lazily resolve optional heavy modules to avoid import-time dependency errors."""
    if name == "EmbeddingModel":
        from .embedding_model import EmbeddingModel
        return EmbeddingModel
    if name in {"VectorStore", "SearchResult", "VectorStoreStats"}:
        from .vector_store import VectorStore, SearchResult, VectorStoreStats
        return {
            "VectorStore": VectorStore,
            "SearchResult": SearchResult,
            "VectorStoreStats": VectorStoreStats,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

