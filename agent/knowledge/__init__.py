"""
Knowledge management components for semantic bug detection.

This package contains:
- KnowledgeBase: Manages bug pattern knowledge base
- EmbeddingModel: Generates embeddings for semantic similarity
- VectorStore: Stores and searches embeddings
"""

from .knowledge_base import KnowledgeBase, BugPattern, KnowledgeBaseStats
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

