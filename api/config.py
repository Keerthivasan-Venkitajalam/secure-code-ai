"""
SecureCodeAI - Configuration Management
Environment-based configuration using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class APIConfig(BaseSettings):
    """API configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SECUREAI_",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Model Configuration
    model_path: str = Field(
        default="models/deepseek-q2/DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf",
        description="Path to model weights (GGUF or vLLM)"
    )
    use_local_llm: bool = Field(
        default=False,
        description="Use local GGUF model with llama.cpp instead of vLLM"
    )
    use_gemini: bool = Field(
        default=False,
        description="Use Google Gemini API for inference"
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API Key"
    )
    model_quantization: str = Field(
        default="awq",
        description="Model quantization method (awq, gptq, none)"
    )
    gpu_memory_utilization: float = Field(
        default=0.9,
        ge=0.1,
        le=1.0,
        description="GPU memory utilization (0.1 to 1.0)"
    )
    tensor_parallel_size: int = Field(
        default=1,
        ge=1,
        description="Number of GPUs for tensor parallelism"
    )
    
    # Workflow Configuration
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum patch refinement iterations"
    )
    symbot_timeout: int = Field(
        default=30,
        ge=10,
        le=300,
        description="Symbolic execution timeout in seconds"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    
    # Feature Flags
    enable_docs: bool = Field(
        default=True,
        description="Enable API documentation endpoints (/docs, /redoc)"
    )
    enable_gpu: bool = Field(
        default=True,
        description="Enable GPU acceleration for vLLM"
    )
    
    # Rate Limiting
    rate_limit_requests: int = Field(
        default=1000,
        ge=1,
        description="Maximum requests per minute per client"
    )


# Global configuration instance
config = APIConfig()
