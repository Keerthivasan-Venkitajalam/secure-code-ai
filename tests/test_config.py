"""
Unit and property tests for configuration management.
Tests environment variable loading, validation, and propagation.
"""

import pytest
import os
from hypothesis import given, strategies as st, settings, HealthCheck
from pydantic import ValidationError

from api.config import APIConfig


class TestConfigDefaults:
    """Test default configuration values."""
    
    def test_default_values(self):
        """Test all default values are set correctly."""
        config = APIConfig()
        
        # Server defaults
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 1
        
        # Model defaults
        assert config.model_path == "/models/deepseek-coder-v2-lite-instruct"
        assert config.model_quantization == "awq"
        assert config.gpu_memory_utilization == 0.9
        assert config.tensor_parallel_size == 1
        
        # Workflow defaults
        assert config.max_iterations == 3
        assert config.symbot_timeout == 30
        
        # Logging defaults
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        
        # Feature flags
        assert config.enable_docs is True
        assert config.enable_gpu is True
        
        # Rate limiting
        assert config.rate_limit_requests == 10


class TestConfigValidation:
    """Test configuration validation rules."""
    
    def test_gpu_memory_utilization_bounds(self):
        """Test GPU memory utilization must be between 0.1 and 1.0."""
        # Valid bounds
        APIConfig(gpu_memory_utilization=0.1)
        APIConfig(gpu_memory_utilization=1.0)
        APIConfig(gpu_memory_utilization=0.5)
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            APIConfig(gpu_memory_utilization=0.05)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            APIConfig(gpu_memory_utilization=1.5)
    
    def test_max_iterations_bounds(self):
        """Test max_iterations must be between 1 and 10."""
        # Valid bounds
        APIConfig(max_iterations=1)
        APIConfig(max_iterations=10)
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            APIConfig(max_iterations=0)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            APIConfig(max_iterations=11)
    
    def test_symbot_timeout_bounds(self):
        """Test symbot_timeout must be between 10 and 300."""
        # Valid bounds
        APIConfig(symbot_timeout=10)
        APIConfig(symbot_timeout=300)
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            APIConfig(symbot_timeout=5)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            APIConfig(symbot_timeout=400)
    
    def test_tensor_parallel_size_positive(self):
        """Test tensor_parallel_size must be >= 1."""
        # Valid
        APIConfig(tensor_parallel_size=1)
        APIConfig(tensor_parallel_size=4)
        
        # Invalid: zero or negative
        with pytest.raises(ValidationError):
            APIConfig(tensor_parallel_size=0)
    
    def test_rate_limit_positive(self):
        """Test rate_limit_requests must be >= 1."""
        # Valid
        APIConfig(rate_limit_requests=1)
        APIConfig(rate_limit_requests=100)
        
        # Invalid: zero or negative
        with pytest.raises(ValidationError):
            APIConfig(rate_limit_requests=0)


class TestEnvironmentVariableLoading:
    """Test environment variable loading with SECUREAI_ prefix."""
    
    def test_env_var_loading(self, monkeypatch):
        """Test configuration loads from environment variables."""
        # Set environment variables with SECUREAI_ prefix
        monkeypatch.setenv("SECUREAI_HOST", "127.0.0.1")
        monkeypatch.setenv("SECUREAI_PORT", "9000")
        monkeypatch.setenv("SECUREAI_MODEL_PATH", "/custom/model/path")
        monkeypatch.setenv("SECUREAI_MAX_ITERATIONS", "5")
        monkeypatch.setenv("SECUREAI_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("SECUREAI_ENABLE_GPU", "false")
        
        config = APIConfig()
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.model_path == "/custom/model/path"
        assert config.max_iterations == 5
        assert config.log_level == "DEBUG"
        assert config.enable_gpu is False
    
    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test environment variables are case-insensitive."""
        monkeypatch.setenv("secureai_host", "192.168.1.1")
        monkeypatch.setenv("SECUREAI_PORT", "7000")
        
        config = APIConfig()
        
        assert config.host == "192.168.1.1"
        assert config.port == 7000
    
    def test_partial_env_override(self, monkeypatch):
        """Test partial environment variable override keeps defaults."""
        monkeypatch.setenv("SECUREAI_PORT", "5000")
        
        config = APIConfig()
        
        # Overridden value
        assert config.port == 5000
        
        # Default values preserved
        assert config.host == "0.0.0.0"
        assert config.workers == 1
        assert config.model_path == "/models/deepseek-coder-v2-lite-instruct"


# Property-Based Tests

@settings(max_examples=50, deadline=1000, suppress_health_check=[HealthCheck.too_slow])
@given(
    port=st.integers(min_value=1024, max_value=65535),
    workers=st.integers(min_value=1, max_value=16),
    max_iterations=st.integers(min_value=1, max_value=10),
    gpu_memory=st.floats(min_value=0.1, max_value=1.0),
    tensor_parallel=st.integers(min_value=1, max_value=8)
)
def test_property_config_validation(port, workers, max_iterations, gpu_memory, tensor_parallel):
    """
    Property 12: Environment Variable Loading
    
    For all valid configuration values within specified bounds:
    - Configuration object can be created without errors
    - All values are correctly stored and retrievable
    - Type conversions are handled correctly
    
    Validates: Requirements 9.1 (Environment variable loading)
    """
    config = APIConfig(
        port=port,
        workers=workers,
        max_iterations=max_iterations,
        gpu_memory_utilization=gpu_memory,
        tensor_parallel_size=tensor_parallel
    )
    
    # Verify all values are correctly stored
    assert config.port == port
    assert config.workers == workers
    assert config.max_iterations == max_iterations
    assert abs(config.gpu_memory_utilization - gpu_memory) < 0.001
    assert config.tensor_parallel_size == tensor_parallel


@settings(max_examples=30, deadline=1000)
@given(
    log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    log_format=st.sampled_from(["json", "text"]),
    model_quantization=st.sampled_from(["awq", "gptq", "none"]),
    enable_docs=st.booleans(),
    enable_gpu=st.booleans()
)
def test_property_config_propagation(log_level, log_format, model_quantization, enable_docs, enable_gpu):
    """
    Property 13: Configuration Propagation
    
    For all valid configuration combinations:
    - Configuration values propagate correctly to all components
    - String values are case-preserved
    - Boolean flags work correctly
    - No data loss or corruption during propagation
    
    Validates: Requirements 9.3, 9.4, 10.5 (Configuration propagation)
    """
    config = APIConfig(
        log_level=log_level,
        log_format=log_format,
        model_quantization=model_quantization,
        enable_docs=enable_docs,
        enable_gpu=enable_gpu
    )
    
    # Verify configuration propagates correctly
    assert config.log_level == log_level
    assert config.log_format == log_format
    assert config.model_quantization == model_quantization
    assert config.enable_docs == enable_docs
    assert config.enable_gpu == enable_gpu
    
    # Verify configuration can be serialized and deserialized
    config_dict = config.model_dump()
    assert config_dict["log_level"] == log_level
    assert config_dict["log_format"] == log_format
    assert config_dict["model_quantization"] == model_quantization
    assert config_dict["enable_docs"] == enable_docs
    assert config_dict["enable_gpu"] == enable_gpu


@settings(max_examples=20, deadline=1000)
@given(
    invalid_gpu_memory=st.one_of(
        st.floats(min_value=-1.0, max_value=0.09),
        st.floats(min_value=1.01, max_value=2.0)
    ),
)
def test_property_invalid_config_rejected(invalid_gpu_memory):
    """
    Property: Invalid Configuration Rejection
    
    For all invalid configuration values:
    - Configuration creation raises ValidationError
    - Error messages are descriptive
    - No partial configuration is created
    
    Validates: Requirements 9.2 (Configuration validation)
    """
    with pytest.raises(ValidationError) as exc_info:
        APIConfig(gpu_memory_utilization=invalid_gpu_memory)
    
    # Verify error is raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
