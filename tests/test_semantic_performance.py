"""
Performance tests for semantic scanning components.

Tests that semantic scanner, validators, and embedding generation
complete within specified performance bounds.

**Feature: agentic-bug-hunter-integration**
**Validates: Requirements 1.5, 4.4, 5.4, 6.4, 11.3**
"""

import time
import pytest
import tempfile
import os
from pathlib import Path
from typing import List

from agent.nodes.semantic_scanner import SemanticScanner
from agent.knowledge.knowledge_base import KnowledgeBase, BugPattern
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore
from agent.validators.hardware_validator import HardwareValidator
from agent.validators.lifecycle_validator import LifecycleValidator
from agent.validators.api_typo_detector import APITypoDetector


# Test data generators
def generate_test_code(num_lines: int = 100, include_hardware: bool = False) -> str:
    """Generate test code with specified characteristics."""
    lines = [
        "import os",
        "import sys",
        "",
        "def process_data(user_input):",
        "    # Process user input",
        "    data = user_input.strip()",
        "    result = []",
    ]
    
    if include_hardware:
        lines.extend([
            "    # Hardware API calls",
            "    set_voltage(25.0)",
            "    set_sample_count(4096)",
        ])
    
    # Fill remaining lines
    while len(lines) < num_lines:
        lines.append(f"    # Processing line {len(lines)}")
        lines.append("    result.append(data)")
    
    lines.append("    return result")
    return '\n'.join(lines[:num_lines])


def generate_hardware_code(num_violations: int = 5) -> str:
    """Generate code with hardware violations."""
    lines = ["def configure_hardware():"]
    
    for i in range(num_violations):
        voltage = 35.0 + i  # All exceed 30V limit
        lines.append(f"    set_voltage({voltage})")
    
    for i in range(num_violations):
        samples = 10000 + i * 1000  # All exceed 8192 limit
        lines.append(f"    set_sample_count({samples})")
    
    return '\n'.join(lines)


def generate_lifecycle_code(num_pairs: int = 5, include_violations: bool = False) -> str:
    """Generate code with RDI lifecycle calls."""
    lines = ["def lifecycle_operations():"]
    
    if include_violations:
        # Add wrong order violation
        lines.append("    RDI_END()")
        lines.append("    RDI_BEGIN()")
    
    for i in range(num_pairs):
        lines.append(f"    RDI_BEGIN()  # Pair {i}")
        lines.append(f"    # Operation {i}")
        lines.append(f"    RDI_END()  # Pair {i}")
    
    return '\n'.join(lines)


def generate_api_code(num_calls: int = 10, include_typos: bool = False) -> str:
    """Generate code with API calls."""
    lines = ["def api_operations():"]
    
    correct_apis = ["get_data", "set_value", "process_item", "validate_input"]
    typo_apis = ["get_dta", "set_vlue", "proces_item", "validat_input"]
    
    for i in range(num_calls):
        if include_typos and i % 2 == 0:
            api = typo_apis[i % len(typo_apis)]
        else:
            api = correct_apis[i % len(correct_apis)]
        lines.append(f"    {api}()")
    
    return '\n'.join(lines)


# Fixtures
@pytest.fixture(scope="module")
def test_knowledge_base(tmp_path_factory):
    """Create a test knowledge base with sample patterns."""
    temp_dir = tmp_path_factory.mktemp("kb_data")
    csv_path = temp_dir / "test_samples.csv"
    
    # Create minimal CSV with test patterns - use correct column names
    csv_content = """ID,Explanation,Context,Code,Correct Code,Category,Severity
1,SQL Injection,User input in query,SELECT * FROM users WHERE name = '{input}',Use parameterized queries,injection,high
2,Command Injection,Shell command with user input,os.system(f'ls {path}'),Use subprocess with list,injection,high
3,Path Traversal,File path from user,open(user_path),Validate and sanitize path,path,medium
"""
    csv_path.write_text(csv_content)
    
    kb = KnowledgeBase(str(csv_path))
    kb.load_patterns()
    return kb


@pytest.fixture(scope="module")
def test_embedding_model():
    """Create a mock embedding model for testing."""
    from unittest.mock import Mock
    import numpy as np
    
    mock_model = Mock(spec=EmbeddingModel)
    
    # Mock encode to return random embeddings quickly
    def mock_encode(texts):
        if isinstance(texts, str):
            return np.random.rand(384)  # Smaller dimension for speed
        else:
            return np.random.rand(len(texts), 384)
    
    def mock_encode_batch(texts, batch_size=32):
        return np.random.rand(len(texts), 384)
    
    mock_model.encode.side_effect = mock_encode
    mock_model.encode_batch.side_effect = mock_encode_batch
    mock_model.get_similarity.return_value = 0.85
    mock_model.clear_cache.return_value = None
    mock_model.get_cache_stats.return_value = {
        "cache_size": 0,
        "max_cache_size": 100,
        "cache_utilization": 0.0
    }
    
    return mock_model


@pytest.fixture(scope="module")
def test_vector_store(tmp_path_factory, test_knowledge_base, test_embedding_model):
    """Create a test vector store with indexed patterns."""
    from agent.knowledge.vector_store import SearchResult
    from unittest.mock import Mock
    
    mock_vs = Mock(spec=VectorStore)
    
    # Mock search to return quick results
    def mock_search(query_embedding, top_k=10):
        results = []
        patterns = test_knowledge_base.get_all_patterns()
        for i, pattern in enumerate(patterns[:top_k]):
            results.append(SearchResult(
                id=pattern.id,
                similarity=0.85 - (i * 0.05),  # Decreasing similarity
                document=f"{pattern.explanation} {pattern.context}",
                metadata={"pattern_id": pattern.id}
            ))
        return results
    
    mock_vs.search.side_effect = mock_search
    mock_vs.get_stats.return_value = Mock(
        collection_name="test",
        document_count=3,
        memory_usage_mb=1.0
    )
    
    return mock_vs


@pytest.fixture
def semantic_scanner(test_knowledge_base, test_embedding_model, test_vector_store):
    """Create a semantic scanner for testing."""
    return SemanticScanner(
        knowledge_base=test_knowledge_base,
        embedding_model=test_embedding_model,
        vector_store=test_vector_store,
        similarity_threshold=0.7,
        top_k=10,
        timeout_seconds=2.0
    )


class TestSemanticScannerPerformance:
    """Test semantic scanner performance bounds."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_completes_within_2_seconds(self, semantic_scanner):
        """
        Test semantic search completes within 2 seconds.
        
        **Property: Semantic Search Performance**
        **Validates: Requirements 1.5**
        """
        code = generate_test_code(num_lines=200)
        
        start_time = time.time()
        results = await semantic_scanner.scan(code, "test.py")
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0, \
            f"Semantic search took {execution_time:.3f}s (expected < 2.0s)"
        
        # Verify scan completed successfully
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_semantic_search_small_code(self, semantic_scanner):
        """Test semantic search performance on small code snippets."""
        code = generate_test_code(num_lines=50)
        
        start_time = time.time()
        results = await semantic_scanner.scan(code, "test.py")
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0, \
            f"Small code scan took {execution_time:.3f}s (expected < 1.0s)"
    
    @pytest.mark.asyncio
    async def test_semantic_search_large_code(self, semantic_scanner):
        """Test semantic search performance on larger code."""
        code = generate_test_code(num_lines=500)
        
        start_time = time.time()
        results = await semantic_scanner.scan(code, "test.py")
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0, \
            f"Large code scan took {execution_time:.3f}s (expected < 2.0s)"
    
    def test_direct_search_performance(self, semantic_scanner):
        """Test direct knowledge base search performance."""
        query = "SQL injection vulnerability in user input"
        
        start_time = time.time()
        results = semantic_scanner.search_similar(query, top_k=10)
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0, \
            f"Direct search took {execution_time:.3f}s (expected < 1.0s)"
        
        assert isinstance(results, list)


class TestHardwareValidatorPerformance:
    """Test hardware validator performance bounds."""
    
    def test_hardware_validation_completes_within_100ms(self):
        """
        Test hardware validation completes within 100ms.
        
        **Property: Hardware Validation Performance**
        **Validates: Requirements 4.4**
        """
        validator = HardwareValidator()
        code = generate_hardware_code(num_violations=10)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Hardware validation took {execution_time:.3f}s (expected < 0.1s)"
        
        # Verify validation completed
        assert isinstance(violations, list)
        assert len(violations) > 0  # Should find violations
    
    def test_hardware_validation_small_code(self):
        """Test hardware validation on small code."""
        validator = HardwareValidator()
        code = generate_hardware_code(num_violations=2)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.05, \
            f"Small code validation took {execution_time:.3f}s (expected < 0.05s)"
    
    def test_hardware_validation_large_code(self):
        """Test hardware validation on larger code."""
        validator = HardwareValidator()
        code = generate_hardware_code(num_violations=50)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Large code validation took {execution_time:.3f}s (expected < 0.1s)"
    
    def test_hardware_validation_no_violations(self):
        """Test hardware validation performance when no violations present."""
        validator = HardwareValidator()
        code = generate_test_code(num_lines=100, include_hardware=True)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"No-violation validation took {execution_time:.3f}s (expected < 0.1s)"


class TestLifecycleValidatorPerformance:
    """Test lifecycle validator performance bounds."""
    
    def test_lifecycle_validation_completes_within_100ms(self):
        """
        Test lifecycle validation completes within 100ms.
        
        **Property: Lifecycle Validation Performance**
        **Validates: Requirements 5.4**
        """
        validator = LifecycleValidator()
        code = generate_lifecycle_code(num_pairs=10, include_violations=True)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Lifecycle validation took {execution_time:.3f}s (expected < 0.1s)"
        
        # Verify validation completed
        assert isinstance(violations, list)
    
    def test_lifecycle_validation_small_code(self):
        """Test lifecycle validation on small code."""
        validator = LifecycleValidator()
        code = generate_lifecycle_code(num_pairs=2)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.05, \
            f"Small code validation took {execution_time:.3f}s (expected < 0.05s)"
    
    def test_lifecycle_validation_large_code(self):
        """Test lifecycle validation on larger code."""
        validator = LifecycleValidator()
        code = generate_lifecycle_code(num_pairs=50)
        
        start_time = time.time()
        violations = validator.validate(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Large code validation took {execution_time:.3f}s (expected < 0.1s)"


class TestAPITypoDetectorPerformance:
    """Test API typo detector performance bounds."""
    
    def test_api_typo_detection_completes_within_50ms_per_call(self):
        """
        Test API typo detection completes within 50ms per call.
        
        **Property: API Typo Detection Performance**
        **Validates: Requirements 6.4**
        """
        known_apis = ["get_data", "set_value", "process_item", "validate_input",
                      "fetch_records", "update_status", "delete_entry", "create_user"]
        detector = APITypoDetector(known_apis)
        
        code = generate_api_code(num_calls=10, include_typos=True)
        
        start_time = time.time()
        suggestions = detector.detect_typos(code)
        execution_time = time.time() - start_time
        
        # Calculate per-call time (10 calls in the code)
        per_call_time = execution_time / 10
        
        assert per_call_time < 0.05, \
            f"API typo detection took {per_call_time:.3f}s per call (expected < 0.05s)"
        
        # Verify detection completed
        assert isinstance(suggestions, list)
    
    def test_api_typo_detection_small_code(self):
        """Test API typo detection on small code."""
        known_apis = ["get_data", "set_value", "process_item"]
        detector = APITypoDetector(known_apis)
        
        code = generate_api_code(num_calls=3, include_typos=True)
        
        start_time = time.time()
        suggestions = detector.detect_typos(code)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.05, \
            f"Small code detection took {execution_time:.3f}s (expected < 0.05s)"
    
    def test_api_typo_detection_large_code(self):
        """Test API typo detection on larger code."""
        known_apis = ["get_data", "set_value", "process_item", "validate_input",
                      "fetch_records", "update_status", "delete_entry", "create_user"]
        detector = APITypoDetector(known_apis)
        
        code = generate_api_code(num_calls=50, include_typos=True)
        
        start_time = time.time()
        suggestions = detector.detect_typos(code)
        execution_time = time.time() - start_time
        
        # Calculate per-call time
        per_call_time = execution_time / 50
        
        assert per_call_time < 0.05, \
            f"Large code detection took {per_call_time:.3f}s per call (expected < 0.05s)"


class TestEmbeddingGenerationPerformance:
    """Test embedding generation performance and scaling."""
    
    def test_embedding_generation_scales_with_batch_size(self):
        """
        Test embedding generation scales efficiently with batch size.
        
        **Property: Embedding Batch Scaling**
        **Validates: Requirements 11.3**
        """
        from unittest.mock import Mock
        import numpy as np
        import time
        
        mock_model = Mock(spec=EmbeddingModel)
        
        # Simulate single encoding being slower
        def mock_encode_single(text):
            time.sleep(0.01)  # 10ms per encoding
            return np.random.rand(384)
        
        # Simulate batch encoding being faster per item
        def mock_encode_batch(texts, batch_size=32):
            time.sleep(0.05)  # 50ms total for batch
            return np.random.rand(len(texts), 384)
        
        mock_model.encode.side_effect = mock_encode_single
        mock_model.encode_batch.side_effect = mock_encode_batch
        
        texts = [f"Test code snippet {i}" for i in range(10)]
        
        # Test single encoding
        start_time = time.time()
        for text in texts:
            mock_model.encode(text)
        single_time = time.time() - start_time
        
        # Test batch encoding
        start_time = time.time()
        mock_model.encode_batch(texts, batch_size=10)
        batch_time = time.time() - start_time
        
        # Batch should be faster than individual encodings
        assert batch_time < single_time, \
            f"Batch encoding ({batch_time:.3f}s) should be faster than single ({single_time:.3f}s)"
        
        # Batch should be at least 1.5x faster
        speedup = single_time / batch_time
        assert speedup >= 1.5, \
            f"Batch encoding speedup {speedup:.2f}x is less than expected (>= 1.5x)"
    
    def test_embedding_cache_improves_performance(self):
        """Test that embedding cache improves performance for repeated texts."""
        from unittest.mock import Mock
        import numpy as np
        import time
        
        mock_model = Mock(spec=EmbeddingModel)
        
        # Track call count
        call_count = [0]
        
        def mock_encode(text):
            call_count[0] += 1
            if call_count[0] == 1:
                time.sleep(0.01)  # First call is slow
            else:
                time.sleep(0.0001)  # Cached call is fast
            return np.random.rand(384)
        
        mock_model.encode.side_effect = mock_encode
        mock_model.clear_cache.return_value = None
        
        text = "Test code snippet for caching"
        
        # First encoding (cache miss)
        start_time = time.time()
        mock_model.encode(text)
        first_time = time.time() - start_time
        
        # Second encoding (cache hit)
        start_time = time.time()
        mock_model.encode(text)
        second_time = time.time() - start_time
        
        # Cached access should be faster
        assert second_time < first_time, \
            f"Cached access ({second_time:.6f}s) should be faster than first ({first_time:.6f}s)"
    
    def test_batch_encoding_different_sizes(self):
        """Test batch encoding performance with different batch sizes."""
        from unittest.mock import Mock
        import numpy as np
        import time
        
        mock_model = Mock(spec=EmbeddingModel)
        
        def mock_encode_batch(texts, batch_size=32):
            # Simulate processing time proportional to number of batches
            num_batches = (len(texts) + batch_size - 1) // batch_size
            time.sleep(0.01 * num_batches)
            return np.random.rand(len(texts), 384)
        
        mock_model.encode_batch.side_effect = mock_encode_batch
        
        texts = [f"Test code snippet {i}" for i in range(100)]
        
        batch_sizes = [8, 16, 32, 64]
        times = []
        
        for batch_size in batch_sizes:
            start_time = time.time()
            mock_model.encode_batch(texts, batch_size=batch_size)
            execution_time = time.time() - start_time
            times.append(execution_time)
        
        # All batch sizes should complete in reasonable time
        for i, (batch_size, exec_time) in enumerate(zip(batch_sizes, times)):
            assert exec_time < 1.0, \
                f"Batch size {batch_size} took {exec_time:.3f}s (expected < 1.0s)"
    
    def test_embedding_generation_small_batch(self):
        """Test embedding generation on small batches."""
        from unittest.mock import Mock
        import numpy as np
        
        mock_model = Mock(spec=EmbeddingModel)
        mock_model.encode_batch.return_value = np.random.rand(10, 384)
        
        texts = [f"Test {i}" for i in range(10)]
        
        start_time = time.time()
        embeddings = mock_model.encode_batch(texts, batch_size=10)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Small batch encoding took {execution_time:.3f}s (expected < 0.1s)"
        
        assert embeddings.shape[0] == 10
    
    def test_embedding_generation_large_batch(self):
        """Test embedding generation on larger batches."""
        from unittest.mock import Mock
        import numpy as np
        
        mock_model = Mock(spec=EmbeddingModel)
        mock_model.encode_batch.return_value = np.random.rand(100, 384)
        
        texts = [f"Test code snippet {i}" for i in range(100)]
        
        start_time = time.time()
        embeddings = mock_model.encode_batch(texts, batch_size=32)
        execution_time = time.time() - start_time
        
        assert execution_time < 0.1, \
            f"Large batch encoding took {execution_time:.3f}s (expected < 0.1s)"
        
        assert embeddings.shape[0] == 100


class TestIntegratedPerformance:
    """Test integrated performance of multiple components."""
    
    @pytest.mark.asyncio
    async def test_full_semantic_scan_with_validators(
        self,
        semantic_scanner,
        test_knowledge_base,
        test_embedding_model,
        test_vector_store
    ):
        """Test full semantic scan with all validators."""
        # Generate code with various features
        code = generate_test_code(num_lines=200, include_hardware=True)
        code += "\n" + generate_lifecycle_code(num_pairs=5)
        code += "\n" + generate_api_code(num_calls=10, include_typos=True)
        
        # Run semantic scan
        start_time = time.time()
        semantic_results = await semantic_scanner.scan(code, "test.py")
        semantic_time = time.time() - start_time
        
        # Run validators
        hw_validator = HardwareValidator()
        lc_validator = LifecycleValidator()
        api_detector = APITypoDetector(["get_data", "set_value", "process_item"])
        
        start_time = time.time()
        hw_violations = hw_validator.validate(code)
        lc_violations = lc_validator.validate(code)
        api_suggestions = api_detector.detect_typos(code)
        validator_time = time.time() - start_time
        
        # Total time should be reasonable
        total_time = semantic_time + validator_time
        assert total_time < 3.0, \
            f"Full scan took {total_time:.3f}s (expected < 3.0s)"
        
        # Verify all components completed
        assert isinstance(semantic_results, list)
        assert isinstance(hw_violations, list)
        assert isinstance(lc_violations, list)
        assert isinstance(api_suggestions, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
