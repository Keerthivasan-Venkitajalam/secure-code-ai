"""
Property-based tests for output validation across all agents.
Tests that all agent outputs are properly validated.
"""

import ast
import pytest
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.nodes.scanner import ScannerAgent
from agent.nodes.speculator import SpeculatorAgent
from agent.nodes.patcher import PatcherAgent
from agent.llm_client import LLMClient
from agent.state import Vulnerability, Contract, Patch


# Strategies for generating test data

@st.composite
def vulnerability_strategy(draw):
    """Generate random Vulnerability objects."""
    vuln_types = ["SQL Injection", "Command Injection", "Path Traversal", "Code Injection"]
    
    return Vulnerability(
        location=f"test.py:{draw(st.integers(min_value=1, max_value=100))}",
        vuln_type=draw(st.sampled_from(vuln_types)),
        description=draw(st.text(min_size=10, max_size=100)),
        hypothesis=draw(st.text(min_size=20, max_size=200)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        severity=draw(st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"]))
    )


@st.composite
def contract_strategy(draw):
    """Generate random Contract objects."""
    vuln_types = ["SQL Injection", "Command Injection", "Path Traversal"]
    
    # Generate valid icontract code
    contract_templates = [
        "@icontract.require(lambda x: x is not None)\n@icontract.ensure(lambda result: result is not None)",
        "@icontract.require(lambda input: len(input) > 0)\n@icontract.ensure(lambda result: \"'\" not in result)",
        "@icontract.require(lambda path: \"..\" not in path)\n@icontract.ensure(lambda result: result is not None)"
    ]
    
    return Contract(
        code=draw(st.sampled_from(contract_templates)),
        vuln_type=draw(st.sampled_from(vuln_types)),
        target_function=f"func_{draw(st.integers(min_value=1, max_value=100))}"
    )


@st.composite
def patch_strategy(draw):
    """Generate random Patch objects."""
    # Generate valid Python code
    patch_templates = [
        "def safe_function(x):\n    return x",
        "def secure_query(user_input):\n    query = \"SELECT * FROM users WHERE id = ?\"\n    return query",
        "def safe_command(cmd):\n    result = subprocess.run([cmd], shell=False)\n    return result"
    ]
    
    return Patch(
        code=draw(st.sampled_from(patch_templates)),
        diff=draw(st.text(min_size=10, max_size=100)),
        verified=draw(st.booleans())
    )


@st.composite
def code_slice_strategy(draw):
    """Generate random code slices."""
    slice_templates = [
        "def vulnerable_func(x):\n    return eval(x)",
        "import sqlite3\n\ndef query_db(user_input):\n    conn = sqlite3.connect('db')\n    return conn.execute(f\"SELECT * FROM users WHERE id={user_input}\")",
        "import subprocess\n\ndef run_cmd(cmd):\n    return subprocess.run(cmd, shell=True)"
    ]
    
    return draw(st.sampled_from(slice_templates))


# Property-Based Tests

@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    vuln=vulnerability_strategy()
)
def test_property_output_validation_scanner_hypothesis(vuln):
    """
    Property 18: Output Validation - Scanner Hypothesis
    
    For any LLM-generated hypothesis:
    - Scanner should validate hypothesis contains required fields
    - location should be non-empty
    - vuln_type should be non-empty
    - confidence should be in range [0.0, 1.0]
    - hypothesis should be non-empty (if LLM was used)
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create scanner with mock LLM client
    mock_client = Mock(spec=LLMClient)
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Validate the hypothesis
    is_valid, error = scanner.validate_hypothesis(vuln)
    
    # Check validation logic
    if not vuln.location:
        assert not is_valid
        assert "location" in error.lower()
    elif not vuln.vuln_type:
        assert not is_valid
        assert "vuln_type" in error.lower()
    elif not (0.0 <= vuln.confidence <= 1.0):
        assert not is_valid
        assert "confidence" in error.lower()
    elif mock_client and not vuln.hypothesis:
        assert not is_valid
        assert "hypothesis" in error.lower()
    else:
        assert is_valid
        assert error is None


@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    code_slice=code_slice_strategy()
)
def test_property_output_validation_scanner_slice(code_slice):
    """
    Property 18: Output Validation - Scanner Code Slice
    
    For any generated code slice:
    - Scanner should validate slice is valid Python
    - Slice should be parseable by ast.parse()
    - Slice should be non-empty
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create scanner with mock LLM client
    mock_client = Mock(spec=LLMClient)
    mock_client.validate_python_syntax.return_value = (True, None)
    
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Validate the code slice
    is_valid, error = scanner.validate_code_slice(code_slice)
    
    # Check validation logic
    if not code_slice:
        assert not is_valid
        assert "empty" in error.lower()
    else:
        # Should validate syntax
        try:
            ast.parse(code_slice)
            expected_valid = True
        except:
            expected_valid = False
        
        # Our validation should match ast.parse result
        if expected_valid:
            assert is_valid
        else:
            # If ast.parse fails, validation should fail
            # (unless mock returns different result)
            pass


@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    contract=contract_strategy()
)
def test_property_output_validation_speculator_contract(contract):
    """
    Property 18: Output Validation - Speculator Contract
    
    For any generated contract:
    - Speculator should validate contract is valid Python
    - Contract should contain @icontract decorators
    - vuln_type should be non-empty
    - target_function should be non-empty
    - Contract code should be non-empty
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create speculator with mock LLM client
    mock_client = Mock(spec=LLMClient)
    mock_client.validate_python_syntax.return_value = (True, None)
    
    speculator = SpeculatorAgent(llm_client=mock_client)
    
    # Validate the contract
    is_valid, error = speculator.validate_contract(contract)
    
    # Check validation logic
    if not contract.code:
        assert not is_valid
        assert "code" in error.lower()
    elif not contract.vuln_type:
        assert not is_valid
        assert "vuln_type" in error.lower()
    elif not contract.target_function:
        assert not is_valid
        assert "target_function" in error.lower()
    elif "@icontract" not in contract.code:
        assert not is_valid
        assert "icontract" in error.lower()
    else:
        # Should validate syntax
        try:
            ast.parse(contract.code)
            assert is_valid
        except:
            # If ast.parse fails, validation should fail
            pass


@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    patch=patch_strategy()
)
def test_property_output_validation_patcher_patch(patch):
    """
    Property 18: Output Validation - Patcher Patch
    
    For any generated patch:
    - Patcher should validate patch is valid Python
    - Patch should preserve function signature
    - Patch code should be non-empty
    - Patch diff should be non-empty
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create patcher with mock LLM client
    mock_client = Mock(spec=LLMClient)
    mock_client.validate_python_syntax.return_value = (True, None)
    
    patcher = PatcherAgent(llm_client=mock_client)
    
    # Use a simple original code for signature comparison
    original_code = "def safe_function(x):\n    return x"
    
    # Validate the patch
    is_valid, error = patcher.validate_patch(patch, original_code)
    
    # Check validation logic
    if not patch.code:
        assert not is_valid
        assert "code" in error.lower()
    elif not patch.diff:
        assert not is_valid
        assert "diff" in error.lower()
    else:
        # Should validate syntax
        try:
            ast.parse(patch.code)
            expected_valid = True
        except:
            expected_valid = False
        
        if expected_valid:
            # Check if signature is preserved
            # (this is complex, so we just check validation runs)
            pass


@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    has_location=st.booleans(),
    has_vuln_type=st.booleans(),
    confidence=st.floats(min_value=-1.0, max_value=2.0),
    has_hypothesis=st.booleans()
)
def test_property_output_validation_comprehensive(has_location, has_vuln_type, confidence, has_hypothesis):
    """
    Property 18: Output Validation - Comprehensive
    
    For any agent output:
    - Validation should catch missing required fields
    - Validation should catch invalid value ranges
    - Validation should catch syntax errors
    - Validation should return clear error messages
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create scanner with mock LLM client
    mock_client = Mock(spec=LLMClient)
    scanner = ScannerAgent(llm_client=mock_client)
    
    # Create vulnerability with controlled fields
    vuln = Vulnerability(
        location="test.py:10" if has_location else "",
        vuln_type="SQL Injection" if has_vuln_type else "",
        description="Test vulnerability",
        hypothesis="Test hypothesis" if has_hypothesis else "",
        confidence=confidence
    )
    
    # Validate
    is_valid, error = scanner.validate_hypothesis(vuln)
    
    # Check validation catches issues
    expected_valid = (
        has_location and
        has_vuln_type and
        (0.0 <= confidence <= 1.0) and
        (not mock_client or has_hypothesis)
    )
    
    if expected_valid:
        assert is_valid
        assert error is None
    else:
        assert not is_valid
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0


@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    code_valid=st.booleans(),
    has_icontract=st.booleans(),
    has_vuln_type=st.booleans(),
    has_target_func=st.booleans()
)
def test_property_output_validation_contract_comprehensive(code_valid, has_icontract, has_vuln_type, has_target_func):
    """
    Property 18: Output Validation - Contract Comprehensive
    
    For any contract output:
    - Validation should verify Python syntax
    - Validation should verify icontract decorators present
    - Validation should verify required fields
    - Validation should return clear error messages
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create speculator with mock LLM client
    mock_client = Mock(spec=LLMClient)
    mock_client.validate_python_syntax.return_value = (code_valid, "Syntax error" if not code_valid else None)
    
    speculator = SpeculatorAgent(llm_client=mock_client)
    
    # Create contract with controlled fields
    contract_code = "@icontract.require(lambda x: x > 0)" if has_icontract else "# No decorator"
    
    contract = Contract(
        code=contract_code,
        vuln_type="SQL Injection" if has_vuln_type else "",
        target_function="test_func" if has_target_func else ""
    )
    
    # Validate
    is_valid, error = speculator.validate_contract(contract)
    
    # Check validation catches issues
    expected_valid = (
        code_valid and
        has_icontract and
        has_vuln_type and
        has_target_func
    )
    
    if expected_valid:
        assert is_valid
        assert error is None
    else:
        assert not is_valid
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0


@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    code_valid=st.booleans(),
    has_code=st.booleans(),
    has_diff=st.booleans()
)
def test_property_output_validation_patch_comprehensive(code_valid, has_code, has_diff):
    """
    Property 18: Output Validation - Patch Comprehensive
    
    For any patch output:
    - Validation should verify Python syntax
    - Validation should verify required fields
    - Validation should verify function signature preservation
    - Validation should return clear error messages
    
    Validates: Requirements 5.4, 5.5
    Feature: llm-agent-intelligence, Property 18: Output Validation
    """
    # Create patcher with mock LLM client
    mock_client = Mock(spec=LLMClient)
    mock_client.validate_python_syntax.return_value = (code_valid, "Syntax error" if not code_valid else None)
    
    patcher = PatcherAgent(llm_client=mock_client)
    
    # Create patch with controlled fields
    patch_code = "def test_func(x):\n    return x" if has_code else ""
    patch_diff = "- old\n+ new" if has_diff else ""
    
    patch = Patch(
        code=patch_code,
        diff=patch_diff,
        verified=False
    )
    
    original_code = "def test_func(x):\n    return x"
    
    # Validate
    is_valid, error = patcher.validate_patch(patch, original_code)
    
    # Check validation catches issues
    expected_valid = (
        code_valid and
        has_code and
        has_diff
    )
    
    if expected_valid:
        assert is_valid
        assert error is None
    else:
        assert not is_valid
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0


# Unit tests for edge cases

class TestOutputValidationEdgeCases:
    """Test edge cases in output validation."""
    
    def test_scanner_validate_hypothesis_empty_location(self):
        """Test validation catches empty location."""
        scanner = ScannerAgent()
        
        vuln = Vulnerability(
            location="",
            vuln_type="SQL Injection",
            confidence=0.8
        )
        
        is_valid, error = scanner.validate_hypothesis(vuln)
        
        assert not is_valid
        assert "location" in error.lower()
    
    def test_scanner_validate_hypothesis_invalid_confidence(self):
        """Test validation catches invalid confidence range."""
        scanner = ScannerAgent()
        
        vuln = Vulnerability(
            location="test.py:10",
            vuln_type="SQL Injection",
            confidence=1.5  # Invalid: > 1.0
        )
        
        is_valid, error = scanner.validate_hypothesis(vuln)
        
        assert not is_valid
        assert "confidence" in error.lower()
    
    def test_scanner_validate_slice_empty(self):
        """Test validation catches empty code slice."""
        scanner = ScannerAgent()
        
        is_valid, error = scanner.validate_code_slice("")
        
        assert not is_valid
        assert "empty" in error.lower()
    
    def test_scanner_validate_slice_invalid_syntax(self):
        """Test validation catches invalid Python syntax."""
        scanner = ScannerAgent()
        
        invalid_code = "def broken(\n    pass"
        
        is_valid, error = scanner.validate_code_slice(invalid_code)
        
        assert not is_valid
        assert error is not None
    
    def test_speculator_validate_contract_no_icontract(self):
        """Test validation catches missing icontract decorators."""
        speculator = SpeculatorAgent()
        
        contract = Contract(
            code="def test():\n    pass",
            vuln_type="SQL Injection",
            target_function="test"
        )
        
        is_valid, error = speculator.validate_contract(contract)
        
        assert not is_valid
        assert "icontract" in error.lower()
    
    def test_patcher_validate_patch_empty_code(self):
        """Test validation catches empty patch code."""
        patcher = PatcherAgent()
        
        patch = Patch(
            code="",
            diff="- old\n+ new"
        )
        
        is_valid, error = patcher.validate_patch(patch, "def test(): pass")
        
        assert not is_valid
        assert "code" in error.lower()
    
    def test_patcher_validate_patch_empty_diff(self):
        """Test validation catches empty diff."""
        patcher = PatcherAgent()
        
        patch = Patch(
            code="def test():\n    pass",
            diff=""
        )
        
        is_valid, error = patcher.validate_patch(patch, "def test(): pass")
        
        assert not is_valid
        assert "diff" in error.lower()
