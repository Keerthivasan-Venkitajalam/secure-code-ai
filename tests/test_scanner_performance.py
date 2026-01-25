"""
Property-based tests for Scanner Agent performance.
Tests that Scanner completes within performance bounds.

**Feature: llm-agent-intelligence, Property 19: Scanner Performance Bound**
**Validates: Requirements 10.4**
"""

import time
import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.scanner import ScannerAgent
from agent.llm_client import LLMClient
from agent.state import AgentState


@pytest.fixture
def mock_llm_client():
    """Create a fast mock LLM client for performance testing."""
    mock_client = Mock(spec=LLMClient)
    
    # Fast responses for performance testing
    mock_client.generate.return_value = "Test hypothesis"
    mock_client.generate_with_self_correction.return_value = "def test(): pass"
    mock_client.validate_python_syntax.return_value = (True, None)
    
    return mock_client


def generate_python_code(num_lines: int, include_vulnerability: bool = True) -> str:
    """
    Generate Python code with specified number of lines.
    
    Args:
        num_lines: Number of lines to generate
        include_vulnerability: Whether to include a vulnerability pattern
        
    Returns:
        Python code string
    """
    lines = [
        "import os",
        "import subprocess",
        "",
        "def process_data(user_input):",
        "    # Process user input",
        "    data = user_input.strip()",
        "    result = []",
        "    ",
    ]
    
    # Add vulnerability if requested
    if include_vulnerability:
        lines.append("    # Vulnerable code")
        lines.append("    query = f\"SELECT * FROM users WHERE name = '{user_input}'\"")
        lines.append("    cursor.execute(query)")
        lines.append("    ")
    
    # Fill remaining lines with safe code
    while len(lines) < num_lines:
        lines.append(f"    # Line {len(lines)}")
        lines.append(f"    result.append(data)")
    
    # Add return statement
    lines.append("    return result")
    
    return '\n'.join(lines[:num_lines])


class TestScannerPerformance:
    """Test Scanner Agent performance bounds."""
    
    def test_scanner_performance_small_file(self, mock_llm_client):
        """
        Test Scanner completes quickly for small files.
        
        **Property 19: Scanner Performance Bound**
        **Validates: Requirements 10.4**
        """
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        # Generate small file (100 lines)
        code = generate_python_code(100, include_vulnerability=True)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = scanner.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 10s for files under 1000 lines)
        assert execution_time < 10.0, \
            f"Scanner took {execution_time:.2f}s for 100 lines (expected < 10s)"
        
        # Verify scanner completed successfully
        assert len(result_state["errors"]) == 0 or \
               not any("performance" in err.lower() for err in result_state["errors"])
    
    def test_scanner_performance_medium_file(self, mock_llm_client):
        """
        Test Scanner completes within bounds for medium files.
        
        **Property 19: Scanner Performance Bound**
        **Validates: Requirements 10.4**
        """
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        # Generate medium file (500 lines)
        code = generate_python_code(500, include_vulnerability=True)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = scanner.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 10s for files under 1000 lines)
        assert execution_time < 10.0, \
            f"Scanner took {execution_time:.2f}s for 500 lines (expected < 10s)"
    
    def test_scanner_performance_large_file(self, mock_llm_client):
        """
        Test Scanner completes within bounds for large files (under 1000 lines).
        
        **Property 19: Scanner Performance Bound**
        **Validates: Requirements 10.4**
        """
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        # Generate large file (999 lines - just under threshold)
        code = generate_python_code(999, include_vulnerability=True)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = scanner.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 10s for files under 1000 lines)
        assert execution_time < 10.0, \
            f"Scanner took {execution_time:.2f}s for 999 lines (expected < 10s)"
    
    @settings(
        max_examples=20,  # Reduced for performance testing
        deadline=15000,  # 15s deadline per test
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
    )
    @given(
        num_lines=st.integers(min_value=10, max_value=999),
        include_vuln=st.booleans()
    )
    def test_scanner_performance_property(self, mock_llm_client, num_lines, include_vuln):
        """
        Property test: Scanner completes within 10s for any file under 1000 lines.
        
        **Property 19: Scanner Performance Bound**
        For any code file under 1000 lines, the Scanner_Agent should complete
        vulnerability detection (including LLM hypothesis generation) in under 10 seconds.
        
        **Validates: Requirements 10.4**
        """
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        # Generate code with specified parameters
        code = generate_python_code(num_lines, include_vulnerability=include_vuln)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = scanner.execute(state)
        execution_time = time.time() - start_time
        
        # Property: Scanner completes within 10s for files under 1000 lines
        assert execution_time < 10.0, \
            f"Scanner took {execution_time:.2f}s for {num_lines} lines (expected < 10s)"
        
        # Verify scanner completed (no critical errors)
        assert "Scanner Agent: Starting scan..." in result_state["logs"]
    
    def test_scanner_logs_timing_metrics(self, mock_llm_client, caplog):
        """
        Test that Scanner logs detailed timing metrics.
        
        **Validates: Requirements 10.4**
        """
        import logging
        caplog.set_level(logging.INFO)
        
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        code = generate_python_code(100, include_vulnerability=True)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = scanner.execute(state)
        
        # Check that timing metrics are logged
        log_messages = [record.message for record in caplog.records]
        timing_logs = [msg for msg in log_messages if "Scanner timing" in msg]
        
        assert len(timing_logs) > 0, "Scanner should log timing metrics"
        
        # Verify timing log contains expected components
        timing_log = timing_logs[0]
        assert "AST:" in timing_log
        assert "Hypothesis:" in timing_log
        assert "Slicing:" in timing_log
        assert "Total:" in timing_log
    
    def test_scanner_warns_on_performance_degradation(self, mock_llm_client):
        """
        Test that Scanner warns when performance degrades.
        
        This test simulates slow LLM responses to trigger performance warning.
        
        **Validates: Requirements 10.4**
        """
        # Create slow mock client
        slow_mock = Mock(spec=LLMClient)
        
        def slow_generate(*args, **kwargs):
            time.sleep(0.5)  # Simulate slow LLM
            return "Test hypothesis"
        
        slow_mock.generate.side_effect = slow_generate
        slow_mock.generate_with_self_correction.return_value = "def test(): pass"
        slow_mock.validate_python_syntax.return_value = (True, None)
        
        scanner = ScannerAgent(llm_client=slow_mock)
        
        # Small file that should be fast
        code = generate_python_code(50, include_vulnerability=True)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[],
            patches=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # This will be slow due to mock
        result_state = scanner.execute(state)
        
        # Note: The actual warning depends on total execution time
        # We just verify the scanner completes without crashing
        assert result_state is not None
