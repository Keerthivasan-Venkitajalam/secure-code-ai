"""
Tests for enhanced LangGraph workflow with semantic scanning integration.

This module tests the integrated workflow including graceful degradation.
"""

import pytest
import asyncio
from hypothesis import given, settings, strategies as st, HealthCheck
from unittest.mock import Mock, AsyncMock, patch

from agent.state import AgentState, Vulnerability, SemanticVulnerability
from agent.graph import create_workflow
from agent.nodes.scanner import ScannerAgent
from agent.nodes.speculator import SpeculatorAgent
from agent.nodes.symbot import SymBotAgent
from agent.nodes.patcher import PatcherAgent
from agent.nodes.semantic_scanner import SemanticScanner
from agent.validators.validator_suite import ValidatorSuite


# Fixtures

@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    scanner = Mock(spec=ScannerAgent)
    scanner.execute = Mock(return_value={
        "vulnerabilities": [
            Vulnerability(
                location="test.py:10",
                vuln_type="SQL Injection",
                severity="HIGH",
                description="Test vulnerability",
                confidence=0.8
            )
        ],
        "logs": ["Scanner: Found 1 vulnerability"]
    })
    
    speculator = Mock(spec=SpeculatorAgent)
    speculator.execute = Mock(return_value={"contracts": [], "logs": []})
    
    symbot = Mock(spec=SymBotAgent)
    symbot.execute = Mock(return_value={"verification_results": [], "logs": []})
    
    patcher = Mock(spec=PatcherAgent)
    patcher.execute = Mock(return_value={"patches": [], "logs": []})
    
    binary_analyzer = Mock()
    binary_analyzer.execute = Mock(return_value={"logs": []})
    
    smart_contract_agent = Mock()
    smart_contract_agent.execute = Mock(return_value={"logs": []})
    
    return {
        "scanner": scanner,
        "speculator": speculator,
        "symbot": symbot,
        "patcher": patcher,
        "binary_analyzer": binary_analyzer,
        "smart_contract_agent": smart_contract_agent
    }


@pytest.fixture
def mock_semantic_scanner():
    """Create mock semantic scanner."""
    scanner = Mock(spec=SemanticScanner)
    
    async def mock_scan(code, file_path):
        return [
            SemanticVulnerability(
                location="test.py:20",
                vuln_type="XSS",
                description="Semantic detection",
                similar_pattern_id="pattern1",
                similarity_score=0.9,
                suggested_fix="Sanitize input",
                severity="high",
                confidence=0.85
            )
        ]
    
    scanner.scan = AsyncMock(side_effect=mock_scan)
    return scanner


@pytest.fixture
def mock_validator_suite():
    """Create mock validator suite."""
    suite = Mock(spec=ValidatorSuite)
    suite.validate = Mock(return_value=Mock(
        hardware_violations=[],
        lifecycle_violations=[],
        api_typo_suggestions=[]
    ))
    return suite


# Property-Based Tests

@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    scanner_fails=st.booleans(),
    semantic_fails=st.booleans()
)
@pytest.mark.asyncio
async def test_property_graceful_degradation(scanner_fails, semantic_fails, mock_agents):
    """
    Feature: agentic-bug-hunter-integration
    Property 7: Graceful Degradation on Scanner Failure
    
    For any code analysis, if either the static scanner or semantic scanner fails,
    the system should continue with results from the successful scanner and not
    fail the entire analysis.
    
    Validates: Requirements 3.3, 10.2
    """
    # Skip case where both fail (system should fail in this case)
    if scanner_fails and semantic_fails:
        return
    
    # Configure scanner to fail or succeed
    if scanner_fails:
        mock_agents["scanner"].execute = Mock(side_effect=RuntimeError("Scanner failed"))
    else:
        mock_agents["scanner"].execute = Mock(return_value={
            "vulnerabilities": [
                Vulnerability(
                    location="test.py:10",
                    vuln_type="SQL Injection",
                    severity="HIGH",
                    description="Static detection",
                    confidence=0.8
                )
            ],
            "logs": ["Scanner: Found 1 vulnerability"]
        })
    
    # Configure semantic scanner to fail or succeed
    if semantic_fails:
        semantic_scanner = Mock(spec=SemanticScanner)
        semantic_scanner.scan = AsyncMock(side_effect=RuntimeError("Semantic scanner failed"))
    else:
        semantic_scanner = Mock(spec=SemanticScanner)
        async def mock_scan(code, file_path):
            return [
                SemanticVulnerability(
                    location="test.py:20",
                    vuln_type="XSS",
                    description="Semantic detection",
                    similar_pattern_id="pattern1",
                    similarity_score=0.9,
                    suggested_fix="Sanitize input",
                    severity="high",
                    confidence=0.85
                )
            ]
        semantic_scanner.scan = AsyncMock(side_effect=mock_scan)
    
    # Create workflow
    workflow = create_workflow(
        scanner=mock_agents["scanner"],
        speculator=mock_agents["speculator"],
        symbot=mock_agents["symbot"],
        patcher=mock_agents["patcher"],
        binary_analyzer=mock_agents["binary_analyzer"],
        smart_contract_agent=mock_agents["smart_contract_agent"],
        semantic_scanner=semantic_scanner,
        validator_suite=None
    )
    
    # Create initial state
    initial_state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    # Run workflow - should not crash
    try:
        final_state = await workflow.ainvoke(initial_state)
        
        # Property 1: Workflow should complete without crashing
        assert final_state is not None
        
        # Property 2: Should have results from at least one scanner
        if not scanner_fails or not semantic_fails:
            # At least one scanner succeeded, so we should have some results
            # (either in vulnerabilities or in errors/logs)
            assert (
                len(final_state.get("vulnerabilities", [])) > 0 or
                len(final_state.get("errors", [])) > 0 or
                len(final_state.get("logs", [])) > 0
            )
        
        # Property 3: Errors should be logged for failed scanners
        if scanner_fails:
            assert any("Scanner" in str(e) or "failed" in str(e).lower() 
                      for e in final_state.get("errors", []) + final_state.get("logs", []))
        
        if semantic_fails:
            assert any("Semantic" in str(e) or "failed" in str(e).lower()
                      for e in final_state.get("errors", []) + final_state.get("logs", []))
        
    except Exception as e:
        # Workflow should not crash due to scanner failures
        pytest.fail(f"Workflow crashed with exception: {e}")


# Unit Tests

@pytest.mark.asyncio
async def test_workflow_with_semantic_scanner_enabled(mock_agents, mock_semantic_scanner, mock_validator_suite):
    """Test workflow with semantic scanning enabled."""
    workflow = create_workflow(
        scanner=mock_agents["scanner"],
        speculator=mock_agents["speculator"],
        symbot=mock_agents["symbot"],
        patcher=mock_agents["patcher"],
        binary_analyzer=mock_agents["binary_analyzer"],
        smart_contract_agent=mock_agents["smart_contract_agent"],
        semantic_scanner=mock_semantic_scanner,
        validator_suite=mock_validator_suite
    )
    
    initial_state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    final_state = await workflow.ainvoke(initial_state)
    
    # Should have called semantic scanner
    mock_semantic_scanner.scan.assert_called_once()
    
    # Should have called validator suite
    mock_validator_suite.validate.assert_called_once()
    
    # Should have merged results
    assert "vulnerabilities" in final_state
    assert len(final_state["vulnerabilities"]) > 0


@pytest.mark.asyncio
async def test_workflow_with_semantic_scanner_disabled(mock_agents):
    """Test workflow with semantic scanning disabled."""
    workflow = create_workflow(
        scanner=mock_agents["scanner"],
        speculator=mock_agents["speculator"],
        symbot=mock_agents["symbot"],
        patcher=mock_agents["patcher"],
        binary_analyzer=mock_agents["binary_analyzer"],
        smart_contract_agent=mock_agents["smart_contract_agent"],
        semantic_scanner=None,
        validator_suite=None
    )
    
    initial_state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    final_state = await workflow.ainvoke(initial_state)
    
    # Should still work without semantic scanner
    assert final_state is not None
    assert "vulnerabilities" in final_state


@pytest.mark.asyncio
async def test_workflow_semantic_scanner_failure_graceful(mock_agents):
    """Test that workflow continues gracefully when semantic scanner fails."""
    # Create semantic scanner that fails
    failing_scanner = Mock(spec=SemanticScanner)
    failing_scanner.scan = AsyncMock(side_effect=RuntimeError("Semantic scanner error"))
    
    workflow = create_workflow(
        scanner=mock_agents["scanner"],
        speculator=mock_agents["speculator"],
        symbot=mock_agents["symbot"],
        patcher=mock_agents["patcher"],
        binary_analyzer=mock_agents["binary_analyzer"],
        smart_contract_agent=mock_agents["smart_contract_agent"],
        semantic_scanner=failing_scanner,
        validator_suite=None
    )
    
    initial_state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    # Should not crash
    final_state = await workflow.ainvoke(initial_state)
    
    # Should have results from static scanner
    assert final_state is not None
    assert len(final_state.get("vulnerabilities", [])) > 0
    
    # Should have logged the error
    assert len(final_state.get("errors", [])) > 0 or len(final_state.get("logs", [])) > 0


@pytest.mark.asyncio
async def test_workflow_validator_suite_failure_graceful(mock_agents, mock_semantic_scanner):
    """Test that workflow continues gracefully when validator suite fails."""
    # Create validator suite that fails
    failing_validator = Mock(spec=ValidatorSuite)
    failing_validator.validate = Mock(side_effect=RuntimeError("Validator error"))
    
    workflow = create_workflow(
        scanner=mock_agents["scanner"],
        speculator=mock_agents["speculator"],
        symbot=mock_agents["symbot"],
        patcher=mock_agents["patcher"],
        binary_analyzer=mock_agents["binary_analyzer"],
        smart_contract_agent=mock_agents["smart_contract_agent"],
        semantic_scanner=mock_semantic_scanner,
        validator_suite=failing_validator
    )
    
    initial_state: AgentState = {
        "code": "test code",
        "file_path": "test.py",
        "vulnerabilities": [],
        "errors": [],
        "logs": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "workflow_complete": False,
        "total_execution_time": 0.0
    }
    
    # Should not crash
    final_state = await workflow.ainvoke(initial_state)
    
    # Should have results from scanners
    assert final_state is not None
    assert len(final_state.get("vulnerabilities", [])) > 0
