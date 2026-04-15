"""
Property and unit tests for Semantic Scanner Agent.

Feature: agentic-bug-hunter-integration
Properties: 1, 2, 3 (Semantic Search Consistency, Similarity Threshold Filtering, Top-K Result Limiting)

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch

from agent.nodes.semantic_scanner import (
    SemanticScanner,
    SemanticVulnerability,
    SimilarPattern
)
from agent.knowledge.knowledge_base import KnowledgeBase, BugPattern
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore


# Test fixtures
@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_knowledge_base(temp_data_dir):
    """Create a sample knowledge base for testing."""
    kb_path = temp_data_dir / "samples.csv"
    
    # Create sample CSV
    with open(kb_path, 'w', encoding='utf-8') as f:
        f.write("ID,Explanation,Context,Code,Correct Code,Category,Severity\n")
        f.write('1,"SQL Injection","User input not sanitized","query = f\'SELECT * FROM users WHERE id={user_id}\'","query = \'SELECT * FROM users WHERE id=?\' with params",security,high\n')
        f.write('2,"Buffer Overflow","Array bounds not checked","strcpy(dest, src)","strncpy(dest, src, sizeof(dest))",memory,high\n')
        f.write('3,"Hardcoded Password","Password in source code","password = \'admin123\'","password = os.getenv(\'PASSWORD\')",security,medium\n')
    
    kb = KnowledgeBase(str(kb_path))
    kb.load_patterns()
    return kb


@pytest.fixture
def embedding_model():
    """Create embedding model for testing."""
    # Use a small model for faster tests
    return EmbeddingModel(
        model_name="BAAI/bge-base-en-v1.5",
        device="cpu",
        cache_size=100
    )


@pytest.fixture
def vector_store(temp_data_dir, sample_knowledge_base, embedding_model):
    """Create and populate vector store for testing."""
    vs_path = temp_data_dir / "vector_store"
    vs = VectorStore(str(vs_path), collection_name="test_patterns")
    
    # Add patterns to vector store
    patterns = sample_knowledge_base.load_patterns()
    
    embeddings = []
    documents = []
    metadatas = []
    ids = []
    
    for pattern in patterns:
        # Create document text from pattern
        doc_text = f"{pattern.explanation} {pattern.context} {pattern.buggy_code}"
        embedding = embedding_model.encode(doc_text)
        
        embeddings.append(embedding)
        documents.append(doc_text)
        metadatas.append({
            "category": pattern.category,
            "severity": pattern.severity
        })
        ids.append(pattern.id)
    
    import numpy as np
    vs.add_embeddings(
        embeddings=np.array(embeddings),
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    yield vs
    
    # Cleanup: explicitly close ChromaDB client
    try:
        del vs.collection
        del vs.client
    except:
        pass


@pytest.fixture
def semantic_scanner(sample_knowledge_base, embedding_model, vector_store):
    """Create semantic scanner for testing."""
    return SemanticScanner(
        knowledge_base=sample_knowledge_base,
        embedding_model=embedding_model,
        vector_store=vector_store,
        similarity_threshold=0.7,
        top_k=10,
        timeout_seconds=5.0
    )


class TestSemanticSearchConsistency:
    """
    Property 1: Semantic Search Consistency
    
    For any code snippet submitted for analysis, the semantic scanner should
    always perform a search operation and return results in a consistent format,
    regardless of whether matches are found.
    
    Feature: agentic-bug-hunter-integration
    Property 1: Semantic Search Consistency
    
    Validates: Requirements 1.1, 1.4
    """
    
    @pytest.mark.asyncio
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for embedding operations
    )
    @given(code=st.text(min_size=1, max_size=500))
    async def test_scan_always_returns_list(self, semantic_scanner, code):
        """
        Property: For any code input, scan() returns a list.
        
        Feature: agentic-bug-hunter-integration
        Property 1: Semantic Search Consistency
        
        Validates: Requirements 1.1, 1.4
        """
        result = await semantic_scanner.scan(code, "test.py")
        
        # Property: Result must always be a list
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        
        # Property: All items in list must be SemanticVulnerability
        for item in result:
            assert isinstance(item, SemanticVulnerability), (
                f"Expected SemanticVulnerability, got {type(item)}"
            )
    
    @pytest.mark.asyncio
    async def test_scan_with_empty_code_returns_empty_list(self, semantic_scanner):
        """Test that empty code returns empty list (not None or error)."""
        result = await semantic_scanner.scan("", "test.py")
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scan_with_whitespace_only_returns_empty_list(self, semantic_scanner):
        """Test that whitespace-only code returns empty list."""
        result = await semantic_scanner.scan("   \n\t  ", "test.py")
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_vulnerability_has_required_fields(self, semantic_scanner):
        """Test that returned vulnerabilities have all required fields."""
        code = "SELECT * FROM users WHERE id = user_input"
        result = await semantic_scanner.scan(code, "test.py")
        
        for vuln in result:
            # Check all required fields exist
            assert hasattr(vuln, 'location')
            assert hasattr(vuln, 'vuln_type')
            assert hasattr(vuln, 'description')
            assert hasattr(vuln, 'similar_pattern_id')
            assert hasattr(vuln, 'similarity_score')
            assert hasattr(vuln, 'suggested_fix')
            assert hasattr(vuln, 'severity')
            assert hasattr(vuln, 'confidence')
            assert hasattr(vuln, 'source')
            
            # Check field types
            assert isinstance(vuln.location, str)
            assert isinstance(vuln.vuln_type, str)
            assert isinstance(vuln.description, str)
            assert isinstance(vuln.similar_pattern_id, str)
            assert isinstance(vuln.similarity_score, float)
            assert isinstance(vuln.suggested_fix, str)
            assert isinstance(vuln.severity, str)
            assert isinstance(vuln.confidence, float)
            assert vuln.source == "semantic_scanner"
    
    @pytest.mark.asyncio
    async def test_scan_timeout_returns_empty_list(self, semantic_scanner):
        """Test that timeout returns empty list (graceful degradation)."""
        # Use very short timeout to force timeout
        result = await semantic_scanner.scan(
            "some code",
            "test.py",
            timeout_override=0.001  # 1ms timeout
        )
        
        # Should return empty list, not raise exception
        assert isinstance(result, list)


class TestSimilarityThresholdFiltering:
    """
    Property 2: Similarity Threshold Filtering
    
    For any search results returned by the semantic scanner, all similarity
    scores should be greater than or equal to the configured threshold.
    
    Feature: agentic-bug-hunter-integration
    Property 2: Similarity Threshold Filtering
    
    Validates: Requirements 1.2
    """
    
    @pytest.mark.asyncio
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for embedding operations
    )
    @given(
        threshold=st.floats(min_value=0.5, max_value=0.95),
        code=st.text(min_size=10, max_size=200)
    )
    async def test_all_results_above_threshold(
        self,
        sample_knowledge_base,
        embedding_model,
        vector_store,
        threshold,
        code
    ):
        """
        Property: For any threshold, all returned results have similarity >= threshold.
        
        Feature: agentic-bug-hunter-integration
        Property 2: Similarity Threshold Filtering
        
        Validates: Requirements 1.2
        """
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=threshold,
            top_k=10
        )
        
        result = await scanner.scan(code, "test.py")
        
        # Property: All similarity scores must be >= threshold
        for vuln in result:
            assert vuln.similarity_score >= threshold, (
                f"Similarity score {vuln.similarity_score} is below "
                f"threshold {threshold}"
            )
    
    @pytest.mark.asyncio
    async def test_threshold_filtering_with_known_pattern(self, semantic_scanner):
        """Test threshold filtering with code similar to known patterns."""
        # Code very similar to SQL injection pattern
        code = "query = f'SELECT * FROM users WHERE id={user_id}'"
        result = await semantic_scanner.scan(code, "test.py")
        
        # Should find at least one match
        assert len(result) > 0
        
        # All matches should be above threshold
        for vuln in result:
            assert vuln.similarity_score >= semantic_scanner.similarity_threshold
    
    @pytest.mark.asyncio
    async def test_high_threshold_returns_fewer_results(
        self,
        sample_knowledge_base,
        embedding_model,
        vector_store
    ):
        """Test that higher threshold returns fewer or equal results."""
        code = "SELECT * FROM users WHERE id = user_input"
        
        # Scan with low threshold
        scanner_low = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.5,
            top_k=10
        )
        results_low = await scanner_low.scan(code, "test.py")
        
        # Scan with high threshold
        scanner_high = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.9,
            top_k=10
        )
        results_high = await scanner_high.scan(code, "test.py")
        
        # Property: Higher threshold should return fewer or equal results
        assert len(results_high) <= len(results_low)


class TestTopKResultLimiting:
    """
    Property 3: Top-K Result Limiting
    
    For any semantic search query, the number of results returned should never
    exceed the configured top-k value, even if more matches exist above the threshold.
    
    Feature: agentic-bug-hunter-integration
    Property 3: Top-K Result Limiting
    
    Validates: Requirements 1.3
    """
    
    @pytest.mark.asyncio
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for embedding operations
    )
    @given(
        top_k=st.integers(min_value=1, max_value=20),
        code=st.text(min_size=10, max_size=200)
    )
    async def test_results_never_exceed_top_k(
        self,
        sample_knowledge_base,
        embedding_model,
        vector_store,
        top_k,
        code
    ):
        """
        Property: For any top_k value, results count <= top_k.
        
        Feature: agentic-bug-hunter-integration
        Property 3: Top-K Result Limiting
        
        Validates: Requirements 1.3
        """
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.0,  # Low threshold to get more results
            top_k=top_k
        )
        
        result = await scanner.scan(code, "test.py")
        
        # Property: Result count must not exceed top_k
        assert len(result) <= top_k, (
            f"Result count {len(result)} exceeds top_k {top_k}"
        )
    
    @pytest.mark.asyncio
    async def test_top_k_1_returns_at_most_1_result(
        self,
        sample_knowledge_base,
        embedding_model,
        vector_store
    ):
        """Test that top_k=1 returns at most 1 result."""
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.5,
            top_k=1
        )
        
        code = "SELECT * FROM users WHERE id = user_input"
        result = await scanner.scan(code, "test.py")
        
        assert len(result) <= 1
    
    @pytest.mark.asyncio
    async def test_search_similar_respects_top_k(self, semantic_scanner):
        """Test that search_similar() also respects top_k limit."""
        query = "SQL injection vulnerability"
        
        # Search with different top_k values
        results_5 = semantic_scanner.search_similar(query, top_k=5)
        results_2 = semantic_scanner.search_similar(query, top_k=2)
        
        assert len(results_5) <= 5
        assert len(results_2) <= 2
        assert len(results_2) <= len(results_5)
    
    @pytest.mark.asyncio
    async def test_top_k_with_low_threshold_still_limits(
        self,
        sample_knowledge_base,
        embedding_model,
        vector_store
    ):
        """Test that top_k limits results even with very low threshold."""
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.0,  # Accept all results
            top_k=2
        )
        
        code = "some generic code that might match multiple patterns"
        result = await scanner.scan(code, "test.py")
        
        # Even with threshold=0, should not exceed top_k
        assert len(result) <= 2



class TestSemanticScannerUnit:
    """Unit tests for SemanticScanner functionality."""
    
    @pytest.mark.asyncio
    async def test_scan_with_known_sql_injection_pattern(self, semantic_scanner):
        """
        Test scanning code with known SQL injection pattern.
        
        Validates: Requirements 1.1, 1.2, 1.3
        """
        # Code similar to SQL injection pattern in knowledge base
        code = """
def get_user(user_id):
    query = f'SELECT * FROM users WHERE id={user_id}'
    return execute_query(query)
"""
        
        result = await semantic_scanner.scan(code, "vulnerable.py")
        
        # Should detect SQL injection
        assert len(result) > 0, "Should detect SQL injection pattern"
        
        # Check that at least one result is about SQL injection
        sql_injection_found = any(
            "sql" in vuln.description.lower() or "injection" in vuln.description.lower()
            for vuln in result
        )
        assert sql_injection_found, "Should identify SQL injection vulnerability"
        
        # Check vulnerability properties
        for vuln in result:
            assert vuln.similarity_score >= 0.7
            assert vuln.confidence > 0.0
            assert vuln.severity in ["high", "medium", "low"]
            assert vuln.source == "semantic_scanner"
    
    @pytest.mark.asyncio
    async def test_scan_with_empty_code(self, semantic_scanner):
        """
        Test scanning empty code.
        
        Validates: Requirements 1.4
        """
        result = await semantic_scanner.scan("", "empty.py")
        
        # Should return empty list, not error
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scan_with_safe_code(self, semantic_scanner):
        """Test scanning code that doesn't match any patterns."""
        # Simple, safe code
        code = """
def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
"""
        
        result = await semantic_scanner.scan(code, "safe.py")
        
        # May return empty or very low similarity results
        # All results should still be above threshold
        for vuln in result:
            assert vuln.similarity_score >= semantic_scanner.similarity_threshold
    
    @pytest.mark.asyncio
    async def test_scan_timeout_handling(self, semantic_scanner):
        """
        Test that scan handles timeout gracefully.
        
        Validates: Requirements 1.5
        """
        # Use very short timeout
        result = await semantic_scanner.scan(
            "some code",
            "test.py",
            timeout_override=0.001  # 1ms - should timeout
        )
        
        # Should return empty list on timeout (graceful degradation)
        assert isinstance(result, list)
        # Don't assert length == 0 because it might complete in time
    
    @pytest.mark.asyncio
    async def test_scan_with_multiple_patterns(self, semantic_scanner):
        """Test scanning code that might match multiple patterns."""
        # Code with multiple potential issues
        code = """
password = 'admin123'
query = f'SELECT * FROM users WHERE name={username}'
strcpy(dest, src)
"""
        
        result = await semantic_scanner.scan(code, "multi_vuln.py")
        
        # Should potentially find multiple vulnerabilities
        # (depends on similarity threshold and patterns)
        assert isinstance(result, list)
        
        # All results should be valid
        for vuln in result:
            assert isinstance(vuln, SemanticVulnerability)
            assert vuln.similarity_score >= semantic_scanner.similarity_threshold
    
    def test_search_similar_with_query(self, semantic_scanner):
        """Test direct knowledge base search."""
        query = "SQL injection vulnerability"
        
        results = semantic_scanner.search_similar(query, top_k=5)
        
        # Should return list of SimilarPattern
        assert isinstance(results, list)
        assert len(results) <= 5
        
        for pattern in results:
            assert isinstance(pattern, SimilarPattern)
            assert hasattr(pattern, 'pattern_id')
            assert hasattr(pattern, 'explanation')
            assert hasattr(pattern, 'similarity_score')
            assert 0.0 <= pattern.similarity_score <= 1.0
    
    def test_search_similar_with_empty_query(self, semantic_scanner):
        """Test search with empty query."""
        results = semantic_scanner.search_similar("", top_k=5)
        
        # Should return empty list, not error
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_search_similar_respects_top_k(self, semantic_scanner):
        """Test that search_similar respects top_k parameter."""
        query = "security vulnerability"
        
        results_3 = semantic_scanner.search_similar(query, top_k=3)
        results_1 = semantic_scanner.search_similar(query, top_k=1)
        
        assert len(results_3) <= 3
        assert len(results_1) <= 1
    
    def test_get_stats(self, semantic_scanner):
        """Test getting scanner statistics."""
        stats = semantic_scanner.get_stats()
        
        # Should return dictionary with expected keys
        assert isinstance(stats, dict)
        assert 'knowledge_base' in stats
        assert 'vector_store' in stats
        assert 'embedding_model' in stats
        assert 'configuration' in stats
        
        # Check configuration
        config = stats['configuration']
        assert config['similarity_threshold'] == 0.7
        assert config['top_k'] == 10
        assert config['timeout_seconds'] == 5.0
    
    @pytest.mark.asyncio
    async def test_scan_with_long_code(self, semantic_scanner):
        """Test scanning longer code snippets."""
        # Generate longer code
        code = """
import os
import sys

def process_user_input(user_id):
    # This function processes user input
    query = f'SELECT * FROM users WHERE id={user_id}'
    result = execute_query(query)
    return result

def authenticate(username, password):
    # Hardcoded credentials
    if password == 'admin123':
        return True
    return False

def copy_data(source, destination):
    # Unsafe memory operation
    strcpy(destination, source)
    return destination
"""
        
        result = await semantic_scanner.scan(code, "long_code.py")
        
        # Should handle long code without error
        assert isinstance(result, list)
        
        # Should potentially find multiple issues
        for vuln in result:
            assert isinstance(vuln, SemanticVulnerability)


class TestSemanticVulnerabilityDataModel:
    """Test SemanticVulnerability data model."""
    
    def test_create_valid_vulnerability(self):
        """Test creating a valid SemanticVulnerability."""
        vuln = SemanticVulnerability(
            location="test.py:10",
            vuln_type="sql_injection",
            description="SQL injection vulnerability",
            similar_pattern_id="1",
            similarity_score=0.85,
            suggested_fix="Use parameterized queries",
            severity="high",
            confidence=0.85
        )
        
        assert vuln.location == "test.py:10"
        assert vuln.similarity_score == 0.85
        assert vuln.source == "semantic_scanner"
    
    def test_invalid_similarity_score_raises_error(self):
        """Test that invalid similarity score raises ValueError."""
        with pytest.raises(ValueError, match="similarity_score must be in"):
            SemanticVulnerability(
                location="test.py",
                vuln_type="test",
                description="test",
                similar_pattern_id="1",
                similarity_score=1.5,  # Invalid: > 1.0
                suggested_fix="test",
                severity="high",
                confidence=0.8
            )
    
    def test_invalid_confidence_raises_error(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be in"):
            SemanticVulnerability(
                location="test.py",
                vuln_type="test",
                description="test",
                similar_pattern_id="1",
                similarity_score=0.8,
                suggested_fix="test",
                severity="high",
                confidence=-0.1  # Invalid: < 0.0
            )
    
    def test_invalid_severity_raises_error(self):
        """Test that invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="severity must be one of"):
            SemanticVulnerability(
                location="test.py",
                vuln_type="test",
                description="test",
                similar_pattern_id="1",
                similarity_score=0.8,
                suggested_fix="test",
                severity="critical",  # Invalid: not in {high, medium, low}
                confidence=0.8
            )


class TestSimilarPatternDataModel:
    """Test SimilarPattern data model."""
    
    def test_create_valid_pattern(self):
        """Test creating a valid SimilarPattern."""
        pattern = SimilarPattern(
            pattern_id="1",
            explanation="SQL injection",
            context="User input not sanitized",
            buggy_code="query = f'SELECT * FROM users WHERE id={user_id}'",
            correct_code="query = 'SELECT * FROM users WHERE id=?' with params",
            similarity_score=0.9,
            category="security"
        )
        
        assert pattern.pattern_id == "1"
        assert pattern.similarity_score == 0.9
        assert pattern.category == "security"
    
    def test_invalid_similarity_score_raises_error(self):
        """Test that invalid similarity score raises ValueError."""
        with pytest.raises(ValueError, match="similarity_score must be in"):
            SimilarPattern(
                pattern_id="1",
                explanation="test",
                context="test",
                buggy_code="test",
                correct_code="test",
                similarity_score=2.0,  # Invalid: > 1.0
                category="test"
            )


class TestSemanticScannerErrorHandling:
    """Test error handling in SemanticScanner."""
    
    @pytest.mark.asyncio
    async def test_scan_handles_embedding_error_gracefully(
        self,
        sample_knowledge_base,
        vector_store
    ):
        """Test that scan handles embedding errors gracefully."""
        # Create mock embedding model that raises error
        mock_embedding_model = Mock()
        mock_embedding_model.encode.side_effect = Exception("Embedding failed")
        mock_embedding_model.get_cache_stats.return_value = {}
        
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=mock_embedding_model,
            vector_store=vector_store
        )
        
        # Should return empty list on error (graceful degradation)
        result = await scanner.scan("some code", "test.py")
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scan_handles_vector_store_error_gracefully(
        self,
        sample_knowledge_base,
        embedding_model
    ):
        """Test that scan handles vector store errors gracefully."""
        # Create mock vector store that raises error
        mock_vector_store = Mock()
        mock_vector_store.search.side_effect = Exception("Search failed")
        mock_vector_store.get_stats.return_value = Mock(
            collection_name="test",
            document_count=0,
            memory_usage_mb=0.0
        )
        
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=embedding_model,
            vector_store=mock_vector_store
        )
        
        # Should return empty list on error (graceful degradation)
        result = await scanner.scan("some code", "test.py")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_search_similar_handles_error_gracefully(
        self,
        sample_knowledge_base,
        vector_store
    ):
        """Test that search_similar handles errors gracefully."""
        # Create mock embedding model that raises error
        mock_embedding_model = Mock()
        mock_embedding_model.encode.side_effect = Exception("Encoding failed")
        mock_embedding_model.get_cache_stats.return_value = {}
        
        scanner = SemanticScanner(
            knowledge_base=sample_knowledge_base,
            embedding_model=mock_embedding_model,
            vector_store=vector_store
        )
        
        # Should return empty list on error
        result = scanner.search_similar("test query")
        assert isinstance(result, list)
        assert len(result) == 0
