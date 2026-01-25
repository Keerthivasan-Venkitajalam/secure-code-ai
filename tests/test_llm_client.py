"""
Unit tests for LLM client wrapper for agent intelligence.
Tests generation, syntax validation, retry logic, and async support.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from agent.llm_client import LLMClient
from api.vllm_client import VLLMClient, VLLMInferenceError


@pytest.fixture(scope="session")
def mock_vllm_module():
    """Mock vLLM module at import time."""
    # Create mock vLLM module
    mock_vllm = MagicMock()
    
    # Mock SamplingParams class
    mock_sampling_class = Mock()
    mock_vllm.SamplingParams = mock_sampling_class
    
    # Install mock module
    sys.modules['vllm'] = mock_vllm
    
    yield {
        'vllm': mock_vllm,
        'sampling_class': mock_sampling_class
    }
    
    # Cleanup
    if 'vllm' in sys.modules:
        del sys.modules['vllm']


@pytest.fixture
def mock_vllm_client():
    """Create a mock VLLMClient for testing."""
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    return mock_client


class TestLLMClientInitialization:
    """Test LLMClient initialization."""
    
    def test_client_creation_with_vllm_client(self, mock_vllm_client):
        """Test LLMClient can be created with VLLMClient."""
        client = LLMClient(mock_vllm_client)
        
        assert client.vllm_client is mock_vllm_client
        assert client.default_max_tokens == 2048
        assert client.default_temperature == 0.2
        assert client.default_top_p == 0.95
    
    def test_client_initializes_vllm_if_needed(self):
        """Test LLMClient initializes VLLMClient if not initialized."""
        mock_client = Mock(spec=VLLMClient)
        mock_client.is_initialized.return_value = False
        
        client = LLMClient(mock_client)
        
        mock_client.initialize.assert_called_once()
    
    def test_client_skips_init_if_already_initialized(self, mock_vllm_client):
        """Test LLMClient skips initialization if VLLMClient already initialized."""
        client = LLMClient(mock_vllm_client)
        
        mock_vllm_client.initialize.assert_not_called()
    
    def test_get_config_returns_defaults(self, mock_vllm_client):
        """Test get_config() returns default configuration."""
        client = LLMClient(mock_vllm_client)
        
        config = client.get_config()
        
        assert config["max_tokens"] == 2048
        assert config["temperature"] == 0.2
        assert config["top_p"] == 0.95
        assert config["vllm_initialized"] is True


class TestLLMClientGeneration:
    """Test LLMClient text generation."""
    
    def test_generate_with_defaults(self, mock_vllm_module, mock_vllm_client):
        """Test generate() uses default parameters."""
        mock_vllm_client.generate.return_value = "Generated text"
        
        client = LLMClient(mock_vllm_client)
        result = client.generate("Test prompt")
        
        assert result == "Generated text"
        mock_vllm_client.generate.assert_called_once_with("Test prompt")
        
        # Check SamplingParams was created with defaults
        mock_vllm_module['sampling_class'].assert_called()
        call_kwargs = mock_vllm_module['sampling_class'].call_args[1]
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["max_tokens"] == 2048
    
    def test_generate_with_custom_params(self, mock_vllm_module, mock_vllm_client):
        """Test generate() accepts custom parameters."""
        mock_vllm_client.generate.return_value = "Custom generated"
        
        client = LLMClient(mock_vllm_client)
        result = client.generate("Test prompt", max_tokens=1024, temperature=0.5)
        
        assert result == "Custom generated"
        
        # Check SamplingParams was created with custom values
        call_kwargs = mock_vllm_module['sampling_class'].call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1024
    
    def test_generate_restores_original_params(self, mock_vllm_module, mock_vllm_client):
        """Test generate() restores original sampling parameters."""
        original_params = Mock()
        mock_vllm_client.sampling_params = original_params
        mock_vllm_client.generate.return_value = "Text"
        
        client = LLMClient(mock_vllm_client)
        client.generate("Test prompt")
        
        # Should restore original params
        assert mock_vllm_client.sampling_params == original_params
    
    def test_generate_restores_params_on_error(self, mock_vllm_module, mock_vllm_client):
        """Test generate() restores parameters even on error."""
        original_params = Mock()
        mock_vllm_client.sampling_params = original_params
        mock_vllm_client.generate.side_effect = VLLMInferenceError("Error")
        
        client = LLMClient(mock_vllm_client)
        
        with pytest.raises(VLLMInferenceError):
            client.generate("Test prompt")
        
        # Should still restore original params
        assert mock_vllm_client.sampling_params == original_params
    
    @pytest.mark.asyncio
    async def test_generate_async(self, mock_vllm_module, mock_vllm_client):
        """Test generate_async() works correctly."""
        mock_vllm_client.generate.return_value = "Async generated"
        
        client = LLMClient(mock_vllm_client)
        result = await client.generate_async("Test prompt")
        
        assert result == "Async generated"
        mock_vllm_client.generate.assert_called_once()


class TestLLMClientSyntaxValidation:
    """Test LLMClient Python syntax validation."""
    
    def test_validate_valid_python_code(self, mock_vllm_client):
        """Test validate_python_syntax() accepts valid Python code."""
        client = LLMClient(mock_vllm_client)
        
        valid_code = """
def hello():
    print("Hello, world!")
    return 42
"""
        
        is_valid, error = client.validate_python_syntax(valid_code)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_invalid_python_code(self, mock_vllm_client):
        """Test validate_python_syntax() rejects invalid Python code."""
        client = LLMClient(mock_vllm_client)
        
        invalid_code = """
def hello(:
    print("Missing closing paren"
"""
        
        is_valid, error = client.validate_python_syntax(invalid_code)
        
        assert is_valid is False
        assert error is not None
        assert "Syntax error" in error or "Parse error" in error
    
    def test_validate_empty_code(self, mock_vllm_client):
        """Test validate_python_syntax() accepts empty code."""
        client = LLMClient(mock_vllm_client)
        
        is_valid, error = client.validate_python_syntax("")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_complex_valid_code(self, mock_vllm_client):
        """Test validate_python_syntax() with complex valid code."""
        client = LLMClient(mock_vllm_client)
        
        complex_code = """
import icontract

@icontract.require(lambda x: x > 0)
@icontract.ensure(lambda result: result > 0)
def factorial(x: int) -> int:
    if x == 1:
        return 1
    return x * factorial(x - 1)
"""
        
        is_valid, error = client.validate_python_syntax(complex_code)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_indentation_error(self, mock_vllm_client):
        """Test validate_python_syntax() detects indentation errors."""
        client = LLMClient(mock_vllm_client)
        
        bad_indent = """
def hello():
print("Bad indent")
"""
        
        is_valid, error = client.validate_python_syntax(bad_indent)
        
        assert is_valid is False
        assert error is not None


class TestLLMClientRetry:
    """Test LLMClient retry logic."""
    
    def test_generate_with_retry_success_first_try(self, mock_vllm_module, mock_vllm_client):
        """Test generate_with_retry() succeeds on first try."""
        mock_vllm_client.generate.return_value = "Success"
        
        client = LLMClient(mock_vllm_client)
        result = client.generate_with_retry("Test prompt")
        
        assert result == "Success"
        assert mock_vllm_client.generate.call_count == 1
    
    def test_generate_with_retry_retries_on_error(self, mock_vllm_module, mock_vllm_client):
        """Test generate_with_retry() retries on VLLMInferenceError."""
        # Fail twice, then succeed
        mock_vllm_client.generate.side_effect = [
            VLLMInferenceError("First failure"),
            VLLMInferenceError("Second failure"),
            "Success"
        ]
        
        client = LLMClient(mock_vllm_client)
        result = client.generate_with_retry("Test prompt")
        
        assert result == "Success"
        assert mock_vllm_client.generate.call_count == 3
    
    def test_generate_with_retry_gives_up_after_max_attempts(self, mock_vllm_module, mock_vllm_client):
        """Test generate_with_retry() gives up after 3 attempts."""
        mock_vllm_client.generate.side_effect = VLLMInferenceError("Persistent failure")
        
        client = LLMClient(mock_vllm_client)
        
        with pytest.raises(VLLMInferenceError, match="Persistent failure"):
            client.generate_with_retry("Test prompt")
        
        # Should try 3 times
        assert mock_vllm_client.generate.call_count == 3


# Property-Based Tests

@settings(
    max_examples=20, 
    deadline=2000, 
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    max_tokens=st.integers(min_value=1, max_value=4096),
    temperature=st.floats(min_value=0.0, max_value=1.0)
)
def test_property_generate_parameters(mock_vllm_module, max_tokens, temperature):
    """
    Property: Generate accepts any valid parameters
    
    For all valid max_tokens and temperature values:
    - generate() should not crash
    - Parameters should be passed correctly
    
    Validates: Requirements 10.1, 10.2
    """
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    mock_client.generate.return_value = "Generated"
    
    client = LLMClient(mock_client)
    result = client.generate("Test", max_tokens=max_tokens, temperature=temperature)
    
    assert result == "Generated"
    
    # Check parameters were used
    call_kwargs = mock_vllm_module['sampling_class'].call_args[1]
    assert call_kwargs["max_tokens"] == max_tokens
    assert abs(call_kwargs["temperature"] - temperature) < 0.001


@settings(
    max_examples=30, 
    deadline=2000, 
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    code=st.text(min_size=0, max_size=200)
)
def test_property_syntax_validation_deterministic(mock_vllm_module, code):
    """
    Property: Syntax validation is deterministic
    
    For all code strings:
    - validate_python_syntax() should return consistent results
    - Calling twice should give same result
    - Result should be a tuple of (bool, Optional[str])
    
    Validates: Requirements 10.1, 10.2
    """
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    
    client = LLMClient(mock_client)
    
    result1 = client.validate_python_syntax(code)
    result2 = client.validate_python_syntax(code)
    
    assert result1 == result2
    assert isinstance(result1, tuple)
    assert len(result1) == 2
    assert isinstance(result1[0], bool)
    assert result1[1] is None or isinstance(result1[1], str)


@settings(
    max_examples=10, 
    deadline=5000, 
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    prompt=st.text(min_size=1, max_size=50)
)
@pytest.mark.asyncio
async def test_property_async_matches_sync(mock_vllm_module, prompt):
    """
    Property: Async generation matches sync generation
    
    For all valid prompts:
    - generate_async() should return same result as generate()
    - Both should complete successfully
    
    Validates: Requirements 10.1, 10.2
    """
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    mock_client.generate.return_value = f"Response: {prompt[:20]}"
    
    client = LLMClient(mock_client)
    
    sync_result = client.generate(prompt)
    async_result = await client.generate_async(prompt)
    
    # Results should be the same
    assert sync_result == async_result
    assert isinstance(async_result, str)


@settings(
    max_examples=50, 
    deadline=2000, 
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    prompt=st.text(min_size=1, max_size=100),
    max_tokens=st.one_of(st.none(), st.integers(min_value=1, max_value=4096)),
    temperature=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0))
)
def test_property_llm_configuration_enforcement(mock_vllm_module, prompt, max_tokens, temperature):
    """
    Property 17: LLM Configuration Enforcement
    
    For any LLM generation request:
    - The request should use max_tokens ≤ 2048 (default) or specified value
    - The request should use temperature = 0.2 (default) or specified value
    - This ensures deterministic, focused responses
    
    Validates: Requirements 10.1, 10.2
    Feature: llm-agent-intelligence, Property 17: LLM Configuration Enforcement
    """
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    mock_client.generate.return_value = "Generated text"
    
    client = LLMClient(mock_client)
    
    # Generate with optional parameters
    result = client.generate(prompt, max_tokens=max_tokens, temperature=temperature)
    
    assert result == "Generated text"
    
    # Check that SamplingParams was called
    assert mock_vllm_module['sampling_class'].called
    
    # Get the actual parameters used
    call_kwargs = mock_vllm_module['sampling_class'].call_args[1]
    
    # Verify max_tokens constraint
    actual_max_tokens = call_kwargs["max_tokens"]
    if max_tokens is None:
        # Should use default
        assert actual_max_tokens == 2048
    else:
        # Should use specified value
        assert actual_max_tokens == max_tokens
    
    # Verify max_tokens is always ≤ 2048 when using defaults
    if max_tokens is None:
        assert actual_max_tokens <= 2048
    
    # Verify temperature constraint
    actual_temperature = call_kwargs["temperature"]
    if temperature is None:
        # Should use default
        assert actual_temperature == 0.2
    else:
        # Should use specified value
        assert abs(actual_temperature - temperature) < 0.001
    
    # Verify temperature is deterministic (0.2) when using defaults
    if temperature is None:
        assert actual_temperature == 0.2


class TestSelfCorrectionLoop:
    """Test self-correction loop infrastructure."""
    
    def test_self_correction_success_first_try(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction succeeds on first try."""
        mock_vllm_client.generate.return_value = "valid output"
        
        client = LLMClient(mock_vllm_client)
        
        # Prompt builder that ignores error feedback
        def prompt_builder(error_feedback):
            return "Generate valid output"
        
        # Validator that always accepts
        def validator(output):
            return (True, None)
        
        result = client.generate_with_self_correction(prompt_builder, validator)
        
        assert result == "valid output"
        assert mock_vllm_client.generate.call_count == 1
    
    def test_self_correction_retries_on_validation_failure(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction retries when validation fails."""
        # First two attempts fail validation, third succeeds
        mock_vllm_client.generate.side_effect = [
            "invalid output 1",
            "invalid output 2",
            "valid output"
        ]
        
        client = LLMClient(mock_vllm_client)
        
        attempt_count = [0]
        
        def prompt_builder(error_feedback):
            if error_feedback:
                return f"Try again. Previous error: {error_feedback}"
            return "Generate output"
        
        def validator(output):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                return (False, f"Validation error {attempt_count[0]}")
            return (True, None)
        
        result = client.generate_with_self_correction(prompt_builder, validator)
        
        assert result == "valid output"
        assert mock_vllm_client.generate.call_count == 3
    
    def test_self_correction_includes_error_feedback(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction includes error feedback in retry prompts."""
        mock_vllm_client.generate.side_effect = [
            "invalid",
            "valid"
        ]
        
        client = LLMClient(mock_vllm_client)
        
        prompts_received = []
        
        def prompt_builder(error_feedback):
            prompt = "Generate output"
            if error_feedback:
                prompt += f"\nError: {error_feedback}"
            prompts_received.append(prompt)
            return prompt
        
        attempt = [0]
        def validator(output):
            attempt[0] += 1
            if attempt[0] == 1:
                return (False, "Syntax error on line 5")
            return (True, None)
        
        result = client.generate_with_self_correction(prompt_builder, validator)
        
        assert result == "valid"
        assert len(prompts_received) == 2
        # Second prompt should include error feedback
        assert "Syntax error on line 5" in prompts_received[1]
    
    def test_self_correction_returns_none_after_max_retries(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction returns None after max retries."""
        mock_vllm_client.generate.return_value = "always invalid"
        
        client = LLMClient(mock_vllm_client)
        
        def prompt_builder(error_feedback):
            return "Generate output"
        
        def validator(output):
            return (False, "Always fails")
        
        result = client.generate_with_self_correction(prompt_builder, validator, max_retries=3)
        
        assert result is None
        assert mock_vllm_client.generate.call_count == 3
    
    def test_self_correction_handles_generation_errors(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction handles generation errors gracefully."""
        # First attempt throws error, second succeeds
        mock_vllm_client.generate.side_effect = [
            VLLMInferenceError("Generation failed"),
            "valid output"
        ]
        
        client = LLMClient(mock_vllm_client)
        
        def prompt_builder(error_feedback):
            return "Generate output"
        
        def validator(output):
            return (True, None)
        
        result = client.generate_with_self_correction(prompt_builder, validator)
        
        assert result == "valid output"
        assert mock_vllm_client.generate.call_count == 2
    
    def test_self_correction_with_custom_max_retries(self, mock_vllm_module, mock_vllm_client):
        """Test self-correction respects custom max_retries."""
        mock_vllm_client.generate.return_value = "invalid"
        
        client = LLMClient(mock_vllm_client)
        
        def prompt_builder(error_feedback):
            return "Generate output"
        
        def validator(output):
            return (False, "Always fails")
        
        result = client.generate_with_self_correction(prompt_builder, validator, max_retries=5)
        
        assert result is None
        assert mock_vllm_client.generate.call_count == 5


# Property-Based Tests for Self-Correction

@settings(
    max_examples=10,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture]
)
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    fail_count=st.integers(min_value=0, max_value=4)
)
def test_property_self_correction_loop(mock_vllm_module, max_retries, fail_count):
    """
    Property 10: Self-Correction Loop
    
    For any self-correction configuration:
    - If validation fails < max_retries times, should eventually succeed
    - If validation fails >= max_retries times, should return None
    - Error feedback should be passed to prompt_builder on retries
    - All retry attempts should be logged
    
    Validates: Requirements 2.5, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5
    Feature: llm-agent-intelligence, Property 10: Self-Correction Loop
    """
    mock_client = Mock(spec=VLLMClient)
    mock_client.is_initialized.return_value = True
    mock_client.sampling_params = Mock()
    
    # Generate outputs: fail_count failures, then success
    outputs = [f"invalid_{i}" for i in range(fail_count)] + ["valid_output"]
    mock_client.generate.side_effect = outputs
    
    client = LLMClient(mock_client)
    
    attempt = [0]
    error_feedbacks = []
    
    def prompt_builder(error_feedback):
        error_feedbacks.append(error_feedback)
        return "Generate output"
    
    def validator(output):
        attempt[0] += 1
        if attempt[0] <= fail_count:
            return (False, f"Error {attempt[0]}")
        return (True, None)
    
    result = client.generate_with_self_correction(
        prompt_builder,
        validator,
        max_retries=max_retries
    )
    
    # Check result
    if fail_count < max_retries:
        # Should succeed
        assert result == "valid_output"
        assert mock_client.generate.call_count == fail_count + 1
    else:
        # Should fail (max retries exceeded)
        assert result is None
        assert mock_client.generate.call_count == max_retries
    
    # Check error feedback was passed
    if fail_count > 0:
        # First attempt has no error feedback
        assert error_feedbacks[0] is None
        # Subsequent attempts should have error feedback
        for i in range(1, min(fail_count + 1, max_retries)):
            assert error_feedbacks[i] is not None
            assert "Error" in error_feedbacks[i]

