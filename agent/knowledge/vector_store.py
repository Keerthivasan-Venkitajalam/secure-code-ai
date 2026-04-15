"""
Vector Store for semantic bug detection.

This module provides persistent storage and efficient similarity search
for code embeddings using ChromaDB with HNSW indexing.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import chromadb
import numpy as np
from chromadb.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """
    Represents a single search result from the vector store.
    
    Attributes:
        id: Unique identifier of the result
        document: The original document text
        metadata: Associated metadata
        distance: Distance from query (lower is more similar)
        similarity: Similarity score (0-1, higher is more similar)
    """
    id: str
    document: str
    metadata: Dict[str, Any]
    distance: float
    similarity: float


@dataclass
class VectorStoreStats:
    """Statistics about the vector store"""
    collection_name: str
    document_count: int
    memory_usage_mb: float


class VectorStore:
    """
    Manages persistent storage and similarity search of embeddings using ChromaDB.
    
    Uses HNSW (Hierarchical Navigable Small World) index for efficient
    approximate nearest neighbor search with configurable memory limits.
    """
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "bug_patterns",
        max_memory_mb: int = 2048,
        hnsw_ef: int = 100
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection to use
            max_memory_mb: Maximum memory usage in MB (for monitoring)
            hnsw_ef: HNSW search_ef parameter (higher = better recall, slower)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.max_memory_mb = max_memory_mb
        self.hnsw_ef = hnsw_ef
        
        # Create persist directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection with optimized HNSW index
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity
                "hnsw:construction_ef": 200,  # Higher = better quality, slower build
                "hnsw:search_ef": hnsw_ef  # Configurable for performance tuning
            }
        )
        
        logger.info(
            f"Initialized vector store at {persist_directory} "
            f"with collection '{collection_name}' (hnsw_ef={hnsw_ef})"
        )
    
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add embeddings to the vector store.
        
        Args:
            embeddings: Array of embedding vectors (shape: [n, dim])
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique identifiers
            
        Raises:
            ValueError: If input lengths don't match
        """
        # Validate inputs
        n_embeddings = len(embeddings)
        if not (n_embeddings == len(documents) == len(metadatas) == len(ids)):
            raise ValueError(
                f"Input length mismatch: embeddings={n_embeddings}, "
                f"documents={len(documents)}, metadatas={len(metadatas)}, "
                f"ids={len(ids)}"
            )
        
        if n_embeddings == 0:
            logger.warning("No embeddings to add")
            return
        
        # Convert numpy array to list of lists for ChromaDB
        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
        
        try:
            # Add to collection
            self.collection.add(
                embeddings=embeddings_list,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {n_embeddings} embeddings to vector store")
            
            # Check memory usage
            self._check_memory_usage()
            
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter: Optional metadata filter (e.g., {"category": "hardware"})
            
        Returns:
            List of SearchResult objects, sorted by similarity (highest first)
        """
        try:
            # Convert numpy array to list for ChromaDB
            query_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_list],
                n_results=top_k,
                where=filter
            )
            
            # Format results
            search_results = []
            
            # ChromaDB returns results in this structure:
            # {'ids': [[...]], 'distances': [[...]], 'documents': [[...]], 'metadatas': [[...]]}
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result_id = results['ids'][0][i]
                    distance = results['distances'][0][i]
                    document = results['documents'][0][i] if results['documents'] else ""
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    
                    # Convert distance to similarity score
                    # For cosine distance: similarity = 1 - distance
                    # ChromaDB returns squared L2 distance for cosine space
                    # We need to convert it properly
                    similarity = 1.0 - distance
                    
                    search_results.append(SearchResult(
                        id=result_id,
                        document=document,
                        metadata=metadata,
                        distance=distance,
                        similarity=max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
                    ))
            
            logger.debug(f"Search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete_collection(self) -> None:
        """
        Delete the entire collection.
        
        Warning: This permanently removes all data in the collection.
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection '{self.collection_name}'")
            
            # Recreate the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "hnsw:construction_ef": 200,
                    "hnsw:search_ef": 100
                }
            )
            logger.info(f"Recreated collection '{self.collection_name}'")
            
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise
    
    def get_stats(self) -> VectorStoreStats:
        """
        Get statistics about the vector store.
        
        Returns:
            VectorStoreStats object with collection information
        """
        try:
            # Get collection count
            count = self.collection.count()
            
            # Estimate memory usage (rough approximation)
            # Assume 768-dim embeddings (float32) + metadata overhead
            embedding_size_bytes = 768 * 4  # 4 bytes per float32
            metadata_overhead = 1024  # Rough estimate for metadata per document
            total_bytes = count * (embedding_size_bytes + metadata_overhead)
            memory_mb = total_bytes / (1024 * 1024)
            
            return VectorStoreStats(
                collection_name=self.collection_name,
                document_count=count,
                memory_usage_mb=memory_mb
            )
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
    
    def _check_memory_usage(self) -> None:
        """
        Check memory usage and log warning if exceeding limit.
        
        Note: This is a soft limit for monitoring purposes only.
        Actual memory management is handled by ChromaDB.
        """
        try:
            stats = self.get_stats()
            
            if stats.memory_usage_mb > self.max_memory_mb:
                logger.warning(
                    f"Vector store memory usage ({stats.memory_usage_mb:.2f} MB) "
                    f"exceeds configured limit ({self.max_memory_mb} MB). "
                    f"Consider rebuilding with fewer patterns or increasing the limit."
                )
        except Exception as e:
            logger.debug(f"Could not check memory usage: {e}")
    
    def clear_cache(self) -> None:
        """
        Clear any internal caches.
        
        Note: ChromaDB manages its own caching internally.
        This method is provided for API consistency.
        """
        logger.info("Vector store cache cleared (ChromaDB manages caching internally)")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the collection.
        
        Returns:
            Dictionary with collection metadata and configuration
        """
        try:
            return {
                "name": self.collection_name,
                "count": self.collection.count(),
                "metadata": self.collection.metadata,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise
