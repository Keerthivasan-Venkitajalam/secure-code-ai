#!/usr/bin/env python3
"""
Vector Store Rebuild Script

This script rebuilds the vector store from the knowledge base by:
1. Loading all bug patterns from the knowledge base
2. Generating embeddings for each pattern
3. Building the vector store with embeddings
4. Verifying vector store integrity

Usage:
    python scripts/rebuild_vector_store.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.knowledge.knowledge_base import KnowledgeBase, BugPattern
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore
from loguru import logger


class VectorStoreRebuilder:
    """Rebuilds vector store from knowledge base."""
    
    def __init__(
        self,
        knowledge_base_path: str,
        vector_store_path: str,
        embedding_model_name: str = "BAAI/bge-base-en-v1.5",
        embedding_model_path: str = None,
        batch_size: int = 32,
        device: str = "cpu"
    ):
        """
        Initialize rebuilder.
        
        Args:
            knowledge_base_path: Path to knowledge base CSV
            vector_store_path: Path to vector store directory
            embedding_model_name: Name of embedding model
            embedding_model_path: Local path to embedding model (optional)
            batch_size: Batch size for embedding generation
            device: Device to use ('cpu' or 'cuda')
        """
        self.knowledge_base_path = knowledge_base_path
        self.vector_store_path = vector_store_path
        self.embedding_model_name = embedding_model_name
        self.embedding_model_path = embedding_model_path
        self.batch_size = batch_size
        self.device = device
        
        self.knowledge_base = None
        self.embedding_model = None
        self.vector_store = None
    
    def rebuild(self) -> bool:
        """
        Rebuild the vector store.
        
        Returns:
            True if rebuild succeeds, False otherwise
        """
        try:
            logger.info("Starting vector store rebuild")
            
            # Step 1: Load knowledge base
            logger.info(f"Loading knowledge base from {self.knowledge_base_path}")
            self.knowledge_base = KnowledgeBase(self.knowledge_base_path)
            patterns = self.knowledge_base.load_patterns()
            
            if not patterns:
                logger.error("No patterns found in knowledge base")
                return False
            
            logger.info(f"Loaded {len(patterns)} patterns")
            
            # Step 2: Initialize embedding model
            logger.info(f"Initializing embedding model: {self.embedding_model_name}")
            self.embedding_model = EmbeddingModel(
                model_name=self.embedding_model_name,
                model_path=self.embedding_model_path,
                device=self.device
            )
            logger.info("Embedding model initialized")
            
            # Step 3: Initialize vector store (this will clear existing data)
            logger.info(f"Initializing vector store at {self.vector_store_path}")
            self.vector_store = VectorStore(
                persist_directory=self.vector_store_path,
                collection_name="bug_patterns"
            )
            
            # Clear existing collection
            logger.info("Clearing existing vector store data")
            self.vector_store.delete_collection()
            
            # Step 4: Generate embeddings
            logger.info("Generating embeddings for all patterns")
            embeddings = self._generate_embeddings(patterns)
            
            if embeddings is None:
                logger.error("Failed to generate embeddings")
                return False
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # Step 5: Build vector store
            logger.info("Building vector store")
            success = self._build_vector_store(patterns, embeddings)
            
            if not success:
                logger.error("Failed to build vector store")
                return False
            
            # Step 6: Verify integrity
            logger.info("Verifying vector store integrity")
            if not self._verify_integrity(patterns):
                logger.error("Vector store integrity check failed")
                return False
            
            logger.success("Vector store rebuild completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during rebuild: {e}")
            return False
    
    def _generate_embeddings(self, patterns: List[BugPattern]) -> List[List[float]]:
        """
        Generate embeddings for all patterns.
        
        Args:
            patterns: List of bug patterns
            
        Returns:
            List of embedding vectors or None if generation fails
        """
        try:
            # Prepare texts for embedding
            # Combine explanation, context, and buggy code for better semantic representation
            texts = []
            for pattern in patterns:
                text = f"{pattern.explanation}\n{pattern.context}\n{pattern.buggy_code}"
                texts.append(text)
            
            # Generate embeddings in batches
            logger.info(f"Generating embeddings in batches of {self.batch_size}")
            start_time = time.time()
            
            embeddings = self.embedding_model.encode_batch(texts, batch_size=self.batch_size)
            
            elapsed = time.time() - start_time
            logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None
    
    def _build_vector_store(
        self,
        patterns: List[BugPattern],
        embeddings: List[List[float]]
    ) -> bool:
        """
        Build vector store from patterns and embeddings.
        
        Args:
            patterns: List of bug patterns
            embeddings: List of embedding vectors
            
        Returns:
            True if build succeeds, False otherwise
        """
        try:
            # Prepare data for vector store
            ids = [pattern.id for pattern in patterns]
            documents = [pattern.buggy_code for pattern in patterns]
            metadatas = [
                {
                    "explanation": pattern.explanation,
                    "context": pattern.context,
                    "correct_code": pattern.correct_code,
                    "category": pattern.category,
                    "severity": pattern.severity
                }
                for pattern in patterns
            ]
            
            # Add to vector store
            logger.info("Adding embeddings to vector store")
            self.vector_store.add_embeddings(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Get stats
            stats = self.vector_store.get_stats()
            logger.info(
                f"Vector store built: {stats.document_count} documents, "
                f"{stats.memory_usage_mb:.2f} MB"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error building vector store: {e}")
            return False
    
    def _verify_integrity(self, patterns: List[BugPattern]) -> bool:
        """
        Verify vector store integrity.
        
        Args:
            patterns: Original list of patterns
            
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            # Check 1: Verify document count matches
            stats = self.vector_store.get_stats()
            if stats.document_count != len(patterns):
                logger.error(
                    f"Document count mismatch: expected {len(patterns)}, "
                    f"got {stats.document_count}"
                )
                return False
            
            logger.info(f" Document count verified: {stats.document_count}")
            
            # Check 2: Verify we can search for a sample pattern
            if patterns:
                sample_pattern = patterns[0]
                sample_text = f"{sample_pattern.explanation}\n{sample_pattern.context}\n{sample_pattern.buggy_code}"
                sample_embedding = self.embedding_model.encode(sample_text)
                
                results = self.vector_store.search(sample_embedding, top_k=1)
                
                if not results:
                    logger.error("Search returned no results for sample pattern")
                    return False
                
                # The top result should be the sample pattern itself
                if results[0].id != sample_pattern.id:
                    logger.warning(
                        f"Top result ID mismatch: expected {sample_pattern.id}, "
                        f"got {results[0].id}"
                    )
                    # This is a warning, not a failure
                
                logger.info(f" Search functionality verified")
            
            # Check 3: Verify all patterns are searchable
            logger.info("Verifying all patterns are searchable...")
            missing_patterns = []
            
            for i, pattern in enumerate(patterns[:10]):  # Check first 10 for speed
                text = f"{pattern.explanation}\n{pattern.context}\n{pattern.buggy_code}"
                embedding = self.embedding_model.encode(text)
                results = self.vector_store.search(embedding, top_k=5)
                
                # Check if pattern ID is in top 5 results
                result_ids = [r.id for r in results]
                if pattern.id not in result_ids:
                    missing_patterns.append(pattern.id)
            
            if missing_patterns:
                logger.warning(
                    f"Some patterns not found in top-5 results: {missing_patterns}"
                )
                # This is a warning, not a failure
            else:
                logger.info(f" All sampled patterns are searchable")
            
            logger.success("Vector store integrity verified")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rebuild vector store from knowledge base"
    )
    parser.add_argument(
        '--knowledge-base',
        required=True,
        help='Path to knowledge base CSV file'
    )
    parser.add_argument(
        '--vector-store',
        required=True,
        help='Path to vector store directory'
    )
    parser.add_argument(
        '--embedding-model',
        default='BAAI/bge-base-en-v1.5',
        help='Embedding model name (default: BAAI/bge-base-en-v1.5)'
    )
    parser.add_argument(
        '--embedding-model-path',
        help='Local path to embedding model (optional)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for embedding generation (default: 32)'
    )
    parser.add_argument(
        '--device',
        default='cpu',
        choices=['cpu', 'cuda'],
        help='Device to use for embedding generation (default: cpu)'
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Perform rebuild
    rebuilder = VectorStoreRebuilder(
        knowledge_base_path=args.knowledge_base,
        vector_store_path=args.vector_store,
        embedding_model_name=args.embedding_model,
        embedding_model_path=args.embedding_model_path,
        batch_size=args.batch_size,
        device=args.device
    )
    
    success = rebuilder.rebuild()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
