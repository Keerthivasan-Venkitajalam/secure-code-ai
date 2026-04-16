"""
SecureCodeAI - Configuration Management
Environment-based configuration using Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
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
    use_ollama: bool = Field(
        default=True,
        description="Use local Ollama for inference"
    )
    ollama_model: str = Field(
        default="phi:latest",
        description="Ollama model name"
    )
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
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
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated CORS origins. Use '*' to allow all origins"
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
    enable_api_auth: bool = Field(
        default=False,
        description="Require API key authentication for analysis endpoints"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key used for request authentication when auth is enabled"
    )
    
    # Semantic Scanning Configuration
    enable_semantic_scanning: bool = Field(
        default=True,
        description="Enable semantic bug detection using RAG"
    )
    knowledge_base_path: str = Field(
        default="data/knowledge_base/samples.csv",
        description="Path to knowledge base CSV file"
    )
    embedding_model_name: str = Field(
        default="BAAI/bge-base-en-v1.5",
        description="Name of the embedding model"
    )
    embedding_model_path: Optional[str] = Field(
        default=None,
        description="Local path to embedding model (None = download from HuggingFace)"
    )
    vector_store_path: str = Field(
        default="data/vector_store",
        description="Path to vector store directory"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic matches (0.0 to 1.0)"
    )
    top_k_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of semantic search results"
    )
    enable_hardware_validation: bool = Field(
        default=True,
        description="Enable hardware constraint validation"
    )
    enable_lifecycle_validation: bool = Field(
        default=True,
        description="Enable lifecycle ordering validation"
    )
    enable_api_typo_detection: bool = Field(
        default=True,
        description="Enable API typo detection"
    )
    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for embedding generation"
    )
    vector_store_max_memory_mb: int = Field(
        default=2048,
        ge=256,
        le=16384,
        description="Maximum memory usage for vector store in MB"
    )
    semantic_scan_timeout: float = Field(
        default=2.0,
        ge=0.1,
        le=30.0,
        description="Timeout for semantic scan operations in seconds"
    )
    vector_store_hnsw_ef: int = Field(
        default=100,
        ge=10,
        le=500,
        description="HNSW search_ef parameter (higher = better recall, slower search)"
    )
    embedding_cache_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum number of embeddings to cache"
    )
    
    @field_validator('knowledge_base_path', 'vector_store_path')
    @classmethod
    def validate_paths(cls, v: str) -> str:
        """Validate that paths are not empty."""
        if not v or not v.strip():
            raise ValueError("Path cannot be empty")
        return v
    
    @field_validator('similarity_threshold')
    @classmethod
    def validate_similarity_threshold(cls, v: float) -> float:
        """Validate similarity threshold is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v


# Global configuration instance
config = APIConfig()
