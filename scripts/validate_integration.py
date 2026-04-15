#!/usr/bin/env python3
"""
Integration Validation Script

This script validates that all components of the Agentic Bug Hunter integration
are properly installed and configured. It performs the following checks:

1. Check all components are properly installed
2. Verify knowledge base is loaded
3. Verify vector store is accessible
4. Verify embedding model is available
5. Run smoke tests

Usage:
    python scripts/validate_integration.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.knowledge.knowledge_base import KnowledgeBase
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore
from agent.validators.hardware_validator import HardwareValidator
from agent.validators.lifecycle_validator import LifecycleValidator
from agent.validators.api_typo_detector import APITypoDetector
from loguru import logger


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str
    duration_ms: float


class IntegrationValidator:
    """Validates Agentic Bug Hunter integration."""
    
    def __init__(
        self,
        knowledge_base_path: str,
        vector_store_path: str,
        embedding_model_name: str = "BAAI/bge-base-en-v1.5",
        embedding_model_path: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        Initialize validator.
        
        Args:
            knowledge_base_path: Path to knowledge base CSV
            vector_store_path: Path to vector store directory
            embedding_model_name: Name of embedding model
            embedding_model_path: Local path to embedding model (optional)
            device: Device to use ('cpu' or 'cuda')
        """
        self.knowledge_base_path = knowledge_base_path
        self.vector_store_path = vector_store_path
        self.embedding_model_name = embedding_model_name
        self.embedding_model_path = embedding_model_path
        self.device = device
        
        self.results: List[ValidationResult] = []
    
    def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all checks pass, False otherwise
        """
        logger.info("Starting integration validation")
        
        # Run all checks
        checks = [
            ("Dependencies", self._check_dependencies),
            ("Knowledge Base", self._check_knowledge_base),
            ("Embedding Model", self._check_embedding_model),
            ("Vector Store", self._check_vector_store),
            ("Hardware Validator", self._check_hardware_validator),
            ("Lifecycle Validator", self._check_lifecycle_validator),
            ("API Typo Detector", self._check_api_typo_detector),
            ("Semantic Search", self._check_semantic_search),
        ]
        
        for name, check_func in checks:
            logger.info(f"Running check: {name}")
            start_time = time.time()
            
            try:
                passed, message = check_func()
                duration_ms = (time.time() - start_time) * 1000
                
                result = ValidationResult(
                    name=name,
                    passed=passed,
                    message=message,
                    duration_ms=duration_ms
                )
                self.results.append(result)
                
                if passed:
                    logger.success(f" {name}: {message} ({duration_ms:.2f}ms)")
                else:
                    logger.error(f" {name}: {message} ({duration_ms:.2f}ms)")
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                result = ValidationResult(
                    name=name,
                    passed=False,
                    message=f"Exception: {str(e)}",
                    duration_ms=duration_ms
                )
                self.results.append(result)
                logger.error(f" {name}: Exception: {e} ({duration_ms:.2f}ms)")
        
        # Print summary
        self._print_summary()
        
        # Return overall result
        return all(r.passed for r in self.results)
    
    def _check_dependencies(self) -> tuple[bool, str]:
        """Check that all required dependencies are installed."""
        try:
            import sentence_transformers
            import chromadb
            import rapidfuzz
            import numpy
            import pandas
            
            return True, "All dependencies installed"
        except ImportError as e:
            return False, f"Missing dependency: {e}"
    
    def _check_knowledge_base(self) -> tuple[bool, str]:
        """Check that knowledge base can be loaded."""
        try:
            # Check file exists
            if not Path(self.knowledge_base_path).exists():
                return False, f"Knowledge base file not found: {self.knowledge_base_path}"
            
            # Try to load
            kb = KnowledgeBase(self.knowledge_base_path)
            patterns = kb.load_patterns()
            
            if not patterns:
                return False, "Knowledge base is empty"
            
            # Get stats
            stats = kb.get_stats()
            
            return True, f"Loaded {stats.pattern_count} patterns from {len(stats.categories)} categories"
            
        except Exception as e:
            return False, f"Failed to load knowledge base: {e}"
    
    def _check_embedding_model(self) -> tuple[bool, str]:
        """Check that embedding model can be loaded."""
        try:
            # Try to load model
            model = EmbeddingModel(
                model_name=self.embedding_model_name,
                model_path=self.embedding_model_path,
                device=self.device
            )
            
            # Try to generate a test embedding
            test_text = "def test(): pass"
            embedding = model.encode(test_text)
            
            if embedding is None or len(embedding) == 0:
                return False, "Failed to generate test embedding"
            
            return True, f"Model loaded, embedding dimension: {len(embedding)}"
            
        except Exception as e:
            return False, f"Failed to load embedding model: {e}"
    
    def _check_vector_store(self) -> tuple[bool, str]:
        """Check that vector store is accessible."""
        try:
            # Check directory exists
            if not Path(self.vector_store_path).exists():
                return False, f"Vector store directory not found: {self.vector_store_path}"
            
            # Try to initialize
            vs = VectorStore(
                persist_directory=self.vector_store_path,
                collection_name="bug_patterns"
            )
            
            # Get stats
            stats = vs.get_stats()
            
            if stats.document_count == 0:
                return False, "Vector store is empty (run rebuild_vector_store.py)"
            
            return True, f"Vector store accessible with {stats.document_count} documents"
            
        except Exception as e:
            return False, f"Failed to access vector store: {e}"
    
    def _check_hardware_validator(self) -> tuple[bool, str]:
        """Check that hardware validator works."""
        try:
            validator = HardwareValidator()
            
            # Test with code that has a violation
            test_code = "set_voltage(35)"
            violations = validator.validate(test_code)
            
            if not violations:
                return False, "Hardware validator did not detect test violation"
            
            return True, "Hardware validator working"
            
        except Exception as e:
            return False, f"Hardware validator failed: {e}"
    
    def _check_lifecycle_validator(self) -> tuple[bool, str]:
        """Check that lifecycle validator works."""
        try:
            validator = LifecycleValidator()
            
            # Test with code that has wrong ordering
            test_code = "RDI_END();\nRDI_BEGIN();"
            violations = validator.validate(test_code)
            
            if not violations:
                return False, "Lifecycle validator did not detect test violation"
            
            return True, "Lifecycle validator working"
            
        except Exception as e:
            return False, f"Lifecycle validator failed: {e}"
    
    def _check_api_typo_detector(self) -> tuple[bool, str]:
        """Check that API typo detector works."""
        try:
            # Use a small set of known APIs for testing
            known_apis = ["set_voltage", "get_voltage", "RDI_BEGIN", "RDI_END"]
            detector = APITypoDetector(known_apis)
            
            # Test with code that has a typo
            test_code = "set_voltag(25)"  # Missing 'e'
            suggestions = detector.detect_typos(test_code)
            
            if not suggestions:
                return False, "API typo detector did not detect test typo"
            
            return True, "API typo detector working"
            
        except Exception as e:
            return False, f"API typo detector failed: {e}"
    
    def _check_semantic_search(self) -> tuple[bool, str]:
        """Check that semantic search works end-to-end."""
        try:
            # Load all components
            kb = KnowledgeBase(self.knowledge_base_path)
            patterns = kb.load_patterns()
            
            if not patterns:
                return False, "No patterns in knowledge base"
            
            model = EmbeddingModel(
                model_name=self.embedding_model_name,
                model_path=self.embedding_model_path,
                device=self.device
            )
            
            vs = VectorStore(
                persist_directory=self.vector_store_path,
                collection_name="bug_patterns"
            )
            
            # Perform a test search
            test_pattern = patterns[0]
            test_text = f"{test_pattern.explanation}\n{test_pattern.context}"
            
            # Generate embedding
            embedding = model.encode(test_text)
            
            # Search
            results = vs.search(embedding, top_k=5)
            
            if not results:
                return False, "Semantic search returned no results"
            
            # Check if we found the test pattern
            result_ids = [r.id for r in results]
            if test_pattern.id not in result_ids:
                return False, f"Test pattern {test_pattern.id} not found in search results"
            
            return True, f"Semantic search working, found {len(results)} results"
            
        except Exception as e:
            return False, f"Semantic search failed: {e}"
    
    def _print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        print(f"Passed: {passed_count}/{total_count}")
        print("-" * 80)
        
        for result in self.results:
            status = "" if result.passed else ""
            print(f"{status} {result.name}: {result.message} ({result.duration_ms:.2f}ms)")
        
        print("=" * 80)
        
        if passed_count == total_count:
            print(" All checks passed! Integration is ready.")
        else:
            print(f" {total_count - passed_count} check(s) failed. Please fix issues above.")
        
        print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Agentic Bug Hunter integration"
    )
    parser.add_argument(
        '--knowledge-base',
        default='data/knowledge_base/samples.csv',
        help='Path to knowledge base CSV file'
    )
    parser.add_argument(
        '--vector-store',
        default='data/vector_store',
        help='Path to vector store directory'
    )
    parser.add_argument(
        '--embedding-model',
        default='BAAI/bge-base-en-v1.5',
        help='Embedding model name'
    )
    parser.add_argument(
        '--embedding-model-path',
        help='Local path to embedding model (optional)'
    )
    parser.add_argument(
        '--device',
        default='cpu',
        choices=['cpu', 'cuda'],
        help='Device to use for embedding generation'
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run validation
    validator = IntegrationValidator(
        knowledge_base_path=args.knowledge_base,
        vector_store_path=args.vector_store,
        embedding_model_name=args.embedding_model,
        embedding_model_path=args.embedding_model_path,
        device=args.device
    )
    
    success = validator.validate_all()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
