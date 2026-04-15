"""
Semantic Scanner Agent for RAG-based bug detection.

This module implements semantic bug detection using knowledge base search,
embedding models, and vector similarity matching to identify potential
vulnerabilities based on learned patterns.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import numpy as np

from ..knowledge.knowledge_base import KnowledgeBase, BugPattern
from ..knowledge.embedding_model import EmbeddingModel
from ..knowledge.vector_store import VectorStore, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class SemanticVulnerability:
    """
    Represents a vulnerability detected through semantic analysis.
    
    Attributes:
        location: Line number or range where vulnerability was found
        vuln_type: Type of vulnerability detected
        description: Human-readable description of the vulnerability
        similar_pattern_id: ID of the matching pattern from knowledge base
        similarity_score: Similarity score (0-1) to the matched pattern
        suggested_fix: Suggested fix from the matched pattern
        severity: Severity level (high, medium, low)
        confidence: Confidence score (0-1) in the detection
        source: Source of detection (always "semantic_scanner")
    """
    location: str
    vuln_type: str
    description: str
    similar_pattern_id: str
    similarity_score: float
    suggested_fix: str
    severity: str
    confidence: float
    source: str = "semantic_scanner"
    
    def __post_init__(self):
        """Validate field values after initialization."""
        # Ensure similarity_score is in valid range
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"similarity_score must be in [0, 1], got {self.similarity_score}")
        
        # Ensure confidence is in valid range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        
        # Validate severity
        valid_severities = {"high", "medium", "low"}
        if self.severity.lower() not in valid_severities:
            raise ValueError(f"severity must be one of {valid_severities}, got {self.severity}")


@dataclass
class SimilarPattern:
    """
    Represents a similar bug pattern from the knowledge base.
    
    Attributes:
        pattern_id: Unique identifier of the pattern
        explanation: Description of what the bug is
        context: Additional context about when this bug occurs
        buggy_code: Example of code with the bug
        correct_code: Example of corrected code
        similarity_score: Similarity score (0-1) to the query
        category: Category of the bug
    """
    pattern_id: str
    explanation: str
    context: str
    buggy_code: str
    correct_code: str
    similarity_score: float
    category: str
    
    def __post_init__(self):
        """Validate field values after initialization."""
        # Ensure similarity_score is in valid range
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"similarity_score must be in [0, 1], got {self.similarity_score}")



class SemanticScanner:
    """
    Semantic bug detection using RAG-based knowledge search.
    
    Scans code for potential vulnerabilities by comparing against a knowledge
    base of known bug patterns using semantic similarity matching.
    """
    
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        similarity_threshold: float = 0.7,
        top_k: int = 10,
        timeout_seconds: float = 2.0
    ):
        """
        Initialize semantic scanner.
        
        Args:
            knowledge_base: Knowledge base of bug patterns
            embedding_model: Model for generating embeddings
            vector_store: Vector store for similarity search
            similarity_threshold: Minimum similarity score for matches (default: 0.7)
            top_k: Maximum number of results to return (default: 10)
            timeout_seconds: Timeout for scan operations (default: 2.0)
        """
        self.knowledge_base = knowledge_base
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.timeout_seconds = timeout_seconds
        
        # Ensure knowledge base is loaded
        if not self.knowledge_base._loaded:
            self.knowledge_base.load_patterns()
        
        logger.info(
            f"Initialized SemanticScanner with threshold={similarity_threshold}, "
            f"top_k={top_k}, timeout={timeout_seconds}s"
        )
    
    async def scan(
        self,
        code: str,
        file_path: str,
        timeout_override: Optional[float] = None
    ) -> List[SemanticVulnerability]:
        """
        Scan code for bugs using semantic similarity.
        
        Args:
            code: Source code to analyze
            file_path: Path to file for context
            timeout_override: Optional timeout override for this scan
            
        Returns:
            List of vulnerabilities found via semantic matching
            
        Raises:
            asyncio.TimeoutError: If scan exceeds timeout
        """
        timeout = timeout_override if timeout_override is not None else self.timeout_seconds
        
        try:
            # Run scan with timeout
            return await asyncio.wait_for(
                self._perform_scan(code, file_path),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Semantic scan timed out after {timeout}s for {file_path}"
            )
            # Return empty results on timeout (graceful degradation)
            return []
        except Exception as e:
            logger.error(f"Semantic scan failed for {file_path}: {e}", exc_info=True)
            # Return empty results on error (graceful degradation)
            return []
    
    async def _perform_scan(
        self,
        code: str,
        file_path: str
    ) -> List[SemanticVulnerability]:
        """
        Internal method to perform the actual semantic scan.
        
        Args:
            code: Source code to analyze
            file_path: Path to file for context
            
        Returns:
            List of vulnerabilities found
        """
        # Handle empty code
        if not code or not code.strip():
            logger.debug(f"Empty code provided for {file_path}, skipping scan")
            return []
        
        try:
            # Generate embedding for the code
            logger.debug(f"Generating embedding for {file_path}")
            code_embedding = self.embedding_model.encode(code)
            
            # Search vector store for similar patterns
            logger.debug(f"Searching vector store for similar patterns")
            search_results = self.vector_store.search(
                query_embedding=code_embedding,
                top_k=self.top_k
            )
            
            # Filter by similarity threshold and convert to vulnerabilities
            vulnerabilities = []
            for result in search_results:
                if result.similarity >= self.similarity_threshold:
                    # Get the full pattern from knowledge base
                    pattern = self.knowledge_base.get_pattern(result.id)
                    
                    if pattern:
                        vulnerability = self._create_vulnerability(
                            pattern=pattern,
                            similarity_score=result.similarity,
                            file_path=file_path
                        )
                        vulnerabilities.append(vulnerability)
            
            logger.info(
                f"Found {len(vulnerabilities)} semantic vulnerabilities in {file_path} "
                f"(from {len(search_results)} candidates)"
            )
            
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error during semantic scan: {e}", exc_info=True)
            raise
    
    def search_similar(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[SimilarPattern]:
        """
        Search knowledge base for similar patterns.
        
        This is a direct query interface for searching the knowledge base
        without performing a full vulnerability scan.
        
        Args:
            query: Search query (code snippet or description)
            top_k: Number of results to return (uses instance default if None)
            
        Returns:
            List of similar patterns with scores
        """
        if top_k is None:
            top_k = self.top_k
        
        try:
            # Handle empty query
            if not query or not query.strip():
                logger.debug("Empty query provided, returning empty results")
                return []
            
            # Generate embedding for the query
            logger.debug(f"Generating embedding for query: {query[:50]}...")
            query_embedding = self.embedding_model.encode(query)
            
            # Search vector store
            logger.debug(f"Searching for top {top_k} similar patterns")
            search_results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            # Convert to SimilarPattern objects
            similar_patterns = []
            for result in search_results:
                # Get the full pattern from knowledge base
                pattern = self.knowledge_base.get_pattern(result.id)
                
                if pattern:
                    similar_pattern = SimilarPattern(
                        pattern_id=pattern.id,
                        explanation=pattern.explanation,
                        context=pattern.context,
                        buggy_code=pattern.buggy_code,
                        correct_code=pattern.correct_code,
                        similarity_score=result.similarity,
                        category=pattern.category
                    )
                    similar_patterns.append(similar_pattern)
            
            logger.info(f"Found {len(similar_patterns)} similar patterns for query")
            return similar_patterns
            
        except Exception as e:
            logger.error(f"Error searching similar patterns: {e}", exc_info=True)
            # Return empty results on error
            return []
    
    def _create_vulnerability(
        self,
        pattern: BugPattern,
        similarity_score: float,
        file_path: str
    ) -> SemanticVulnerability:
        """
        Create a SemanticVulnerability from a matched pattern.
        
        Args:
            pattern: The matched bug pattern
            similarity_score: Similarity score to the pattern
            file_path: Path to the file being scanned
            
        Returns:
            SemanticVulnerability object
        """
        # Determine confidence based on similarity score
        # Higher similarity = higher confidence
        confidence = similarity_score
        
        # Create vulnerability
        return SemanticVulnerability(
            location=file_path,  # Could be enhanced to include line numbers
            vuln_type=pattern.category,
            description=pattern.explanation,
            similar_pattern_id=pattern.id,
            similarity_score=similarity_score,
            suggested_fix=pattern.correct_code,
            severity=pattern.severity,
            confidence=confidence,
            source="semantic_scanner"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the semantic scanner.
        
        Returns:
            Dictionary with scanner statistics
        """
        kb_stats = self.knowledge_base.get_stats()
        vs_stats = self.vector_store.get_stats()
        em_stats = self.embedding_model.get_cache_stats()
        
        return {
            "knowledge_base": {
                "pattern_count": kb_stats.pattern_count,
                "categories": kb_stats.categories,
                "last_updated": kb_stats.last_updated
            },
            "vector_store": {
                "collection_name": vs_stats.collection_name,
                "document_count": vs_stats.document_count,
                "memory_usage_mb": vs_stats.memory_usage_mb
            },
            "embedding_model": em_stats,
            "configuration": {
                "similarity_threshold": self.similarity_threshold,
                "top_k": self.top_k,
                "timeout_seconds": self.timeout_seconds
            }
        }
