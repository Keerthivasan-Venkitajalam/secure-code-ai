"""
Unit tests for prompt template system.
Tests template formatting, few-shot examples, and anti-hallucination instructions.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.prompts import (
    PromptTemplate,
    VulnerabilityType,
    HYPOTHESIS_PROMPT,
    SLICING_PROMPT,
    CONTRACT_PROMPT,
    PATCH_PROMPT,
    get_secure_patterns,
    format_previous_attempts
)


class TestPromptTemplate:
    """Test PromptTemplate dataclass."""
    
    def test_template_creation(self):
        """Test creating a basic template."""
        template = PromptTemplate(
            name="test_template",
            template="Hello {name}!",
            max_tokens=100,
            temperature=0.5
        )
        
        assert template.name == "test_template"
        assert template.template == "Hello {name}!"
        assert template.max_tokens == 100
        assert template.temperature == 0.5
    
    def test_template_format_basic(self):
        """Test basic template formatting."""
        template = PromptTemplate(
            name="test",
            template="Hello {name}, you are {age} years old."
        )
        
        result = template.format(name="Alice", age=30)
        
        assert "Hello Alice" in result
        assert "30 years old" in result
    
    def test_template_format_with_system_prompt(self):
        """Test formatting with system prompt."""
        template = PromptTemplate(
            name="test",
            template="Task: {task}",
            system_prompt="You are a helpful assistant."
        )
        
        result = template.format(task="analyze code")
        
        assert "System Instructions" in result
        assert "You are a helpful assistant" in result
        assert "Task: analyze code" in result
    
    def test_template_format_with_output_format(self):
        """Test formatting with output format."""
        template = PromptTemplate(
            name="test",
            template="Generate: {item}",
            output_format="Output should be JSON"
        )
        
        result = template.format(item="data")
        
        assert "Output Format" in result
        assert "Output should be JSON" in result
    
    def test_template_format_with_constraints(self):
        """Test formatting with constraints."""
        template = PromptTemplate(
            name="test",
            template="Task: {task}",
            constraints=["Only output code", "No explanations"]
        )
        
        result = template.format(task="write function")
        
        assert "Constraints" in result
        assert "Only output code" in result
        assert "No explanations" in result
    
    def test_template_format_with_few_shot_examples(self):
        """Test formatting with few-shot examples."""
        template = PromptTemplate(
            name="test",
            template="Analyze: {code}",
            few_shot_examples={
                "SQL Injection": "Example: SELECT * FROM users",
                "XSS": "Example: <script>alert(1)</script>"
            }
        )
        
        result = template.format(code="test", vuln_type="SQL Injection")
        
        assert "Example" in result
        assert "SELECT * FROM users" in result
    
    def test_template_format_missing_variable(self):
        """Test formatting with missing variable raises KeyError."""
        template = PromptTemplate(
            name="test",
            template="Hello {name}!"
        )
        
        with pytest.raises(KeyError):
            template.format()
    
    def test_get_generation_params(self):
        """Test getting generation parameters."""
        template = PromptTemplate(
            name="test",
            template="Test",
            max_tokens=512,
            temperature=0.3
        )
        
        params = template.get_generation_params()
        
        assert params["max_tokens"] == 512
        assert params["temperature"] == 0.3


class TestHypothesisPrompt:
    """Test HYPOTHESIS_PROMPT template."""
    
    def test_hypothesis_prompt_exists(self):
        """Test hypothesis prompt is defined."""
        assert HYPOTHESIS_PROMPT is not None
        assert HYPOTHESIS_PROMPT.name == "hypothesis_generation"
    
    def test_hypothesis_prompt_format(self):
        """Test hypothesis prompt formatting."""
        result = HYPOTHESIS_PROMPT.format(
            code="def query(user): return f'SELECT * FROM users WHERE id={user}'",
            vuln_type="SQL Injection",
            line_num=1,
            function_name="query"
        )
        
        assert "SQL Injection" in result
        assert "line 1" in result
        assert "query" in result
        assert "Security Property" in result
        assert "Attack Vector" in result
    
    def test_hypothesis_prompt_has_system_prompt(self):
        """Test hypothesis prompt has system instructions."""
        assert HYPOTHESIS_PROMPT.system_prompt is not None
        assert "security expert" in HYPOTHESIS_PROMPT.system_prompt.lower()
    
    def test_hypothesis_prompt_has_constraints(self):
        """Test hypothesis prompt has anti-hallucination constraints."""
        assert len(HYPOTHESIS_PROMPT.constraints) > 0
        assert any("only analyze" in c.lower() for c in HYPOTHESIS_PROMPT.constraints)
    
    def test_hypothesis_prompt_has_few_shot_examples(self):
        """Test hypothesis prompt has few-shot examples."""
        assert "SQL Injection" in HYPOTHESIS_PROMPT.few_shot_examples
        assert "Command Injection" in HYPOTHESIS_PROMPT.few_shot_examples
        assert "Path Traversal" in HYPOTHESIS_PROMPT.few_shot_examples
    
    def test_hypothesis_prompt_sql_injection_example(self):
        """Test SQL injection example is included."""
        result = HYPOTHESIS_PROMPT.format(
            code="test",
            vuln_type="SQL Injection",
            line_num=1,
            function_name="test"
        )
        
        assert "Example for SQL Injection" in result or "SQL metacharacters" in result


class TestSlicingPrompt:
    """Test SLICING_PROMPT template."""
    
    def test_slicing_prompt_exists(self):
        """Test slicing prompt is defined."""
        assert SLICING_PROMPT is not None
        assert SLICING_PROMPT.name == "code_slicing"
    
    def test_slicing_prompt_format(self):
        """Test slicing prompt formatting."""
        result = SLICING_PROMPT.format(
            code="def vulnerable(): pass",
            vuln_type="SQL Injection",
            line_num=1,
            hypothesis="User input flows to SQL query"
        )
        
        assert "SQL Injection" in result
        assert "Line 1" in result
        assert "User input flows to SQL query" in result
    
    def test_slicing_prompt_has_constraints(self):
        """Test slicing prompt has code-only constraints."""
        assert len(SLICING_PROMPT.constraints) > 0
        assert any("only python code" in c.lower() for c in SLICING_PROMPT.constraints)
        assert any("mock" in c.lower() for c in SLICING_PROMPT.constraints)
    
    def test_slicing_prompt_low_temperature(self):
        """Test slicing prompt uses low temperature for precise code."""
        assert SLICING_PROMPT.temperature <= 0.2
    
    def test_slicing_prompt_has_examples(self):
        """Test slicing prompt has code examples."""
        assert "SQL Injection" in SLICING_PROMPT.few_shot_examples
        assert "import" in SLICING_PROMPT.few_shot_examples["SQL Injection"]
        assert "Mock" in SLICING_PROMPT.few_shot_examples["SQL Injection"]


class TestContractPrompt:
    """Test CONTRACT_PROMPT template."""
    
    def test_contract_prompt_exists(self):
        """Test contract prompt is defined."""
        assert CONTRACT_PROMPT is not None
        assert CONTRACT_PROMPT.name == "contract_generation"
    
    def test_contract_prompt_format(self):
        """Test contract prompt formatting."""
        result = CONTRACT_PROMPT.format(
            vuln_type="SQL Injection",
            hypothesis="SQL injection via user input",
            function_name="search_users"
        )
        
        assert "SQL Injection" in result
        assert "search_users" in result
        assert "icontract" in result
    
    def test_contract_prompt_has_icontract_examples(self):
        """Test contract prompt has icontract examples."""
        assert "SQL Injection" in CONTRACT_PROMPT.few_shot_examples
        example = CONTRACT_PROMPT.few_shot_examples["SQL Injection"]
        assert "@icontract.require" in example
        assert "@icontract.ensure" in example
        assert "lambda" in example
    
    def test_contract_prompt_sql_injection_checks(self):
        """Test SQL injection contract checks for dangerous characters."""
        example = CONTRACT_PROMPT.few_shot_examples["SQL Injection"]
        assert "'" in example  # Check for quotes
        assert "--" in example  # Check for comments
        assert "OR" in example or "UNION" in example  # Check for keywords
    
    def test_contract_prompt_command_injection_checks(self):
        """Test command injection contract checks for shell metacharacters."""
        example = CONTRACT_PROMPT.few_shot_examples["Command Injection"]
        assert "|" in example  # Pipe
        assert ";" in example  # Semicolon
        assert "&" in example  # Ampersand
        assert "`" in example or "$(" in example  # Command substitution
    
    def test_contract_prompt_path_traversal_checks(self):
        """Test path traversal contract checks for directory traversal."""
        example = CONTRACT_PROMPT.few_shot_examples["Path Traversal"]
        assert ".." in example  # Directory traversal
        assert "/" in example  # Absolute paths


class TestPatchPrompt:
    """Test PATCH_PROMPT template."""
    
    def test_patch_prompt_exists(self):
        """Test patch prompt is defined."""
        assert PATCH_PROMPT is not None
        assert PATCH_PROMPT.name == "patch_generation"
    
    def test_patch_prompt_format(self):
        """Test patch prompt formatting."""
        result = PATCH_PROMPT.format(
            code="def vulnerable(): pass",
            vuln_type="SQL Injection",
            hypothesis="SQL injection",
            counterexample="' OR '1'='1",
            previous_attempts="",
            secure_patterns="Use parameterized queries"
        )
        
        assert "SQL Injection" in result
        assert "' OR '1'='1" in result
        assert "parameterized queries" in result
    
    def test_patch_prompt_large_max_tokens(self):
        """Test patch prompt has large max_tokens for complete functions."""
        assert PATCH_PROMPT.max_tokens >= 4096
    
    def test_patch_prompt_has_secure_patterns(self):
        """Test patch prompt includes secure coding patterns."""
        assert "SQL Injection" in PATCH_PROMPT.few_shot_examples
        example = PATCH_PROMPT.few_shot_examples["SQL Injection"]
        assert "parameterized" in example.lower() or "?" in example
        assert "SECURITY FIX" in example
    
    def test_patch_prompt_preserves_signature(self):
        """Test patch examples preserve function signatures."""
        for example in PATCH_PROMPT.few_shot_examples.values():
            assert "def " in example  # Has function definition
            assert "(" in example and ")" in example  # Has parameters


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_secure_patterns_sql_injection(self):
        """Test getting secure patterns for SQL injection."""
        patterns = get_secure_patterns("SQL Injection")
        
        assert "parameterized" in patterns.lower()
        assert "ORM" in patterns or "orm" in patterns.lower()
    
    def test_get_secure_patterns_command_injection(self):
        """Test getting secure patterns for command injection."""
        patterns = get_secure_patterns("Command Injection")
        
        assert "subprocess" in patterns.lower()
        assert "shell=False" in patterns
    
    def test_get_secure_patterns_path_traversal(self):
        """Test getting secure patterns for path traversal."""
        patterns = get_secure_patterns("Path Traversal")
        
        assert "abspath" in patterns.lower() or "canonicalize" in patterns.lower()
        assert ".." in patterns
    
    def test_get_secure_patterns_unknown_type(self):
        """Test getting secure patterns for unknown vulnerability type."""
        patterns = get_secure_patterns("Unknown Type")
        
        assert "secure coding" in patterns.lower()
        assert "validate" in patterns.lower()
    
    def test_format_previous_attempts_empty(self):
        """Test formatting empty previous attempts."""
        result = format_previous_attempts([])
        
        assert result == ""
    
    def test_format_previous_attempts_single(self):
        """Test formatting single previous attempt."""
        result = format_previous_attempts(["def patch(): pass"])
        
        assert "Previous Failed Attempts" in result
        assert "Attempt 1" in result
        assert "def patch(): pass" in result
    
    def test_format_previous_attempts_multiple(self):
        """Test formatting multiple previous attempts."""
        result = format_previous_attempts([
            "def patch1(): pass",
            "def patch2(): pass"
        ])
        
        assert "Attempt 1" in result
        assert "Attempt 2" in result
        assert "def patch1(): pass" in result
        assert "def patch2(): pass" in result


class TestVulnerabilityType:
    """Test VulnerabilityType enum."""
    
    def test_vulnerability_types_defined(self):
        """Test all vulnerability types are defined."""
        assert VulnerabilityType.SQL_INJECTION.value == "SQL Injection"
        assert VulnerabilityType.COMMAND_INJECTION.value == "Command Injection"
        assert VulnerabilityType.PATH_TRAVERSAL.value == "Path Traversal"
        assert VulnerabilityType.XSS.value == "Cross-Site Scripting"
    
    def test_vulnerability_type_enumeration(self):
        """Test vulnerability types can be enumerated."""
        types = list(VulnerabilityType)
        assert len(types) >= 3  # At least SQL, Command, Path


# Property-Based Tests

@settings(
    max_examples=20,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    name=st.text(min_size=1, max_size=50),
    template_text=st.text(min_size=1, max_size=100),
    max_tokens=st.integers(min_value=1, max_value=8192),
    temperature=st.floats(min_value=0.0, max_value=1.0)
)
def test_property_template_creation(name, template_text, max_tokens, temperature):
    """
    Property: Template creation with any valid parameters
    
    For all valid template parameters:
    - Template can be created without errors
    - Parameters are stored correctly
    - get_generation_params() returns correct values
    
    Validates: Requirements 5.1, 5.2
    """
    template = PromptTemplate(
        name=name,
        template=template_text,
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    assert template.name == name
    assert template.template == template_text
    assert template.max_tokens == max_tokens
    assert abs(template.temperature - temperature) < 0.001
    
    params = template.get_generation_params()
    assert params["max_tokens"] == max_tokens
    assert abs(params["temperature"] - temperature) < 0.001


@settings(
    max_examples=30,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    vuln_type=st.sampled_from(["SQL Injection", "Command Injection", "Path Traversal", "XSS"])
)
def test_property_all_prompts_have_examples(vuln_type):
    """
    Property: All major prompts have examples for common vulnerabilities
    
    For all common vulnerability types:
    - HYPOTHESIS_PROMPT should have examples
    - SLICING_PROMPT should have examples
    - CONTRACT_PROMPT should have examples
    - PATCH_PROMPT should have examples
    
    Validates: Requirements 5.2, 5.3
    """
    # Check hypothesis prompt
    if vuln_type in ["SQL Injection", "Command Injection", "Path Traversal"]:
        assert vuln_type in HYPOTHESIS_PROMPT.few_shot_examples
        assert len(HYPOTHESIS_PROMPT.few_shot_examples[vuln_type]) > 0
    
    # Check slicing prompt
    if vuln_type in ["SQL Injection", "Command Injection"]:
        assert vuln_type in SLICING_PROMPT.few_shot_examples
        assert "import" in SLICING_PROMPT.few_shot_examples[vuln_type]
    
    # Check contract prompt
    if vuln_type in ["SQL Injection", "Command Injection", "Path Traversal"]:
        assert vuln_type in CONTRACT_PROMPT.few_shot_examples
        assert "@icontract" in CONTRACT_PROMPT.few_shot_examples[vuln_type]
    
    # Check patch prompt
    if vuln_type in ["SQL Injection", "Command Injection", "Path Traversal"]:
        assert vuln_type in PATCH_PROMPT.few_shot_examples
        assert "def " in PATCH_PROMPT.few_shot_examples[vuln_type]


@settings(
    max_examples=20,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(
    constraints=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
)
def test_property_constraints_appear_in_output(constraints):
    """
    Property: All constraints appear in formatted output
    
    For all constraint lists:
    - Each constraint should appear in the formatted prompt
    - Constraints section should be present
    
    Validates: Requirements 5.3
    """
    template = PromptTemplate(
        name="test",
        template="Task: {task}",
        constraints=constraints
    )
    
    result = template.format(task="test")
    
    assert "Constraints" in result
    for constraint in constraints:
        assert constraint in result
