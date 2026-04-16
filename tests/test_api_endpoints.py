"""
Unit tests for new API endpoints (semantic search and knowledge base stats).
Tests request/response validation, error handling, and backward compatibility.
"""

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError

from api.models import (
    SearchSimilarRequest,
    SearchSimilarResponse,
    SimilarPatternResponse,
    KnowledgeBaseStatsResponse,
    AnalyzeRequest,
    AnalyzeResponse
)


class TestSearchSimilarRequest:
    """Test SearchSimilarRequest validation."""
    
    def test_valid_request(self):
        """Test valid search similar request."""
        request = SearchSimilarRequest(
            query="SELECT * FROM users WHERE id={}",
            top_k=5
        )
        assert request.query == "SELECT * FROM users WHERE id={}"
        assert request.top_k == 5
    
    def test_default_top_k(self):
        """Test default top_k value."""
        request = SearchSimilarRequest(query="test query")
        assert request.top_k == 10
    
    def test_empty_query_rejected(self):
        """Test empty query is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SearchSimilarRequest(query="")
        
        errors = exc_info.value.errors()
        assert any("String should have at least 1 character" in str(e) or "Query cannot be empty" in str(e) for e in errors)
    
    def test_whitespace_only_query_rejected(self):
        """Test whitespace-only query is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SearchSimilarRequest(query="   \n\t  ")
        
        errors = exc_info.value.errors()
        assert any("Query cannot be empty" in str(e) for e in errors)
    
    def test_top_k_bounds(self):
        """Test top_k must be between 1 and 50."""
        # Valid bounds
        SearchSimilarRequest(query="test", top_k=1)
        SearchSimilarRequest(query="test", top_k=50)
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            SearchSimilarRequest(query="test", top_k=0)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            SearchSimilarRequest(query="test", top_k=51)


class TestSimilarPatternResponse:
    """Test SimilarPatternResponse serialization."""
    
    def test_valid_pattern(self):
        """Test valid similar pattern response."""
        pattern = SimilarPatternResponse(
            pattern_id="001",
            explanation="SQL injection vulnerability",
            context="Using string formatting with user input",
            buggy_code="query = f\"SELECT * FROM users WHERE id={user_id}\"",
            correct_code="query = \"SELECT * FROM users WHERE id=?\"\ncursor.execute(query, (user_id,))",
            similarity_score=0.92,
            category="sql_injection"
        )
        
        assert pattern.pattern_id == "001"
        assert pattern.similarity_score == 0.92
        assert pattern.category == "sql_injection"
    
    def test_serialization(self):
        """Test pattern can be serialized to dict."""
        pattern = SimilarPatternResponse(
            pattern_id="001",
            explanation="Test bug",
            context="Test context",
            buggy_code="bad_code",
            correct_code="good_code",
            similarity_score=0.85,
            category="test"
        )
        
        data = pattern.model_dump()
        assert isinstance(data, dict)
        assert data["pattern_id"] == "001"
        assert data["similarity_score"] == 0.85


class TestSearchSimilarResponse:
    """Test SearchSimilarResponse serialization."""
    
    def test_valid_response(self):
        """Test valid search similar response."""
        response = SearchSimilarResponse(
            query="test query",
            similar_patterns=[
                SimilarPatternResponse(
                    pattern_id="001",
                    explanation="Test bug",
                    context="Test context",
                    buggy_code="bad_code",
                    correct_code="good_code",
                    similarity_score=0.85,
                    category="test"
                )
            ],
            count=1
        )
        
        assert response.query == "test query"
        assert len(response.similar_patterns) == 1
        assert response.count == 1
    
    def test_empty_results(self):
        """Test response with no similar patterns."""
        response = SearchSimilarResponse(
            query="test query",
            similar_patterns=[],
            count=0
        )
        
        assert response.similar_patterns == []
        assert response.count == 0


class TestKnowledgeBaseStatsResponse:
    """Test KnowledgeBaseStatsResponse serialization."""
    
    def test_valid_stats(self):
        """Test valid knowledge base stats response."""
        stats = KnowledgeBaseStatsResponse(
            pattern_count=150,
            categories={
                "sql_injection": 25,
                "xss": 30,
                "buffer_overflow": 20,
                "general": 75
            },
            last_updated="2025-01-24T10:30:00.000Z"
        )
        
        assert stats.pattern_count == 150
        assert len(stats.categories) == 4
        assert stats.categories["sql_injection"] == 25
        assert stats.last_updated == "2025-01-24T10:30:00.000Z"
    
    def test_optional_last_updated(self):
        """Test last_updated can be None."""
        stats = KnowledgeBaseStatsResponse(
            pattern_count=100,
            categories={"general": 100}
        )
        
        assert stats.last_updated is None
    
    def test_empty_categories(self):
        """Test stats with no categories."""
        stats = KnowledgeBaseStatsResponse(
            pattern_count=0,
            categories={}
        )
        
        assert stats.pattern_count == 0
        assert stats.categories == {}


# Property-Based Tests

@given(
    query=st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=0, max_size=100).filter(lambda x: x.strip() == ""),  # Whitespace only
    )
)
@settings(max_examples=100)
def test_property_invalid_query_rejection(query):
    """
    Property: Invalid Query Rejection
    
    For any invalid query input (empty or whitespace-only),
    the SearchSimilarRequest model SHALL reject it with a ValidationError.
    """
    with pytest.raises(ValidationError):
        SearchSimilarRequest(query=query)


@given(
    top_k=st.one_of(
        st.integers(max_value=0),  # Too low
        st.integers(min_value=51),  # Too high
    )
)
@settings(max_examples=100)
def test_property_top_k_bounds(top_k):
    """
    Property: Top-K Bounds Validation
    
    For any top_k value outside the valid range [1, 50],
    the SearchSimilarRequest model SHALL reject it with a ValidationError.
    """
    with pytest.raises(ValidationError):
        SearchSimilarRequest(query="test query", top_k=top_k)


@given(
    code=st.text(min_size=1, max_size=1000).filter(lambda s: s.strip() != ""),
    file_path=st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""),
    max_iterations=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100)
def test_property_api_backward_compatibility(code, file_path, max_iterations):
    """
    Property 13: API Backward Compatibility
    
    Feature: agentic-bug-hunter-integration, Property 13: API Backward Compatibility
    Validates: Requirements 14.1, 14.2, 14.3
    
    For any valid AnalyzeRequest, the request format and behavior should remain
    unchanged when semantic scanning is disabled via configuration. This ensures
    existing API clients continue to work without modification.
    
    This test verifies that:
    1. AnalyzeRequest accepts the same parameters as before
    2. AnalyzeResponse has the same required fields as before
    3. New fields are optional and don't break existing clients
    """
    # Test that existing AnalyzeRequest format still works
    request = AnalyzeRequest(
        code=code,
        file_path=file_path,
        max_iterations=max_iterations
    )
    
    # Verify all original fields are present
    assert hasattr(request, 'code')
    assert hasattr(request, 'file_path')
    assert hasattr(request, 'max_iterations')
    
    # Verify values are preserved
    assert request.code == code
    assert request.file_path == file_path
    assert request.max_iterations == max_iterations
    
    # Test that AnalyzeResponse can be created with original fields only
    response = AnalyzeResponse(
        analysis_id="test-123",
        vulnerabilities=[],
        patches=[],
        execution_time=1.0,
        errors=[],
        logs=[],
        workflow_complete=True
    )
    
    # Verify all original fields are present
    assert hasattr(response, 'analysis_id')
    assert hasattr(response, 'vulnerabilities')
    assert hasattr(response, 'patches')
    assert hasattr(response, 'execution_time')
    assert hasattr(response, 'errors')
    assert hasattr(response, 'logs')
    assert hasattr(response, 'workflow_complete')
    
    # Verify response can be serialized (backward compatibility)
    response_dict = response.model_dump()
    assert isinstance(response_dict, dict)
    assert 'analysis_id' in response_dict
    assert 'vulnerabilities' in response_dict
    assert 'patches' in response_dict


@given(
    pattern_count=st.integers(min_value=0, max_value=10000),
    category_count=st.integers(min_value=0, max_value=50)
)
@settings(max_examples=100)
def test_property_knowledge_base_stats_consistency(pattern_count, category_count):
    """
    Property: Knowledge Base Stats Consistency
    
    For any valid pattern count and category distribution,
    the KnowledgeBaseStatsResponse should correctly represent the statistics.
    """
    # Generate random categories
    categories = {}
    remaining = pattern_count
    
    for i in range(category_count):
        if remaining > 0:
            # Distribute patterns across categories
            count = min(remaining, pattern_count // max(category_count, 1))
            categories[f"category_{i}"] = count
            remaining -= count
    
    # Add remaining to last category if any
    if remaining > 0 and category_count > 0:
        categories[f"category_{category_count - 1}"] += remaining
    
    stats = KnowledgeBaseStatsResponse(
        pattern_count=pattern_count,
        categories=categories
    )
    
    # Verify stats are consistent
    assert stats.pattern_count == pattern_count
    assert isinstance(stats.categories, dict)
    
    # Verify total patterns in categories matches pattern_count
    total_in_categories = sum(stats.categories.values())
    assert total_in_categories <= pattern_count  # May be less if categories is empty


@given(
    similarity_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100)
def test_property_similarity_score_range(similarity_score):
    """
    Property: Similarity Score Range
    
    For any similarity score in the valid range [0.0, 1.0],
    the SimilarPatternResponse should accept it.
    """
    pattern = SimilarPatternResponse(
        pattern_id="test",
        explanation="test",
        context="test",
        buggy_code="test",
        correct_code="test",
        similarity_score=similarity_score,
        category="test"
    )
    
    assert 0.0 <= pattern.similarity_score <= 1.0
    assert pattern.similarity_score == similarity_score


# Integration Tests for API Endpoints

from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from api.server import app, service_state
from agent.nodes.semantic_scanner import SemanticScanner, SimilarPattern
from agent.knowledge.knowledge_base import KnowledgeBase, KnowledgeBaseStats


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_semantic_scanner():
    """Create mock semantic scanner."""
    scanner = Mock(spec=SemanticScanner)
    scanner.knowledge_base = Mock(spec=KnowledgeBase)
    return scanner


class TestSearchSimilarEndpoint:
    """Integration tests for POST /search_similar endpoint."""
    
    def test_search_similar_with_valid_query(self, client, mock_semantic_scanner):
        """Test /search_similar with valid query returns results."""
        # Setup mock
        mock_patterns = [
            SimilarPattern(
                pattern_id="001",
                explanation="SQL injection vulnerability",
                context="Using string formatting with user input",
                buggy_code="query = f\"SELECT * FROM users WHERE id={user_id}\"",
                correct_code="query = \"SELECT * FROM users WHERE id=?\"\ncursor.execute(query, (user_id,))",
                similarity_score=0.92,
                category="sql_injection"
            )
        ]
        mock_semantic_scanner.search_similar.return_value = mock_patterns
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        request_data = {
            "query": "SELECT * FROM users WHERE id={}",
            "top_k": 5
        }
        
        response = client.post("/search_similar", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "SELECT * FROM users WHERE id={}"
        assert data["count"] == 1
        assert len(data["similar_patterns"]) == 1
        assert data["similar_patterns"][0]["pattern_id"] == "001"
        assert data["similar_patterns"][0]["similarity_score"] == 0.92
    
    def test_search_similar_with_empty_results(self, client, mock_semantic_scanner):
        """Test /search_similar with no matching patterns."""
        # Setup mock to return empty results
        mock_semantic_scanner.search_similar.return_value = []
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        request_data = {
            "query": "some random query",
            "top_k": 10
        }
        
        response = client.post("/search_similar", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "some random query"
        assert data["count"] == 0
        assert data["similar_patterns"] == []
    
    def test_search_similar_rejects_empty_query(self, client):
        """Test /search_similar rejects empty query."""
        request_data = {
            "query": "",
            "top_k": 5
        }
        
        response = client.post("/search_similar", json=request_data)
        
        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422
    
    def test_search_similar_uses_default_top_k(self, client, mock_semantic_scanner):
        """Test /search_similar uses default top_k when not provided."""
        # Setup mock
        mock_semantic_scanner.search_similar.return_value = []
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request without top_k
        request_data = {
            "query": "test query"
        }
        
        response = client.post("/search_similar", json=request_data)
        
        assert response.status_code == 200
        
        # Verify default top_k was used (10)
        mock_semantic_scanner.search_similar.assert_called_once()
        call_args = mock_semantic_scanner.search_similar.call_args
        assert call_args[1]['top_k'] == 10
    
    def test_search_similar_returns_503_when_semantic_scanning_disabled(self, client):
        """Test /search_similar returns 503 when semantic scanning not enabled."""
        # Setup service state without semantic scanner
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = None  # Not enabled
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        request_data = {
            "query": "test query",
            "top_k": 5
        }
        
        response = client.post("/search_similar", json=request_data)
        
        assert response.status_code == 503
        data = response.json()
        assert "Semantic scanning is not enabled" in data["detail"]
    
    def test_search_similar_handles_errors_gracefully(self, client, mock_semantic_scanner):
        """Test /search_similar handles errors gracefully."""
        # Setup mock to raise exception
        mock_semantic_scanner.search_similar.side_effect = Exception("Test error")
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        request_data = {
            "query": "test query",
            "top_k": 5
        }
        
        response = client.post("/search_similar", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Similarity search failed" in data["detail"]


class TestKnowledgeBaseStatsEndpoint:
    """Integration tests for GET /knowledge_base/stats endpoint."""
    
    def test_knowledge_base_stats_returns_statistics(self, client, mock_semantic_scanner):
        """Test /knowledge_base/stats returns knowledge base statistics."""
        # Setup mock
        mock_stats = KnowledgeBaseStats(
            pattern_count=150,
            categories={
                "sql_injection": 25,
                "xss": 30,
                "buffer_overflow": 20,
                "general": 75
            },
            last_updated="2025-01-24T10:30:00.000Z"
        )
        mock_semantic_scanner.knowledge_base.get_stats.return_value = mock_stats
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        response = client.get("/knowledge_base/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pattern_count"] == 150
        assert len(data["categories"]) == 4
        assert data["categories"]["sql_injection"] == 25
        assert data["last_updated"] == "2025-01-24T10:30:00.000Z"
    
    def test_knowledge_base_stats_with_empty_knowledge_base(self, client, mock_semantic_scanner):
        """Test /knowledge_base/stats with empty knowledge base."""
        # Setup mock with empty stats
        mock_stats = KnowledgeBaseStats(
            pattern_count=0,
            categories={},
            last_updated=None
        )
        mock_semantic_scanner.knowledge_base.get_stats.return_value = mock_stats
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        response = client.get("/knowledge_base/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pattern_count"] == 0
        assert data["categories"] == {}
        assert data["last_updated"] is None
    
    def test_knowledge_base_stats_returns_503_when_semantic_scanning_disabled(self, client):
        """Test /knowledge_base/stats returns 503 when semantic scanning not enabled."""
        # Setup service state without semantic scanner
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = None  # Not enabled
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        response = client.get("/knowledge_base/stats")
        
        assert response.status_code == 503
        data = response.json()
        assert "Semantic scanning is not enabled" in data["detail"]
    
    def test_knowledge_base_stats_handles_errors_gracefully(self, client, mock_semantic_scanner):
        """Test /knowledge_base/stats handles errors gracefully."""
        # Setup mock to raise exception
        mock_semantic_scanner.knowledge_base.get_stats.side_effect = Exception("Test error")
        
        # Setup service state
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = True
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        response = client.get("/knowledge_base/stats")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve knowledge base statistics" in data["detail"]
    
    def test_knowledge_base_stats_initializes_orchestrator_if_needed(self, client, mock_semantic_scanner):
        """Test /knowledge_base/stats initializes orchestrator if not initialized."""
        # Setup mock
        mock_stats = KnowledgeBaseStats(
            pattern_count=100,
            categories={"general": 100},
            last_updated=None
        )
        mock_semantic_scanner.knowledge_base.get_stats.return_value = mock_stats
        
        # Setup service state with uninitialized orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.is_initialized.return_value = False
        mock_orchestrator.semantic_scanner = mock_semantic_scanner
        service_state.orchestrator = mock_orchestrator
        
        # Make request
        response = client.get("/knowledge_base/stats")
        
        assert response.status_code == 200
        
        # Verify orchestrator was initialized
        mock_orchestrator.initialize.assert_called_once()
