"""
Tests for workflow nodes (semantic scanner, validator suite, merge results).

This module tests the LangGraph nodes for semantic scanning integration.
"""

import pytest
import asyncio
from hypothesis import given, settings, strategies as st, HealthCheck
from typing import List

from agent.state import (
    AgentState,
    Vulnerability,
    SemanticVulnerability,
    HardwareViolation,
    LifecycleViolation,
    APITypoSuggestion
)
from agent.nodes.workflow_nodes import (
    semantic_scanner_node,
    validator_suite_node,
    merge_results_node
)
from agent.nodes.semantic_scanner import SemanticScanner
from agent.validators.validator_suite import ValidatorSuite
from agent.knowledge.knowledge_base import KnowledgeBase
from agent.knowledge.embedding_model import EmbeddingModel
from agent.knowledge.vector_store import VectorStore


# Fixtures for testing

@pytest.fixture
def mock_semantic_scanner(tmp_path):
    """Create a mock semantic scanner for testing."""
    # Create minimal knowledge base with correct column names
    kb_path = tmp_path / "samples.csv"
    kb_path.write_text(
        "ID,Explanation,Context,Code,Correct Code,Category,Severity\n"
        "1,SQL Injection,User input in query,execute(f'SELECT * FROM users WHERE id={user_id}'),"
        "execute('SELECT * FROM users WHERE id=?', (user_id,)),SQL Injection,high\n"
    )
    
    # Initialize components
    kb = KnowledgeBase(str(kb_path))
    em = EmbeddingModel()
    vs = VectorStore(persist_directory=str(tmp_path / "vector_store"))
    
    # Build vector store
    patterns = kb.load_patterns()
    if patterns:
        embeddings = em.encode_batch([p.buggy_code for p in patterns])
        vs.add_embeddings(
            embeddings=embeddings,
            documents=[p.buggy_code for p in patterns],
            metadatas=[{"category": p.category} for p in patterns],
            ids=[p.id for p in patterns]
        )
    
    return SemanticScanner(
        knowledge_base=kb,
        embedding_model=em,
        vector_store=vs,
        similarity_threshold=0.7,
        top_k=10
    )


@pytest.fixture
def mock_validator_suite():
    """Create a mock validator suite for testing."""
    return ValidatorSuite(
        enable_hardware=True,
        enable_lifecycle=True,
        enable_api_typo=True
    )


# Property-Based Tests

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    static_vulns=st.lists(
        st.builds(
            Vulnerability,
            location=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=5, max_size=20),
            vuln_type=st.sampled_from(["SQL Injection", "XSS", "Command Injection"]),
            severity=st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            description=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=5, max_size=50),
            confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        max_size=5
    ),
    semantic_vulns=st.lists(
        st.builds(
            SemanticVulnerability,
            location=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=5, max_size=20),
            vuln_type=st.sampled_from(["SQL Injection", "XSS", "Command Injection"]),
            description=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=5, max_size=50),
            similar_pattern_id=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=3, max_size=10),
            similarity_score=st.floats(min_value=0.7, max_value=1.0, allow_nan=False, allow_infinity=False),
            suggested_fix=st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=5, max_size=50),
            severity=st.sampled_from(["high", "medium", "low"]),
            confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        max_size=5
    )
)
def test_property_parallel_scanner_result_merging(static_vulns, semantic_vulns):
    """
    Feature: agentic-bug-hunter-integration
    Property 6: Parallel Scanner Result Merging
    
    For any code analysis, when both static scanner and semantic scanner complete
    successfully, the merged results should contain all vulnerabilities from both
    sources without duplicates (based on location and type).
    
    Validates: Requirements 3.2
    """
    # Create state with vulnerabilities from both scanners
    state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": static_vulns,
        "semantic_vulnerabilities": semantic_vulns,
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    # Run merge
    merged_state = merge_results_node(state)
    merged_vulns = merged_state["vulnerabilities"]
    
    # Property 1: All static vulnerabilities should be present
    static_locations_types = {(v.location, v.vuln_type) for v in static_vulns}
    merged_locations_types = {(v.location, v.vuln_type) for v in merged_vulns}
    
    assert static_locations_types.issubset(merged_locations_types), \
        "All static vulnerabilities should be in merged results"
    
    # Property 2: Semantic vulnerabilities should be added if not duplicates
    for sem_vuln in semantic_vulns:
        pair = (sem_vuln.location, sem_vuln.vuln_type)
        
        # If this pair is not in static vulns, it should be in merged
        if pair not in static_locations_types:
            assert pair in merged_locations_types, \
                f"Non-duplicate semantic vulnerability {pair} should be in merged results"
    
    # Property 3: No duplicates in merged results (based on location and type)
    assert len(merged_locations_types) == len(merged_vulns), \
        "Merged results should not contain duplicates"
    
    # Property 4: Merged count should be <= sum of both (due to deduplication)
    assert len(merged_vulns) <= len(static_vulns) + len(semantic_vulns), \
        "Merged count should not exceed sum of both scanners"
    
    # Property 5: Merged count should equal the number of unique (location, type) pairs
    # from both scanners combined
    all_pairs = set()
    for v in static_vulns:
        all_pairs.add((v.location, v.vuln_type))
    for v in semantic_vulns:
        all_pairs.add((v.location, v.vuln_type))
    
    assert len(merged_vulns) == len(all_pairs), \
        f"Merged count should equal unique pairs: {len(merged_vulns)} != {len(all_pairs)}"


# Unit Tests

@pytest.mark.asyncio
async def test_semantic_scanner_node_with_code(mock_semantic_scanner):
    """Test semantic_scanner_node with valid code."""
    state: AgentState = {
        "code": "execute(f'SELECT * FROM users WHERE id={user_id}')",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = await semantic_scanner_node(state, mock_semantic_scanner)
    
    # Should have semantic_vulnerabilities field
    assert "semantic_vulnerabilities" in result_state
    assert isinstance(result_state["semantic_vulnerabilities"], list)
    
    # Should have logs
    assert len(result_state["logs"]) > 0
    assert any("Semantic Scanner" in log for log in result_state["logs"])


@pytest.mark.asyncio
async def test_semantic_scanner_node_with_empty_code(mock_semantic_scanner):
    """Test semantic_scanner_node with empty code."""
    state: AgentState = {
        "code": "",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = await semantic_scanner_node(state, mock_semantic_scanner)
    
    # Should return empty results
    assert result_state["semantic_vulnerabilities"] == []
    
    # Should have log about empty code
    assert any("Empty code" in log for log in result_state["logs"])


@pytest.mark.asyncio
async def test_semantic_scanner_node_error_handling(mock_semantic_scanner, monkeypatch):
    """Test semantic_scanner_node handles errors gracefully."""
    # Mock the scanner to raise an exception
    async def mock_scan_error(*args, **kwargs):
        raise RuntimeError("Simulated scanner error")
    
    monkeypatch.setattr(mock_semantic_scanner, "scan", mock_scan_error)
    
    state: AgentState = {
        "code": "valid code",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = await semantic_scanner_node(state, mock_semantic_scanner)
    
    # Should not crash, should return empty results
    assert "semantic_vulnerabilities" in result_state
    assert result_state["semantic_vulnerabilities"] == []
    
    # Should have error logged
    assert len(result_state["errors"]) > 0
    assert any("Error" in error for error in result_state["errors"])


def test_validator_suite_node_with_hardware_code(mock_validator_suite):
    """Test validator_suite_node with hardware API calls."""
    state: AgentState = {
        "code": "set_voltage(50)  # Exceeds 30V limit",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = validator_suite_node(state, mock_validator_suite)
    
    # Should have validation results
    assert "hardware_violations" in result_state
    assert "lifecycle_violations" in result_state
    assert "api_typo_suggestions" in result_state
    
    # Should detect voltage violation
    assert len(result_state["hardware_violations"]) > 0
    
    # Should have logs
    assert len(result_state["logs"]) > 0


def test_validator_suite_node_with_lifecycle_code(mock_validator_suite):
    """Test validator_suite_node with lifecycle calls."""
    state: AgentState = {
        "code": "RDI_END()\nRDI_BEGIN()  # Wrong order",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = validator_suite_node(state, mock_validator_suite)
    
    # Should detect lifecycle violation
    assert len(result_state["lifecycle_violations"]) > 0


def test_validator_suite_node_with_empty_code(mock_validator_suite):
    """Test validator_suite_node with empty code."""
    state: AgentState = {
        "code": "",
        "file_path": "test.py",
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = validator_suite_node(state, mock_validator_suite)
    
    # Should return empty results
    assert result_state["hardware_violations"] == []
    assert result_state["lifecycle_violations"] == []
    assert result_state["api_typo_suggestions"] == []


def test_merge_results_node_with_overlapping_results():
    """Test merge_results_node with overlapping vulnerabilities."""
    # Create overlapping vulnerabilities
    static_vulns = [
        Vulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Static detection",
            confidence=0.8
        ),
        Vulnerability(
            location="test.py:20",
            vuln_type="XSS",
            severity="MEDIUM",
            description="Static detection",
            confidence=0.7
        )
    ]
    
    semantic_vulns = [
        SemanticVulnerability(
            location="test.py:10",  # Duplicate location and type
            vuln_type="SQL Injection",
            description="Semantic detection",
            similar_pattern_id="pattern1",
            similarity_score=0.9,
            suggested_fix="Use parameterized queries",
            severity="high",
            confidence=0.85
        ),
        SemanticVulnerability(
            location="test.py:30",  # Unique
            vuln_type="Command Injection",
            description="Semantic detection",
            similar_pattern_id="pattern2",
            similarity_score=0.8,
            suggested_fix="Avoid shell=True",
            severity="high",
            confidence=0.8
        )
    ]
    
    state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": static_vulns,
        "semantic_vulnerabilities": semantic_vulns,
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = merge_results_node(state)
    merged_vulns = result_state["vulnerabilities"]
    
    # Should have 3 vulnerabilities (2 static + 1 unique semantic)
    assert len(merged_vulns) == 3
    
    # Should have the duplicate removed
    locations_types = [(v.location, v.vuln_type) for v in merged_vulns]
    assert locations_types.count(("test.py:10", "SQL Injection")) == 1
    
    # Should have all unique ones
    assert ("test.py:20", "XSS") in locations_types
    assert ("test.py:30", "Command Injection") in locations_types


def test_merge_results_node_with_no_duplicates():
    """Test merge_results_node with no overlapping vulnerabilities."""
    static_vulns = [
        Vulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Static detection",
            confidence=0.8
        )
    ]
    
    semantic_vulns = [
        SemanticVulnerability(
            location="test.py:20",
            vuln_type="XSS",
            description="Semantic detection",
            similar_pattern_id="pattern1",
            similarity_score=0.9,
            suggested_fix="Sanitize input",
            severity="medium",
            confidence=0.85
        )
    ]
    
    state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": static_vulns,
        "semantic_vulnerabilities": semantic_vulns,
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = merge_results_node(state)
    merged_vulns = result_state["vulnerabilities"]
    
    # Should have both vulnerabilities
    assert len(merged_vulns) == 2


def test_merge_results_node_with_empty_semantic():
    """Test merge_results_node with no semantic vulnerabilities."""
    static_vulns = [
        Vulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Static detection",
            confidence=0.8
        )
    ]
    
    state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": static_vulns,
        "semantic_vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    result_state = merge_results_node(state)
    merged_vulns = result_state["vulnerabilities"]
    
    # Should have only static vulnerabilities
    assert len(merged_vulns) == 1
    assert merged_vulns[0].location == "test.py:10"
