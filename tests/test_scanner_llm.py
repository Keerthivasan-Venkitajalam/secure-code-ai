"""
Unit and property tests for LLM-enhanced Scanner Agent.
Tests hypothesis generation and false positive reduction.
"""

import ast
import pytest
from unittest.mock import Mock, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.scanner import ScannerAgent
from agent.llm_client import LLMClient
from agent.state import AgentState, Vulnerability


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_client = Mock(spec=LLMClient)
    hypothesis_response = """**Security Property:** Input validation
**Attack Vector:** SQL injection via string concatenation
**Data Flow:** user_input → query string → execute()
**Impact:** Unauthorized database access"""
    
    # Mock both generate and generate_with_self_correction
    mock_client.generate.return_value = hypothesis_response
    mock_client.generate_with_self_correction.return_value = """def search_users(username):
    # Mock database connection
    def get_db_connection():
        return MockConnection()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()"""
    
    mock_client.validate_python_syntax.return_value = (True, None)
    return mock_client


@pytest.fixture
def sample_vulnerable_code():
    """Sample vulnerable code for testing."""
    return """
def search_users(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
"""


class TestScannerAgentInitialization:
    """Test Scanner Agent initialization with LLM client."""
    
    def test_scanner_creation_without_llm(self):
        """Test scanner can be created without LLM client."""
        scanner = ScannerAgent()
        
        assert scanner.llm_client is None
        assert scanner.dangerous_patterns is not None
    
    def test_scanner_creation_with_llm(self, mock_llm_client):
        """Test scanner can be created with LLM client."""
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        assert scanner.llm_client is mock_llm_client
        assert scanner.dangerous_patterns is not None


class TestHypothesisGeneration:
    """Test LLM-powered hypothesis generation."""
    
    def test_generate_hypothesis_with_llm(self, mock_llm_client, sample_vulnerable_code):
        """Test hypothesis generation with LLM client."""
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        vuln = Vulnerability(
            location="test.py:4",
            vuln_type="SQL Injection",
            description="Test vulnerability"
        )
        
        hypothesis = scanner._generate_hypothesis(vuln, sample_vulnerable_code)
        
        assert hypothesis is not None
        assert len(hypothesis) > 0
        assert "Security Property" in hypothesis or "Attack Vector" in hypothesis
        mock_llm_client.generate.assert_called_once()
    
    def test_generate_hypothesis_without_llm(self, sample_vulnerable_code):
        """Test hypothesis generation falls back without LLM."""
        scanner = ScannerAgent()
        
        vuln = Vulnerability(
            location="test.py:4",
            vuln_type="SQL Injection",
            description="Test vulnerability"
        )
        
        hypothesis = scanner._generate_hypothesis(vuln, sample_vulnerable_code)
        
        assert hypothesis == vuln.description
    
    def test_generate_hypothesis_handles_errors(self, sample_vulnerable_code):
        """Test hypothesis generation handles LLM errors gracefully."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.side_effect = Exception("LLM error")
        
        scanner = ScannerAgent(llm_client=mock_client)
        
        vuln = Vulnerability(
            location="test.py:4",
            vuln_type="SQL Injection",
            description="Test vulnerability"
        )
        
        hypothesis = scanner._generate_hypothesis(vuln, sample_vulnerable_code)
        
        # Should fall back to description
        assert hypothesis == vuln.description


class TestContextAssessment:
    """Test contextual false positive reduction."""
    
    def test_assess_context_true_positive(self, sample_vulnerable_code):
        """Test context assessment identifies true positives."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.return_value = "TRUE_POSITIVE: 0.9"
        
        scanner = ScannerAgent(llm_client=mock_client)
        
        vuln = Vulnerability(
            location="test.py:4",
            vuln_type="SQL Injection",
            confidence=0.7
        )
        
        adjusted_confidence = scanner._assess_context(vuln, sample_vulnerable_code)
        
        # Should maintain or increase confidence
        assert adjusted_confidence >= 0.7
    
    def test_assess_context_false_positive(self):
        """Test context assessment reduces confidence for false positives."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.return_value = "FALSE_POSITIVE: 0.2"
        
        scanner = ScannerAgent(llm_client=mock_client)
        
        # Safe eval with hardcoded string
        safe_code = """
def calculate():
    result = eval("2 + 2")
    return result
"""
        
        vuln = Vulnerability(
            location="test.py:2",
            vuln_type="Code Injection",
            confidence=0.9
        )
        
        adjusted_confidence = scanner._assess_context(vuln, safe_code)
        
        # Should reduce confidence significantly
        assert adjusted_confidence < 0.5
    
    def test_assess_context_without_llm(self, sample_vulnerable_code):
        """Test context assessment without LLM returns original confidence."""
        scanner = ScannerAgent()
        
        vuln = Vulnerability(
            location="test.py:4",
            vuln_type="SQL Injection",
            confidence=0.7
        )
        
        adjusted_confidence = scanner._assess_context(vuln, sample_vulnerable_code)
        
        assert adjusted_confidence == 0.7


class TestHelperMethods:
    """Test helper methods."""
    
    def test_extract_function_at_line(self):
        """Test extracting function containing a line."""
        scanner = ScannerAgent()
        
        code = """
def foo():
    print("line 2")
    print("line 3")
    return True

def bar():
    pass
"""
        
        func_name, func_code = scanner._extract_function_at_line(code, 3)
        
        assert func_name == "foo"
        assert "def foo" in func_code
        assert "line 3" in func_code
    
    def test_extract_context(self):
        """Test extracting code context around a line."""
        scanner = ScannerAgent()
        
        code = """line 1
line 2
line 3
line 4
line 5"""
        
        context = scanner._extract_context(code, 3, context_lines=1)
        
        assert "line 2" in context
        assert "line 3" in context
        assert "line 4" in context
        assert ">>>" in context  # Marker for target line
    
    def test_get_line_number(self):
        """Test extracting line number from location."""
        scanner = ScannerAgent()
        
        assert scanner._get_line_number("test.py:42") == 42
        assert scanner._get_line_number("file.py:1") == 1
        assert scanner._get_line_number("invalid") == 1  # Fallback


class TestScannerExecution:
    """Test full scanner execution with LLM."""
    
    def test_execute_with_llm_generates_hypotheses(self, mock_llm_client):
        """Test scanner execution generates hypotheses for vulnerabilities."""
        scanner = ScannerAgent(llm_client=mock_llm_client)
        
        # Code with eval - easier to detect with AST
        vuln_code = """
def calculate(user_expr):
    result = eval(user_expr)
    return result
"""
        
        state = AgentState(
            code=vuln_code,
            file_path="test.py",
            vulnerabilities=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = scanner.execute(state)
        
        assert len(result_state["vulnerabilities"]) > 0, "Scanner should detect eval() vulnerability"
        # Check that hypotheses were generated
        for vuln in result_state["vulnerabilities"]:
            assert vuln.hypothesis is not None
            assert len(vuln.hypothesis) > 0
    
    def test_execute_without_llm_works(self):
        """Test scanner execution works without LLM client."""
        scanner = ScannerAgent()
        
        # Code with eval (easy to detect)
        vuln_code = """
def calculate(expr):
    result = eval(expr)
    return result
"""
        
        state = AgentState(
            code=vuln_code,
            file_path="test.py",
            vulnerabilities=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = scanner.execute(state)
        
        assert len(result_state["vulnerabilities"]) > 0
        assert "Scanner Agent" in result_state["logs"][0]


# Property-Based Tests

@settings(
    max_examples=10,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"]),
    line_num=st.integers(min_value=1, max_value=100)
)
def test_property_hypothesis_generation_completeness(vuln_type, line_num):
    """
    Property 1: Hypothesis Generation Completeness
    
    For any detected vulnerability pattern:
    - Scanner should generate a Vulnerability_Hypothesis
    - Hypothesis should contain vulnerability_type, location, confidence_score
    - Hypothesis should have natural language explanation
    
    Validates: Requirements 1.1, 1.3
    Feature: llm-agent-intelligence, Property 1: Hypothesis Generation Completeness
    """
    # Create mock client inside test to avoid fixture issues
    mock_client = Mock(spec=LLMClient)
    mock_client.generate.return_value = """**Security Property:** Input validation
**Attack Vector:** SQL injection
**Data Flow:** user_input → query
**Impact:** Data breach"""
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    code = f"""
def vulnerable_function(user_input):
    # Line {line_num}
    result = execute(f"SELECT * FROM users WHERE id={{user_input}}")
    return result
"""
    
    vuln = Vulnerability(
        location=f"test.py:{line_num}",
        vuln_type=vuln_type,
        description="Test vulnerability",
        confidence=0.7
    )
    
    hypothesis = scanner._generate_hypothesis(vuln, code)
    
    # Hypothesis should be generated
    assert hypothesis is not None
    assert isinstance(hypothesis, str)
    assert len(hypothesis) > 0
    
    # Should contain meaningful content (not just the description)
    if mock_client.generate.called:
        assert len(hypothesis) > len(vuln.description)


@settings(
    max_examples=10,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    initial_confidence=st.floats(min_value=0.5, max_value=1.0)
)
def test_property_false_positive_reduction(initial_confidence):
    """
    Property 2: False Positive Reduction
    
    For any code containing dangerous functions in safe contexts:
    - Scanner should use LLM contextual analysis
    - Confidence should be reduced for false positives (< 0.5)
    - True positives should maintain confidence
    
    Validates: Requirements 1.2
    Feature: llm-agent-intelligence, Property 2: False Positive Reduction
    """
    # Mock LLM to return false positive assessment
    mock_client = Mock(spec=LLMClient)
    mock_client.generate.return_value = "FALSE_POSITIVE: 0.2"
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Safe code: eval with hardcoded string
    safe_code = """
def calculate_constant():
    result = eval("2 + 2")
    return result
"""
    
    vuln = Vulnerability(
        location="test.py:2",
        vuln_type="Code Injection",
        confidence=initial_confidence
    )
    
    adjusted_confidence = scanner._assess_context(vuln, safe_code)
    
    # Confidence should be reduced for false positives
    assert adjusted_confidence < 0.5
    assert adjusted_confidence < initial_confidence


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"]),
    line_num=st.integers(min_value=1, max_value=50)
)
def test_property_code_slice_validity(vuln_type, line_num):
    """
    Property 3: Code Slice Validity
    
    For any generated Code_Slice:
    - The slice should be syntactically valid Python code
    - It should be parseable by ast.parse() without errors
    
    Validates: Requirements 4.3
    Feature: llm-agent-intelligence, Property 3: Code Slice Validity
    """
    # Create mock client that returns valid Python code
    mock_client = Mock(spec=LLMClient)
    
    # Generate a valid code slice
    valid_slice = f"""import sqlite3
from unittest.mock import Mock

def get_db_connection():
    mock_conn = Mock()
    return mock_conn

def vulnerable_function(user_input):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id={{user_input}}"
    cursor.execute(query)
    return cursor.fetchall()
"""
    
    mock_client.generate.return_value = valid_slice
    mock_client.generate_with_self_correction.return_value = valid_slice
    mock_client.validate_python_syntax.return_value = (True, None)
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    code = f"""
def vulnerable_function(user_input):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id={{user_input}}"
    cursor.execute(query)
    return cursor.fetchall()
"""
    
    vuln = Vulnerability(
        location=f"test.py:{line_num}",
        vuln_type=vuln_type,
        description="Test vulnerability",
        hypothesis="User input flows to SQL query"
    )
    
    slice_code = scanner._extract_code_slice(code, vuln)
    
    # Slice should be generated
    assert slice_code is not None
    assert isinstance(slice_code, str)
    assert len(slice_code) > 0
    
    # Slice should be syntactically valid
    try:
        ast.parse(slice_code)
        is_valid = True
    except SyntaxError:
        is_valid = False
    
    assert is_valid, f"Generated slice is not valid Python: {slice_code[:200]}"


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection"]),
    has_imports=st.booleans()
)
def test_property_code_slice_completeness(vuln_type, has_imports):
    """
    Property 4: Code Slice Completeness
    
    For any vulnerability:
    - Generated Code_Slice should include all functions in data flow path
    - Should include all variables from user input to vulnerable operation
    - Should include necessary imports
    
    Validates: Requirements 4.1, 4.2
    Feature: llm-agent-intelligence, Property 4: Code Slice Completeness
    """
    # Create mock client that returns complete slice
    mock_client = Mock(spec=LLMClient)
    
    # Complete slice with imports, mocks, and vulnerable function
    complete_slice = """import subprocess
from unittest.mock import Mock

def process_file(filename):
    result = subprocess.call(f"cat {filename}", shell=True)
    return result
"""
    
    mock_client.generate.return_value = complete_slice
    mock_client.generate_with_self_correction.return_value = complete_slice
    mock_client.validate_python_syntax.return_value = (True, None)
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    code = """import subprocess

def process_file(filename):
    result = subprocess.call(f"cat {filename}", shell=True)
    return result
"""
    
    vuln = Vulnerability(
        location="test.py:4",
        vuln_type=vuln_type,
        description="Command injection",
        hypothesis="User input flows to shell command"
    )
    
    slice_code = scanner._extract_code_slice(code, vuln)
    
    # Slice should be generated
    assert slice_code is not None
    
    # Slice should include the vulnerable function
    assert "def " in slice_code or "process_file" in slice_code or "vulnerable" in slice_code
    
    # If original had imports, slice should too (or mocks)
    if has_imports:
        # Should have imports or mocks
        assert "import" in slice_code or "Mock" in slice_code


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    has_db=st.booleans(),
    has_network=st.booleans()
)
def test_property_mock_generation(has_db, has_network):
    """
    Property 5: Mock Generation
    
    For any Code_Slice containing external dependencies:
    - Slice should include mock objects for database connections
    - Slice should include mock objects for network calls
    - Slice should include mock objects for file I/O
    - Mocks should allow independent execution
    
    Validates: Requirements 4.4
    Feature: llm-agent-intelligence, Property 5: Mock Generation
    """
    # Create mock client that returns slice with mocks
    mock_client = Mock(spec=LLMClient)
    
    # Slice with mocks for external dependencies
    slice_with_mocks = """import sqlite3
from unittest.mock import Mock

def get_db_connection():
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn

def vulnerable_function(user_input):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id={user_input}"
    cursor.execute(query)
    return cursor.fetchall()
"""
    
    mock_client.generate.return_value = slice_with_mocks
    mock_client.generate_with_self_correction.return_value = slice_with_mocks
    mock_client.validate_python_syntax.return_value = (True, None)
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Code with external dependencies
    code = """import sqlite3

def get_db_connection():
    return sqlite3.connect('database.db')

def vulnerable_function(user_input):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id={user_input}"
    cursor.execute(query)
    return cursor.fetchall()
"""
    
    vuln = Vulnerability(
        location="test.py:8",
        vuln_type="SQL Injection",
        description="SQL injection via f-string",
        hypothesis="User input flows to SQL query"
    )
    
    slice_code = scanner._extract_code_slice(code, vuln)
    
    # Slice should be generated
    assert slice_code is not None
    
    # Slice should include mocks for external dependencies
    # Check for Mock usage
    assert "Mock" in slice_code or "mock" in slice_code.lower()
    
    # Should be executable (syntactically valid)
    try:
        ast.parse(slice_code)
        is_valid = True
    except:
        is_valid = False
    
    assert is_valid


@settings(
    max_examples=5,  # Fewer examples for performance test
    deadline=15000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    code_size=st.integers(min_value=10, max_value=100)
)
def test_property_slicing_performance_improvement(code_size):
    """
    Property 6: Slicing Performance Improvement
    
    For any vulnerability:
    - Code slice should be significantly smaller than full code
    - Slice should reduce complexity for symbolic execution
    - Slice extraction should complete in reasonable time
    
    Note: This test validates slice size reduction, not actual symbolic execution time
    
    Validates: Requirements 4.5
    Feature: llm-agent-intelligence, Property 6: Slicing Performance Improvement
    """
    # Create mock client that returns smaller slice
    mock_client = Mock(spec=LLMClient)
    
    # Small slice (much smaller than original)
    small_slice = """from unittest.mock import Mock

def vulnerable_function(user_input):
    result = eval(user_input)
    return result
"""
    
    mock_client.generate.return_value = small_slice
    mock_client.generate_with_self_correction.return_value = small_slice
    mock_client.validate_python_syntax.return_value = (True, None)
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Generate large code with many functions
    large_code_lines = [f"def function_{i}():\n    pass\n" for i in range(code_size)]
    large_code_lines.append("""
def vulnerable_function(user_input):
    result = eval(user_input)
    return result
""")
    large_code = "\n".join(large_code_lines)
    
    vuln = Vulnerability(
        location=f"test.py:{code_size * 2 + 2}",
        vuln_type="Code Injection",
        description="eval() usage",
        hypothesis="User input flows to eval()"
    )
    
    import time
    start_time = time.time()
    slice_code = scanner._extract_code_slice(large_code, vuln)
    extraction_time = time.time() - start_time
    
    # Slice should be generated
    assert slice_code is not None
    
    # Slice should be significantly smaller than original
    # (at least 50% smaller for meaningful reduction)
    assert len(slice_code) < len(large_code) * 0.5, \
        f"Slice ({len(slice_code)} chars) not significantly smaller than original ({len(large_code)} chars)"
    
    # Extraction should complete in reasonable time (< 10 seconds)
    assert extraction_time < 10.0, f"Slice extraction took {extraction_time:.2f}s, should be < 10s"


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    has_imports=st.booleans(),
    has_type_hints=st.booleans(),
    has_docstring=st.booleans()
)
def test_property_context_enrichment(has_imports, has_type_hints, has_docstring):
    """
    Property 7: Context Enrichment
    
    For any function analyzed:
    - LLM context should include function's imports
    - LLM context should include type hints (if present)
    - LLM context should include called function signatures
    - LLM context should include docstrings (if present)
    - LLM context should include security-relevant comments
    
    Validates: Requirements 6.1, 6.2, 6.5
    Feature: llm-agent-intelligence, Property 7: Context Enrichment
    """
    scanner = ScannerAgent()
    
    # Build code with various elements
    code_parts = []
    
    if has_imports:
        code_parts.append("import sqlite3")
        code_parts.append("from typing import Optional")
    
    code_parts.append("")
    
    # Build function with optional type hints and docstring
    func_lines = []
    if has_type_hints:
        func_lines.append("def vulnerable_function(user_input: str) -> list:")
    else:
        func_lines.append("def vulnerable_function(user_input):")
    
    if has_docstring:
        func_lines.append('    """Search users by username."""')
    
    func_lines.append("    conn = get_db_connection()")
    func_lines.append("    cursor = conn.cursor()")
    func_lines.append("    query = f\"SELECT * FROM users WHERE name='{user_input}'\"")
    func_lines.append("    cursor.execute(query)")
    func_lines.append("    return cursor.fetchall()")
    
    code_parts.extend(func_lines)
    code = "\n".join(code_parts)
    
    # Build context
    context = scanner._build_context(code, line_num=7)
    
    # Context should be generated
    assert context is not None
    assert len(context) > 0
    
    # Check for expected elements
    if has_imports:
        assert "import" in context.lower()
    
    if has_type_hints:
        assert "str" in context or "list" in context
    
    if has_docstring:
        assert "Search users" in context or '"""' in context
    
    # Should include the vulnerable function
    assert "vulnerable_function" in context or "def " in context
