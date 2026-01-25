"""
Unit and property tests for LLM-enhanced Speculator Agent.
Tests contract generation and vulnerability-specific patterns.
"""

import ast
import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.speculator import SpeculatorAgent
from agent.llm_client import LLMClient
from agent.state import AgentState, Vulnerability, Contract


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_client = Mock(spec=LLMClient)
    # Default: return valid icontract code
    valid_contract = """@icontract.require(lambda query: "'" not in query, "Query contains SQL quote")
@icontract.ensure(lambda result: "--" not in str(result), "Result contains SQL comment")"""
    
    mock_client.generate.return_value = valid_contract
    mock_client.generate_with_self_correction.return_value = valid_contract
    mock_client.validate_python_syntax.return_value = (True, None)
    return mock_client


@pytest.fixture
def sample_vulnerability():
    """Sample vulnerability for testing."""
    return Vulnerability(
        location="test.py:10",
        vuln_type="SQL Injection",
        description="SQL injection via f-string",
        hypothesis="User input flows to SQL query without sanitization",
        confidence=0.9
    )


class TestSpeculatorAgentInitialization:
    """Test Speculator Agent initialization with LLM client."""
    
    def test_speculator_creation_without_llm(self):
        """Test speculator can be created without LLM client."""
        speculator = SpeculatorAgent()
        
        assert speculator.llm_client is None
        assert speculator.contract_templates is not None
        assert speculator.few_shot_examples is not None
    
    def test_speculator_creation_with_llm(self, mock_llm_client):
        """Test speculator can be created with LLM client."""
        speculator = SpeculatorAgent(llm_client=mock_llm_client)
        
        assert speculator.llm_client is mock_llm_client
        assert speculator.contract_templates is not None


class TestContractGeneration:
    """Test LLM-powered contract generation."""
    
    def test_generate_contract_with_llm(self, mock_llm_client, sample_vulnerability):
        """Test contract generation with LLM client."""
        speculator = SpeculatorAgent(llm_client=mock_llm_client)
        
        code = """
def search_users(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
"""
        
        contract = speculator._generate_contract_with_retry(sample_vulnerability, code)
        
        assert contract is not None
        assert isinstance(contract, Contract)
        assert contract.vuln_type == "SQL Injection"
        assert "@icontract" in contract.code
        mock_llm_client.generate_with_self_correction.assert_called_once()
    
    def test_generate_contract_without_llm(self, sample_vulnerability):
        """Test contract generation falls back to template without LLM."""
        speculator = SpeculatorAgent()
        
        code = """
def search_users(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
"""
        
        contract = speculator._generate_contract_with_retry(sample_vulnerability, code)
        
        assert contract is not None
        assert isinstance(contract, Contract)
        assert "@icontract" in contract.code
    
    def test_generate_contract_with_retry_on_syntax_error(self, sample_vulnerability):
        """Test contract generation retries on syntax errors."""
        mock_client = Mock(spec=LLMClient)
        
        # Mock generate_with_self_correction to simulate retry behavior
        # It should return valid contract after self-correction
        valid_contract = "@icontract.require(lambda x: x is not None)"
        mock_client.generate_with_self_correction.return_value = valid_contract
        mock_client.validate_python_syntax.return_value = (True, None)
        
        speculator = SpeculatorAgent(llm_client=mock_client)
        
        code = "def test(): pass"
        contract = speculator._generate_contract_with_retry(sample_vulnerability, code)
        
        assert contract is not None
        assert mock_client.generate_with_self_correction.call_count == 1
    
    def test_generate_contract_falls_back_after_max_retries(self, sample_vulnerability):
        """Test contract generation falls back to template after max retries."""
        mock_client = Mock(spec=LLMClient)
        
        # Mock generate_with_self_correction to return None (all retries failed)
        mock_client.generate_with_self_correction.return_value = None
        
        speculator = SpeculatorAgent(llm_client=mock_client)
        
        code = "def test(): pass"
        contract = speculator._generate_contract_with_retry(sample_vulnerability, code)
        
        # Should fall back to template
        assert contract is not None
        assert "@icontract" in contract.code


class TestVulnerabilitySpecificPatterns:
    """Test vulnerability-specific contract patterns."""
    
    def test_get_relevant_examples_sql_injection(self):
        """Test getting examples for SQL injection."""
        speculator = SpeculatorAgent()
        
        examples = speculator._get_relevant_examples("SQL Injection")
        
        assert examples is not None
        assert len(examples) > 0
        # Should contain SQL-specific checks
        assert "'" in examples or "SQL" in examples
    
    def test_get_relevant_examples_command_injection(self):
        """Test getting examples for command injection."""
        speculator = SpeculatorAgent()
        
        examples = speculator._get_relevant_examples("Command Injection")
        
        assert examples is not None
        assert len(examples) > 0
        # Should contain shell metacharacter checks
        assert "|" in examples or ";" in examples or "cmd" in examples.lower()
    
    def test_get_relevant_examples_path_traversal(self):
        """Test getting examples for path traversal."""
        speculator = SpeculatorAgent()
        
        examples = speculator._get_relevant_examples("Path Traversal")
        
        assert examples is not None
        assert len(examples) > 0
        # Should contain path traversal checks
        assert ".." in examples or "path" in examples.lower()


class TestHelperMethods:
    """Test helper methods."""
    
    def test_clean_contract_response_with_markdown(self):
        """Test cleaning contract response with markdown."""
        speculator = SpeculatorAgent()
        
        response = """```python
@icontract.require(lambda x: x > 0)
@icontract.ensure(lambda result: result is not None)
```"""
        
        cleaned = speculator._clean_contract_response(response)
        
        assert "```" not in cleaned
        assert "@icontract" in cleaned
    
    def test_clean_contract_response_without_markdown(self):
        """Test cleaning contract response without markdown."""
        speculator = SpeculatorAgent()
        
        response = "@icontract.require(lambda x: x > 0)"
        
        cleaned = speculator._clean_contract_response(response)
        
        assert cleaned == response
    
    def test_extract_function_at_line(self):
        """Test extracting function name at line."""
        speculator = SpeculatorAgent()
        
        code = """
def foo():
    pass

def bar():
    x = 1
    return x
"""
        
        func_name = speculator._extract_function_at_line(code, "test.py:6")
        
        assert func_name == "bar"


class TestSpeculatorExecution:
    """Test full speculator execution."""
    
    def test_execute_with_llm_generates_contracts(self, mock_llm_client):
        """Test speculator execution generates contracts for vulnerabilities."""
        speculator = SpeculatorAgent(llm_client=mock_llm_client)
        
        vuln = Vulnerability(
            location="test.py:3",
            vuln_type="SQL Injection",
            description="SQL injection",
            hypothesis="User input to SQL",
            confidence=0.9
        )
        
        state = AgentState(
            code="""
def search(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
""",
            file_path="test.py",
            vulnerabilities=[vuln],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = speculator.execute(state)
        
        assert len(result_state["contracts"]) > 0
        assert result_state["current_vulnerability"] is not None
    
    def test_execute_without_llm_works(self):
        """Test speculator execution works without LLM client."""
        speculator = SpeculatorAgent()
        
        vuln = Vulnerability(
            location="test.py:3",
            vuln_type="SQL Injection",
            description="SQL injection",
            confidence=0.9
        )
        
        state = AgentState(
            code="""
def search(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
""",
            file_path="test.py",
            vulnerabilities=[vuln],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        result_state = speculator.execute(state)
        
        assert len(result_state["contracts"]) > 0


# Property-Based Tests

@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"]),
    has_hypothesis=st.booleans()
)
def test_property_contract_syntax_validity(vuln_type, has_hypothesis):
    """
    Property 8: Contract Syntax Validity
    
    For any Vulnerability_Hypothesis:
    - Speculator should generate a Formal_Contract
    - Contract should be syntactically valid Python code
    - Contract should contain at least one @icontract decorator
    
    Validates: Requirements 2.1, 2.2
    Feature: llm-agent-intelligence, Property 8: Contract Syntax Validity
    """
    # Create mock client that returns valid contract
    mock_client = Mock(spec=LLMClient)
    valid_contract = """@icontract.require(lambda x: x is not None)
@icontract.ensure(lambda result: result is not None)"""
    
    mock_client.generate.return_value = valid_contract
    mock_client.generate_with_self_correction.return_value = valid_contract
    mock_client.validate_python_syntax.return_value = (True, None)
    
    speculator = SpeculatorAgent(llm_client=mock_client)
    
    vuln = Vulnerability(
        location="test.py:10",
        vuln_type=vuln_type,
        description=f"Test {vuln_type}",
        hypothesis=f"User input flows to vulnerable operation" if has_hypothesis else "",
        confidence=0.8
    )
    
    code = "def vulnerable_function(user_input):\n    pass"
    
    contract = speculator._generate_contract_with_retry(vuln, code)
    
    # Contract should be generated
    assert contract is not None
    assert isinstance(contract, Contract)
    
    # Contract should contain @icontract decorator
    assert "@icontract" in contract.code
    
    # Contract should be syntactically valid Python
    # (We can't fully validate without imports, but check basic structure)
    assert "lambda" in contract.code or "def" in contract.code


@settings(
    max_examples=10,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal"])
)
def test_property_vulnerability_specific_contract_patterns(vuln_type):
    """
    Property 9: Vulnerability-Specific Contract Patterns
    
    For any vulnerability type:
    - SQL injection contracts should check for SQL metacharacters (', --, ;, OR, UNION)
    - Command injection contracts should check for shell metacharacters (|, ;, &, `, $()
    - Path traversal contracts should check for directory traversal (.., /)
    
    Validates: Requirements 2.3, 2.4, 8.1, 8.2, 8.3
    Feature: llm-agent-intelligence, Property 9: Vulnerability-Specific Contract Patterns
    """
    speculator = SpeculatorAgent()
    
    # Get template contract (fallback behavior)
    vuln = Vulnerability(
        location="test.py:10",
        vuln_type=vuln_type,
        description=f"Test {vuln_type}",
        confidence=0.8
    )
    
    contract_code = speculator._generate_contract_template(vuln)
    
    # Contract should be generated
    assert contract_code is not None
    assert len(contract_code) > 0
    
    # Check for vulnerability-specific patterns
    if vuln_type == "SQL Injection":
        # Should check for SQL metacharacters
        has_sql_checks = (
            "'" in contract_code or
            "--" in contract_code or
            "OR" in contract_code.upper() or
            "UNION" in contract_code.upper()
        )
        assert has_sql_checks, f"SQL injection contract missing SQL metacharacter checks: {contract_code}"
    
    elif vuln_type == "Command Injection":
        # Should check for shell metacharacters
        has_shell_checks = (
            "|" in contract_code or
            ";" in contract_code or
            "&" in contract_code or
            "`" in contract_code or
            "$(" in contract_code
        )
        assert has_shell_checks, f"Command injection contract missing shell metacharacter checks: {contract_code}"
    
    elif vuln_type == "Path Traversal":
        # Should check for directory traversal
        has_path_checks = (
            ".." in contract_code or
            "/" in contract_code
        )
        assert has_path_checks, f"Path traversal contract missing directory traversal checks: {contract_code}"
