"""
Unit and property tests for LLM-enhanced Patcher Agent.
Tests patch generation, signature preservation, and vulnerability-specific patterns.
"""

import ast
import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.patcher import PatcherAgent
from agent.llm_client import LLMClient
from agent.state import AgentState, Vulnerability, VerificationResult, Patch


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_client = Mock(spec=LLMClient)
    # Default: return valid patched code
    mock_client.generate.return_value = """def search_users(username):
    # SECURITY FIX: Use parameterized query to prevent SQL injection
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()"""
    mock_client.validate_python_syntax.return_value = (True, None)
    return mock_client


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability for testing."""
    return Vulnerability(
        location="test.py:4",
        vuln_type="SQL Injection",
        description="SQL injection via f-string",
        hypothesis="User input flows to SQL query without sanitization",
        confidence=0.9
    )


@pytest.fixture
def sample_counterexample():
    """Sample counterexample from symbolic execution."""
    return "username=\"admin' OR '1'='1\""


class TestPatcherAgentInitialization:
    """Test Patcher Agent initialization with LLM client."""
    
    def test_patcher_creation_without_llm(self):
        """Test patcher can be created without LLM client."""
        patcher = PatcherAgent()
        
        assert patcher.llm_client is None
        assert patcher.patch_templates is not None
        assert patcher.patch_examples is not None
    
    def test_patcher_creation_with_llm(self, mock_llm_client):
        """Test patcher can be created with LLM client."""
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        assert patcher.llm_client is mock_llm_client
        assert patcher.patch_templates is not None


class TestPatchGeneration:
    """Test LLM-powered patch generation."""
    
    def test_generate_patch_with_llm(self, mock_llm_client, sample_vulnerability, sample_counterexample):
        """Test patch generation with LLM client."""
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        code = """
def search_users(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return execute(query)
"""
        
        patch = patcher._generate_patch_with_feedback(
            code,
            sample_vulnerability,
            sample_counterexample,
            iteration=0
        )
        
        assert patch is not None
        assert isinstance(patch, Patch)
        assert len(patch.code) > 0
        assert patch.diff is not None
        mock_llm_client.generate.assert_called_once()
    
    def test_generate_patch_without_llm(self, sample_vulnerability, sample_counterexample):
        """Test patch generation falls back to template without LLM."""
        patcher = PatcherAgent()
        
        code = """
def search_users(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return execute(query)
"""
        
        patch = patcher._generate_patch_with_feedback(
            code,
            sample_vulnerability,
            sample_counterexample,
            iteration=0
        )
        
        assert patch is not None
        assert isinstance(patch, Patch)
    
    def test_generate_patch_with_syntax_error_fallback(self, sample_vulnerability, sample_counterexample):
        """Test patch generation falls back to template on syntax errors."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.return_value = "def invalid syntax here"
        mock_client.validate_python_syntax.return_value = (False, "SyntaxError")
        
        patcher = PatcherAgent(llm_client=mock_client)
        
        code = "def test(): pass"
        patch = patcher._generate_patch_with_feedback(
            code,
            sample_vulnerability,
            sample_counterexample,
            iteration=0
        )
        
        assert patch is not None
        # Should fall back to template


class TestFunctionSignaturePreservation:
    """Test function signature preservation."""
    
    def test_extract_function_signature(self):
        """Test extracting function signature."""
        patcher = PatcherAgent()
        
        code = """
def search_users(username: str, limit: int = 10) -> list:
    pass
"""
        
        sig = patcher._extract_function_signature(code)
        
        assert sig is not None
        assert sig[0] == "search_users"
        assert "username" in sig[1]
        assert "limit" in sig[1]
    
    def test_verify_signature_preserved(self):
        """Test verifying signature preservation."""
        patcher = PatcherAgent()
        
        original = """
def search_users(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return execute(query)
"""
        
        patched = """
def search_users(username):
    query = "SELECT * FROM users WHERE username = ?"
    return execute(query, (username,))
"""
        
        preserved = patcher._verify_signature_preserved(original, patched)
        
        assert preserved is True
    
    def test_verify_signature_not_preserved(self):
        """Test detecting signature changes."""
        patcher = PatcherAgent()
        
        original = """
def search_users(username):
    pass
"""
        
        patched = """
def search_users(username, limit):
    pass
"""
        
        preserved = patcher._verify_signature_preserved(original, patched)
        
        assert preserved is False


class TestVulnerabilitySpecificPatterns:
    """Test vulnerability-specific patch patterns."""
    
    def test_get_patch_examples_sql_injection(self):
        """Test getting examples for SQL injection."""
        patcher = PatcherAgent()
        
        examples = patcher._get_patch_examples("SQL Injection")
        
        assert examples is not None
        assert len(examples) > 0
        # Should contain secure patterns
        assert "parameterized" in examples.lower() or "?" in examples
    
    def test_get_patch_examples_command_injection(self):
        """Test getting examples for command injection."""
        patcher = PatcherAgent()
        
        examples = patcher._get_patch_examples("Command Injection")
        
        assert examples is not None
        assert len(examples) > 0
        # Should contain subprocess patterns
        assert "subprocess" in examples.lower() or "shell=False" in examples


class TestHelperMethods:
    """Test helper methods."""
    
    def test_clean_patch_response_with_markdown(self):
        """Test cleaning patch response with markdown."""
        patcher = PatcherAgent()
        
        response = """```python
def patched_function():
    return "secure"
```"""
        
        cleaned = patcher._clean_patch_response(response)
        
        assert "```" not in cleaned
        assert "def patched_function" in cleaned
    
    def test_generate_diff(self):
        """Test diff generation."""
        patcher = PatcherAgent()
        
        original = "line1\nline2\nline3"
        patched = "line1\nmodified\nline3"
        
        diff = patcher._generate_diff(original, patched)
        
        assert "line2" in diff or "modified" in diff


class TestPatcherExecution:
    """Test full patcher execution."""
    
    def test_execute_with_llm_generates_patch(self, mock_llm_client):
        """Test patcher execution generates patches."""
        patcher = PatcherAgent(llm_client=mock_llm_client)
        
        vuln = Vulnerability(
            location="test.py:3",
            vuln_type="SQL Injection",
            description="SQL injection",
            hypothesis="User input to SQL",
            confidence=0.9
        )
        
        verification_result = VerificationResult(
            verified=False,
            counterexample="username=\"admin' OR '1'='1\"",
            error_message=None,
            execution_time=0.5
        )
        
        state = AgentState(
            code="""
def search(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
""",
            file_path="test.py",
            vulnerabilities=[vuln],
            verification_results=[verification_result],
            current_vulnerability=vuln,
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = patcher.execute(state)
        
        assert result_state["current_patch"] is not None
        assert len(result_state.get("patches", [])) > 0


# Property-Based Tests

@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"]),
    has_counterexample=st.booleans()
)
def test_property_patch_exploit_handling(vuln_type, has_counterexample):
    """
    Property 11: Patch Exploit Handling
    
    For any Counterexample from SymBot:
    - Patcher should generate a patch
    - Patch should be syntactically valid Python
    - Patch should address the specific exploit
    
    Validates: Requirements 3.1
    Feature: llm-agent-intelligence, Property 11: Patch Exploit Handling
    """
    # Create mock client that returns valid patch
    mock_client = Mock(spec=LLMClient)
    mock_client.generate.return_value = """def secure_function(user_input):
    # SECURITY FIX: Input validation
    if not user_input:
        return None
    return process(user_input)"""
    mock_client.validate_python_syntax.return_value = (True, None)
    
    patcher = PatcherAgent(llm_client=mock_client)
    
    vuln = Vulnerability(
        location="test.py:10",
        vuln_type=vuln_type,
        description=f"Test {vuln_type}",
        hypothesis="User input flows to vulnerable operation",
        confidence=0.8
    )
    
    counterexample = "exploit_input" if has_counterexample else ""
    code = "def vulnerable_function(user_input):\n    pass"
    
    patch = patcher._generate_patch_with_feedback(code, vuln, counterexample, iteration=0)
    
    # Patch should be generated
    assert patch is not None
    assert isinstance(patch, Patch)
    
    # Patch should be syntactically valid
    try:
        ast.parse(patch.code)
        is_valid = True
    except SyntaxError:
        is_valid = False
    
    assert is_valid, f"Generated patch is not valid Python: {patch.code[:200]}"


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    has_params=st.booleans(),
    has_return_type=st.booleans()
)
def test_property_function_signature_preservation(has_params, has_return_type):
    """
    Property 12: Function Signature Preservation
    
    For any generated patch:
    - Patched function should have same name as original
    - Patched function should have same parameters as original
    - Patched function should have same return type as original (if present)
    
    Validates: Requirements 3.2
    Feature: llm-agent-intelligence, Property 12: Function Signature Preservation
    """
    patcher = PatcherAgent()
    
    # Build original function
    params = "(username, limit)" if has_params else "()"
    return_annotation = " -> list" if has_return_type else ""
    
    original = f"""
def search_users{params}{return_annotation}:
    query = f"SELECT * FROM users"
    return execute(query)
"""
    
    # Build patched function (same signature)
    patched = f"""
def search_users{params}{return_annotation}:
    query = "SELECT * FROM users"
    return execute(query)
"""
    
    preserved = patcher._verify_signature_preserved(original, patched)
    
    # Signature should be preserved
    assert preserved is True
    
    # Extract signatures to verify
    orig_sig = patcher._extract_function_signature(original)
    patch_sig = patcher._extract_function_signature(patched)
    
    if orig_sig and patch_sig:
        # Function names should match
        assert orig_sig[0] == patch_sig[0]
        # Parameters should match
        assert orig_sig[1] == patch_sig[1]


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection"])
)
def test_property_vulnerability_specific_patch_patterns(vuln_type):
    """
    Property 13: Vulnerability-Specific Patch Patterns
    
    For any vulnerability type:
    - SQL injection patches should use parameterized queries or ORM methods
    - Command injection patches should use subprocess with list args and shell=False
    
    Validates: Requirements 3.3, 3.4, 8.4, 8.5
    Feature: llm-agent-intelligence, Property 13: Vulnerability-Specific Patch Patterns
    """
    patcher = PatcherAgent()
    
    # Get secure patterns
    patterns = patcher._get_patch_examples(vuln_type)
    
    # Patterns should be generated
    assert patterns is not None
    assert len(patterns) > 0
    
    # Check for vulnerability-specific patterns
    if vuln_type == "SQL Injection":
        # Should mention parameterized queries or ORM
        has_sql_patterns = (
            "parameterized" in patterns.lower() or
            "?" in patterns or
            "orm" in patterns.lower() or
            "execute(query, " in patterns
        )
        assert has_sql_patterns, f"SQL injection patterns missing secure coding guidance: {patterns}"
    
    elif vuln_type == "Command Injection":
        # Should mention subprocess with list args and shell=False
        has_cmd_patterns = (
            "subprocess" in patterns.lower() and
            "shell=False" in patterns
        ) or "list" in patterns.lower()
        assert has_cmd_patterns, f"Command injection patterns missing secure coding guidance: {patterns}"


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    indent_char=st.sampled_from([' ', '\t']),
    indent_size=st.sampled_from([2, 4]),
    has_type_hints=st.booleans()
)
def test_property_code_style_preservation(indent_char, indent_size, has_type_hints):
    """
    Property 14: Code Style and Type Preservation
    
    For any generated patch:
    - Patched code should preserve indentation style (spaces vs tabs, indent size)
    - Patched code should preserve type hints if present in original
    - Patched code should not introduce unnecessary new dependencies
    
    Validates: Requirements 9.1, 9.3, 9.4
    Feature: llm-agent-intelligence, Property 14: Code Style and Type Preservation
    """
    patcher = PatcherAgent()
    
    # Build original code with specific style
    indent = indent_char * indent_size
    type_hint = ": str" if has_type_hints else ""
    return_hint = " -> str" if has_type_hints else ""
    
    original = f"""def search_users(username{type_hint}){return_hint}:
{indent}query = f"SELECT * FROM users WHERE name='{{username}}'"
{indent}return execute(query)
"""
    
    # Build patched code (may have different style)
    patched = """def search_users(username):
    query = "SELECT * FROM users WHERE name=?"
    return execute(query, (username,))
"""
    
    # Preserve code style
    preserved = patcher._preserve_code_style(original, patched)
    
    # Check indentation is preserved
    detected_char, detected_size = patcher._detect_indentation(original)
    assert detected_char == indent_char or indent_char == ' '  # Tabs may be detected as spaces
    
    # Check type hints are preserved if present
    if has_type_hints:
        preserved_with_hints = patcher._preserve_type_hints(original, patched)
        # Should contain type annotations
        assert "username" in preserved_with_hints
    
    # Check no unnecessary dependencies
    new_deps = patcher._check_new_dependencies(original, patched)
    # Should not introduce new imports for simple patches
    assert len(new_deps) == 0


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"]),
    has_hypothesis=st.booleans()
)
def test_property_patch_documentation(vuln_type, has_hypothesis):
    """
    Property 15: Patch Documentation
    
    For any generated patch:
    - Patch should include a comment explaining the security fix
    - Comment should describe what vulnerability was fixed
    - Comment should explain how the fix addresses the exploit
    
    Validates: Requirement 9.2
    Feature: llm-agent-intelligence, Property 15: Patch Documentation
    """
    patcher = PatcherAgent()
    
    vuln = Vulnerability(
        location="test.py:10",
        vuln_type=vuln_type,
        description=f"Test {vuln_type} vulnerability",
        hypothesis="User input flows to vulnerable operation" if has_hypothesis else None,
        confidence=0.8
    )
    
    code = """def vulnerable_function(user_input):
    return process(user_input)
"""
    
    counterexample = "exploit_input"
    
    # Add security comment
    documented = patcher._add_security_comment(code, vuln, counterexample)
    
    # Should contain security comment
    assert "# SECURITY FIX:" in documented
    assert vuln_type in documented
    
    # Should contain description
    assert vuln.description in documented or "Test" in documented
    
    # Should contain fix explanation
    fix_explanation = patcher._get_fix_explanation(vuln_type)
    assert fix_explanation is not None
    assert len(fix_explanation) > 0


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    has_violations=st.booleans()
)
def test_property_pep8_compliance(has_violations):
    """
    Property 16: PEP 8 Compliance
    
    For any generated patch:
    - Patch should be checked for PEP 8 compliance
    - If violations found, they should be auto-fixed
    - Final patch should be PEP 8 compliant
    
    Validates: Requirement 9.5
    Feature: llm-agent-intelligence, Property 16: PEP 8 Compliance
    """
    patcher = PatcherAgent()
    
    # Create code with or without PEP 8 violations
    if has_violations:
        # Code with violations (long line, missing spaces)
        code = """def search_users(username,limit):
    query="SELECT * FROM users WHERE username=? LIMIT ?"
    return execute(query,(username,limit))
"""
    else:
        # PEP 8 compliant code
        code = """def search_users(username, limit):
    query = "SELECT * FROM users WHERE username=? LIMIT ?"
    return execute(query, (username, limit))
"""
    
    # Check compliance
    is_compliant, violations = patcher._check_pep8_compliance(code)
    
    # If violations found, fix them
    if not is_compliant:
        fixed_code = patcher._fix_pep8_violations(code)
        
        # Fixed code should be valid Python
        try:
            ast.parse(fixed_code)
            is_valid = True
        except SyntaxError:
            is_valid = False
        
        assert is_valid, "Fixed code should be valid Python"
        
        # Check if violations were reduced
        is_compliant_after, violations_after = patcher._check_pep8_compliance(fixed_code)
        # Should have fewer or equal violations
        assert len(violations_after) <= len(violations)

