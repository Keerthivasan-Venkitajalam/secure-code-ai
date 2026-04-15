"""
Embedding Model Manager for semantic bug detection.

This module manages the lifecycle of the embedding model used for generating
vector representations of code snippets and bug patterns.
"""

import logging
import os
from functools import lru_cache
from typing import List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Manages embedding model lifecycle and generates embeddings for text.
    
    Uses BAAI/bge-base-en-v1.5 model for generating 768-dimensional embeddings.
    Implements caching for efficient reuse of embeddings.
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        model_path: Optional[str] = None,
        device: str = "cpu",
        cache_size: int = 1000
    ):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name
            model_path: Local path to model (if already downloaded)
            device: Device to run model on ('cpu' or 'cuda')
            cache_size: Maximum number of embeddings to cache
        """
        self.model_name = model_name
        self.model_path = model_path
        self.device = device
        self.cache_size = cache_size
        self.model = None
        self._embedding_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the embedding model from local path or download from HuggingFace."""
        try:
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"Loading embedding model from local path: {self.model_path}")
                self.model = SentenceTransformer(self.model_path, device=self.device)
            else:
                logger.info(f"Downloading embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name, device=self.device)
                
                # Save to model_path if specified
                if self.model_path:
                    os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                    self.model.save(self.model_path)
                    logger.info(f"Saved embedding model to: {self.model_path}")
            
            logger.info(f"Embedding model loaded successfully on device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts
            
        Returns:
            Embedding vectors (768-dimensional)
        """
        if isinstance(texts, str):
            # Check cache for single text
            cache_key = hash(texts)
            if cache_key in self._embedding_cache:
                logger.debug(f"Cache hit for text: {texts[:50]}...")
                self._cache_hits += 1
                return self._embedding_cache[cache_key]
            
            # Generate embedding
            self._cache_misses += 1
            embedding = self.model.encode(texts, convert_to_numpy=True)
            
            # Cache the result
            self._manage_cache(cache_key, embedding)
            
            return embedding
        else:
            # For lists, encode in batch (no caching for batch operations)
            return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings in batches for efficiency.
        
        Args:
            texts: List of texts to encode
            batch_size: Number of texts to process in each batch
            
        Returns:
            Array of embedding vectors
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
    
    def get_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Ensure result is in [0, 1] range (cosine similarity is in [-1, 1])
        # For semantic similarity, we typically use (similarity + 1) / 2
        # But for embeddings from sentence transformers, they're already in [0, 1]
        return float(np.clip(similarity, 0.0, 1.0))
    
    def _manage_cache(self, cache_key: int, embedding: np.ndarray) -> None:
        """
        Manage embedding cache with LRU eviction.
        
        Args:
            cache_key: Hash key for the text
            embedding: Embedding vector to cache
        """
        if len(self._embedding_cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]
            logger.debug(f"Cache full, evicted entry: {oldest_key}")
        
        self._embedding_cache[cache_key] = embedding
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> dict:
        """
        Get statistics about the embedding cache.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self._embedding_cache),
            "max_cache_size": self.cache_size,
            "cache_utilization": len(self._embedding_cache) / self.cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate
        }
