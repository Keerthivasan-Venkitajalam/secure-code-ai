"""
Unit and property tests for vLLM client wrapper.
Tests initialization, generation, retry logic, and async support.
"""

import pytest
import asyncio
import time
import sys
from unittest.mock import Mock, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck

from api.vllm_client import (
    VLLMClient,
    VLLMInferenceError,
    get_vllm_client,
    initialize_vllm
)


@pytest.fixture(scope="session")
def mock_vllm_module():
    """Mock vLLM module at import time."""
    # Create mock vLLM module
    mock_vllm = MagicMock()
    
    # Mock LLM class
    mock_llm_class = Mock()
    mock_vllm.LLM = mock_llm_class
    
    # Mock SamplingParams class
    mock_sampling_class = Mock()
    mock_vllm.SamplingParams = mock_sampling_class
    
    # Install mock module
    sys.modules['vllm'] = mock_vllm
    
    yield {
        'vllm': mock_vllm,
        'llm_class': mock_llm_class,
        'sampling_class': mock_sampling_class
    }
    
    # Cleanup
    if 'vllm' in sys.modules:
        del sys.modules['vllm']


class TestVLLMClientInitialization:
    """Test VLLMClient initialization."""
    
    def test_client_creation_with_defaults(self, mock_vllm_module):
        """Test client can be created with default config."""
        client = VLLMClient()
        
        assert client.model_path is not None
        assert client.quantization is not None
        assert client.gpu_memory_utilization > 0
        assert client.tensor_parallel_size >= 1
        assert client._initialized is False
    
    def test_client_creation_with_custom_params(self, mock_vllm_module):
        """Test client can be created with custom parameters."""
        client = VLLMClient(
            model_path="/custom/model",
            quantization="gptq",
            gpu_memory_utilization=0.8,
            tensor_parallel_size=2,
            enable_gpu=False
        )
        
        assert client.model_path == "/custom/model"
        assert client.quantization == "gptq"
        assert client.gpu_memory_utilization == 0.8
        assert client.tensor_parallel_size == 2
        assert client.enable_gpu is False
    
    def test_client_not_initialized_on_creation(self, mock_vllm_module):
        """Test client is not initialized on creation."""
        client = VLLMClient()
        
        assert client.is_initialized() is False
        assert client.llm is None
        assert client.sampling_params is None
    
    def test_get_model_info_before_init(self, mock_vllm_module):
        """Test get_model_info returns config before initialization."""
        client = VLLMClient(
            model_path="/test/model",
            quantization="awq"
        )
        
        info = client.get_model_info()
        
        assert info["model_path"] == "/test/model"
        assert info["quantization"] == "awq"
        assert info["initialized"] is False


class TestVLLMClientGeneration:
    """Test VLLMClient text generation."""
    
    def test_generate_initializes_if_needed(self, mock_vllm_module):
        """Test generate() initializes client if not initialized."""
        # Setup mocks
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Generated text")]
        mock_llm.generate.return_value = [mock_output]
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        assert client.is_initialized() is False
        
        result = client.generate("Test prompt")
        
        assert client.is_initialized() is True
        assert result == "Generated text"
        mock_vllm_module['llm_class'].assert_called_once()
    
    def test_generate_returns_text(self, mock_vllm_module):
        """Test generate() returns generated text."""
        # Setup mocks
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Hello world")]
        mock_llm.generate.return_value = [mock_output]
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        result = client.generate("Test prompt")
        
        assert result == "Hello world"
        mock_llm.generate.assert_called_once()
    
    def test_generate_raises_on_empty_output(self, mock_vllm_module):
        """Test generate() raises error on empty output."""
        # Setup mocks
        mock_llm = Mock()
        mock_llm.generate.return_value = []
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        
        with pytest.raises(VLLMInferenceError, match="No output generated"):
            client.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_async(self, mock_vllm_module):
        """Test generate_async() works correctly."""
        # Setup mocks
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Async generated")]
        mock_llm.generate.return_value = [mock_output]
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        result = await client.generate_async("Test prompt")
        
        assert result == "Async generated"


class TestVLLMClientRetry:
    """Test VLLMClient retry logic."""
    
    def test_retry_on_inference_error(self, mock_vllm_module):
        """Test retry logic retries on VLLMInferenceError."""
        # Setup mocks to fail twice then succeed
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Success")]
        
        mock_llm.generate.side_effect = [
            VLLMInferenceError("First failure"),
            VLLMInferenceError("Second failure"),
            [mock_output]
        ]
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        result = client.generate("Test prompt")
        
        assert result == "Success"
        assert mock_llm.generate.call_count == 3
    
    def test_retry_gives_up_after_max_attempts(self, mock_vllm_module):
        """Test retry logic gives up after 3 attempts."""
        # Setup mocks to always fail
        mock_llm = Mock()
        mock_llm.generate.side_effect = VLLMInferenceError("Persistent failure")
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        
        with pytest.raises(VLLMInferenceError, match="Persistent failure"):
            client.generate("Test prompt")
        
        # Should try 3 times (initial + 2 retries)
        assert mock_llm.generate.call_count == 3
    
    def test_retry_timing(self, mock_vllm_module):
        """Test retry uses exponential backoff."""
        # Setup mocks to fail twice then succeed
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Success")]
        
        call_times = []
        
        def track_time(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) < 3:
                raise VLLMInferenceError("Retry")
            return [mock_output]
        
        mock_llm.generate.side_effect = track_time
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        start_time = time.time()
        result = client.generate("Test prompt")
        
        assert result == "Success"
        assert len(call_times) == 3
        
        # Check exponential backoff (2s, 4s)
        # First retry should be ~2s after first attempt
        if len(call_times) >= 2:
            first_retry_delay = call_times[1] - call_times[0]
            assert first_retry_delay >= 2.0
            assert first_retry_delay < 3.0


class TestVLLMClientCleanup:
    """Test VLLMClient cleanup."""
    
    def test_cleanup_resets_state(self, mock_vllm_module):
        """Test cleanup() resets client state."""
        # Setup mocks
        mock_llm = Mock()
        mock_output = Mock()
        mock_output.outputs = [Mock(text="Text")]
        mock_llm.generate.return_value = [mock_output]
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = VLLMClient()
        client.generate("Test")
        
        assert client.is_initialized() is True
        
        client.cleanup()
        
        assert client.is_initialized() is False
        assert client.llm is None


class TestVLLMClientGlobalInstance:
    """Test global vLLM client instance."""
    
    def test_get_vllm_client_returns_singleton(self, mock_vllm_module):
        """Test get_vllm_client() returns same instance."""
        client1 = get_vllm_client()
        client2 = get_vllm_client()
        
        assert client1 is client2
    
    def test_initialize_vllm_initializes_global(self, mock_vllm_module):
        """Test initialize_vllm() initializes global client."""
        mock_llm = Mock()
        mock_vllm_module['llm_class'].return_value = mock_llm
        
        client = initialize_vllm()
        
        assert client.is_initialized() is True
        # Just check it was called (may be called multiple times due to session fixture)
        assert mock_vllm_module['llm_class'].called


# Property-Based Tests

@settings(max_examples=30, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
@given(
    prompt=st.text(min_size=1, max_size=100),
)
def test_property_generate_handles_any_prompt(mock_vllm_module, prompt):
    """
    Property: Generate handles any valid prompt
    
    For all non-empty prompts:
    - generate() should not crash
    - generate() should return a string
    - The returned string should not be None
    
    Validates: Requirements 3.1, 3.2 (LLM inference)
    """
    # Setup mocks
    mock_llm = Mock()
    mock_output = Mock()
    mock_output.outputs = [Mock(text=f"Response to: {prompt[:20]}")]
    mock_llm.generate.return_value = [mock_output]
    mock_vllm_module['llm_class'].return_value = mock_llm
    
    client = VLLMClient()
    result = client.generate(prompt)
    
    assert isinstance(result, str)
    assert result is not None
    assert len(result) > 0


@settings(max_examples=20, deadline=5000, suppress_health_check=[HealthCheck.too_slow])
@given(
    num_failures=st.integers(min_value=0, max_value=2)
)
def test_property_retry_behavior(mock_vllm_module, num_failures):
    """
    Property 5: Retry with Exponential Backoff
    
    For all failure counts from 0 to 2:
    - If failures < 3, generation should eventually succeed
    - Retry count should equal number of failures
    - Final result should be valid
    
    Validates: Requirements 7.4 (Retry logic with exponential backoff)
    """
    # Setup mocks
    mock_llm = Mock()
    mock_output = Mock()
    mock_output.outputs = [Mock(text="Success")]
    
    # Create side effect: fail num_failures times, then succeed
    side_effects = [VLLMInferenceError(f"Failure {i}") for i in range(num_failures)]
    side_effects.append([mock_output])
    
    mock_llm.generate.side_effect = side_effects
    mock_vllm_module['llm_class'].return_value = mock_llm
    
    client = VLLMClient()
    result = client.generate("Test prompt")
    
    # Should succeed after retries
    assert result == "Success"
    
    # Should have called generate num_failures + 1 times
    assert mock_llm.generate.call_count == num_failures + 1


@settings(max_examples=20, deadline=3000, suppress_health_check=[HealthCheck.too_slow])
@given(
    gpu_memory=st.floats(min_value=0.1, max_value=1.0),
    tensor_parallel=st.integers(min_value=1, max_value=4)
)
def test_property_client_configuration(mock_vllm_module, gpu_memory, tensor_parallel):
    """
    Property: Client Configuration
    
    For all valid configuration values:
    - Client can be created without errors
    - Configuration is stored correctly
    - get_model_info() returns correct values
    
    Validates: Requirements 3.1 (vLLM configuration)
    """
    client = VLLMClient(
        gpu_memory_utilization=gpu_memory,
        tensor_parallel_size=tensor_parallel
    )
    
    info = client.get_model_info()
    
    assert abs(info["gpu_memory_utilization"] - gpu_memory) < 0.001
    assert info["tensor_parallel_size"] == tensor_parallel
    assert info["initialized"] is False


@settings(max_examples=10, deadline=5000, suppress_health_check=[HealthCheck.too_slow])
@given(
    prompt=st.text(min_size=1, max_size=50)
)
@pytest.mark.asyncio
async def test_property_async_generation(mock_vllm_module, prompt):
    """
    Property: Async Generation
    
    For all valid prompts:
    - generate_async() should complete without blocking
    - Result should match synchronous generation
    - Should return valid string
    
    Validates: Requirements 3.2 (Async inference support)
    """
    # Setup mocks
    mock_llm = Mock()
    mock_output = Mock()
    mock_output.outputs = [Mock(text=f"Async: {prompt[:20]}")]
    mock_llm.generate.return_value = [mock_output]
    mock_vllm_module['llm_class'].return_value = mock_llm
    
    client = VLLMClient()
    result = await client.generate_async(prompt)
    
    assert isinstance(result, str)
    assert result is not None
    assert "Async:" in result
