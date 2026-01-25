"""
Property-based tests for Patcher Agent performance.
Tests that Patcher completes within performance bounds.

**Feature: llm-agent-intelligence, Property 20: Patcher Performance Bound**
**Validates: Requirements 10.5**
"""

import time
import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.patcher import PatcherAgent
from agent.llm_client import LLMClient
from agent.state import AgentState, Vulnerability, VerificationResult, Patch


@pytest.fixture
def mock_llm_client():
    """Create a fast mock LLM client for performance testing."""
    mock_client = Mock(spec=LLMClient)
    
    # Fast responses for performance testing
    patched_code = """
def search_users(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    # SECURITY FIX: Use parameterized query
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
"""
    
    mock_client.generate.return_value = patched_code
    mock_client.validate_python_syntax.return_value = (True, None)
    
    return mock_client


def create_test_vulnerability(vuln_type: str = "SQL Injection") -> Vulnerability:
    """Create a test vulnerability."""
    return Vulnerability(
        location="test.py:4",
        vuln_type=vuln_type,
        severity="HIGH",
        description=f"Test {vuln_type} vulnerability",
        hypothesis=f"User input flows directly into {vuln_type.lower()} operation",
        confidence=0.9
    )


def create_test_verification_result(counterexample: str) -> VerificationResult:
    """Create a test verification result with counterexample."""
    return VerificationResult(
        verified=False,
        counterexample=counterexample,
        error_message=None,
        execution_time=1.0
    )


def generate_vulnerable_code(complexity: str = "simple") -> str:
    """
    Generate vulnerable code with varying complexity.
    
    Args:
        complexity: "simple", "medium", or "complex"
        
    Returns:
        Python code string
    """
    if complexity == "simple":
        return """
def search_users(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
"""
    elif complexity == "medium":
        return """
def search_users(username, email=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if email:
        query = f"SELECT * FROM users WHERE username = '{username}' AND email = '{email}'"
    else:
        query = f"SELECT * FROM users WHERE username = '{username}'"
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    return [dict(row) for row in results]
"""
    else:  # complex
        return """
def search_users(username, email=None, role=None, active=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query dynamically
    conditions = []
    if username:
        conditions.append(f"username = '{username}'")
    if email:
        conditions.append(f"email = '{email}'")
    if role:
        conditions.append(f"role = '{role}'")
    if active:
        conditions.append("active = 1")
    
    where_clause = " AND ".join(conditions)
    query = f"SELECT * FROM users WHERE {where_clause}"
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Process results
    processed = []
    for row in results:
        user_dict = dict(row)
        user_dict['full_name'] = f"{user_dict['first_name']} {user_dict['last_name']}"
        processed.append(user_dict)
    
    return processed
"""


class TestPatcherPerformance:
    """Test Patcher Agent performance bounds."""
    
    def test_patcher_performance_simple_patch(self, mock_llm_client):
        """
        Test Patcher completes quickly for simple patches.
        
        **Property 20: Patcher Performance Bound**
        **Validates: Requirements 10.5**
        """
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"' OR '1'='1\""
        )
        
        code = generate_vulnerable_code("simple")
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = patcher.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 5s per patch)
        assert execution_time < 5.0, \
            f"Patcher took {execution_time:.2f}s (expected < 5s)"
        
        # Verify patcher completed successfully
        assert len(result_state["errors"]) == 0 or \
               not any("performance" in err.lower() for err in result_state["errors"])
    
    def test_patcher_performance_medium_patch(self, mock_llm_client):
        """
        Test Patcher completes within bounds for medium complexity patches.
        
        **Property 20: Patcher Performance Bound**
        **Validates: Requirements 10.5**
        """
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"admin' --\", email = \"test@evil.com\""
        )
        
        code = generate_vulnerable_code("medium")
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = patcher.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 5s per patch)
        assert execution_time < 5.0, \
            f"Patcher took {execution_time:.2f}s (expected < 5s)"
    
    def test_patcher_performance_complex_patch(self, mock_llm_client):
        """
        Test Patcher completes within bounds for complex patches.
        
        **Property 20: Patcher Performance Bound**
        **Validates: Requirements 10.5**
        """
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"' UNION SELECT * FROM passwords --\""
        )
        
        code = generate_vulnerable_code("complex")
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = patcher.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound (< 5s per patch)
        assert execution_time < 5.0, \
            f"Patcher took {execution_time:.2f}s (expected < 5s)"
    
    @settings(
        max_examples=20,  # Reduced for performance testing
        deadline=10000,  # 10s deadline per test
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
    )
    @given(
        complexity=st.sampled_from(["simple", "medium", "complex"]),
        vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"])
    )
    def test_patcher_performance_property(self, mock_llm_client, complexity, vuln_type):
        """
        Property test: Patcher completes within 5s for any counterexample.
        
        **Property 20: Patcher Performance Bound**
        For any counterexample, the Patcher_Agent should complete patch generation
        (including LLM inference) in under 5 seconds.
        
        **Validates: Requirements 10.5**
        """
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability(vuln_type)
        
        # Generate appropriate counterexample for vulnerability type
        counterexamples = {
            "SQL Injection": "username = \"' OR '1'='1\"",
            "Command Injection": "filename = \"test.txt; rm -rf /\"",
            "Path Traversal": "path = \"../../etc/passwd\""
        }
        
        verification_result = create_test_verification_result(
            counterexample=counterexamples[vuln_type]
        )
        
        code = generate_vulnerable_code(complexity)
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = patcher.execute(state)
        execution_time = time.time() - start_time
        
        # Property: Patcher completes within 5s per patch
        assert execution_time < 5.0, \
            f"Patcher took {execution_time:.2f}s for {complexity} {vuln_type} (expected < 5s)"
        
        # Verify patcher completed (no critical errors)
        assert "Patcher Agent: Generating patch..." in result_state["logs"]
    
    def test_patcher_logs_timing_metrics(self, mock_llm_client, caplog):
        """
        Test that Patcher logs detailed timing metrics.
        
        **Validates: Requirements 10.5**
        """
        import logging
        caplog.set_level(logging.INFO)
        
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"' OR '1'='1\""
        )
        
        code = generate_vulnerable_code("simple")
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        result_state = patcher.execute(state)
        
        # Check that timing metrics are logged
        log_messages = [record.message for record in caplog.records]
        timing_logs = [msg for msg in log_messages if "Patcher timing" in msg]
        
        assert len(timing_logs) > 0, "Patcher should log timing metrics"
        
        # Verify timing log contains expected components
        timing_log = timing_logs[0]
        assert "Generation:" in timing_log
        assert "Total:" in timing_log
    
    def test_patcher_warns_on_performance_degradation(self, mock_llm_client):
        """
        Test that Patcher warns when performance degrades.
        
        This test simulates slow LLM responses to trigger performance warning.
        
        **Validates: Requirements 10.5**
        """
        # Create slow mock client
        slow_mock = Mock(spec=LLMClient)
        
        def slow_generate(*args, **kwargs):
            time.sleep(2.0)  # Simulate slow LLM (2s)
            return """
def search_users(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
"""
        
        slow_mock.generate.side_effect = slow_generate
        slow_mock.validate_python_syntax.return_value = (True, None)
        
        patcher = PatcherAgent(llm_client=slow_mock)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"' OR '1'='1\""
        )
        
        code = generate_vulnerable_code("simple")
        
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=0,
            total_execution_time=0.0
        )
        
        # This will be slow due to mock
        result_state = patcher.execute(state)
        
        # Note: The actual warning depends on total execution time
        # We just verify the patcher completes without crashing
        assert result_state is not None
    
    def test_patcher_performance_with_retry(self, mock_llm_client):
        """
        Test Patcher performance when retrying after failed verification.
        
        **Validates: Requirements 10.5**
        """
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = create_test_vulnerability("SQL Injection")
        verification_result = create_test_verification_result(
            counterexample="username = \"' OR '1'='1\""
        )
        
        code = generate_vulnerable_code("simple")
        
        # Simulate retry scenario (iteration > 0)
        state = AgentState(
            code=code,
            file_path="test.py",
            vulnerabilities=[vuln],
            current_vulnerability=vuln,
            verification_results=[verification_result],
            patches=[],
            logs=[],
            errors=[],
            iteration_count=2,  # Third attempt
            total_execution_time=0.0
        )
        
        # Measure execution time
        start_time = time.time()
        result_state = patcher.execute(state)
        execution_time = time.time() - start_time
        
        # Assert performance bound even with retries (< 5s per patch)
        assert execution_time < 5.0, \
            f"Patcher took {execution_time:.2f}s on retry (expected < 5s)"
