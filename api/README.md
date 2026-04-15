# SecureCodeAI API Module

This module provides the FastAPI backend for SecureCodeAI with multiple LLM backend options.

## LLM Client Architecture

SecureCodeAI supports three LLM backends for maximum flexibility:

### 1. Gemini Client (`gemini_client.py`) - **Recommended**
- **Use Case**: Production deployments, fastest inference
- **Provider**: Google Gemini 2.5 Flash API
- **Advantages**: 
  - Cloud-based, no local GPU required
  - Fast inference (<1s typical)
  - Latest model capabilities
  - Reliable and scalable
- **Configuration**:
  ```bash
  set SECUREAI_USE_GEMINI=true
  set SECUREAI_GEMINI_API_KEY=your_api_key
  ```

### 2. vLLM Client (`vllm_client.py`) - **Linux GPU**
- **Use Case**: Self-hosted deployments with GPU
- **Provider**: vLLM engine with DeepSeek-Coder-V2-Lite
- **Advantages**:
  - High-performance GPU inference
  - Full data privacy (on-premise)
  - Optimized for throughput
- **Requirements**: Linux, CUDA-capable GPU
- **Configuration**:
  ```bash
  set SECUREAI_USE_GEMINI=false
  set SECUREAI_USE_LOCAL_LLM=false
  ```

### 3. Local LLM Client (`local_llm_client.py`) - **Windows/CPU**
- **Use Case**: Development, offline environments, Windows
- **Provider**: llama-cpp-python or ctransformers with GGUF models
- **Advantages**:
  - Works on Windows/Mac/Linux
  - CPU or GPU support
  - Fully offline
  - Lower memory requirements
- **Configuration**:
  ```bash
  set SECUREAI_USE_GEMINI=false
  set SECUREAI_USE_LOCAL_LLM=true
  set SECUREAI_MODEL_PATH=models/deepseek-q2/DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf
  ```

## Module Files

- `server.py` - FastAPI application with endpoints
- `models.py` - Pydantic models for request/response validation
- `config.py` - Environment-based configuration management
- `orchestrator.py` - Multi-agent workflow orchestration
- `logging_config.py` - Structured logging configuration
- `shutdown.py` - Graceful shutdown handling
- `gemini_client.py` - Google Gemini API client
- `vllm_client.py` - vLLM inference engine client
- `local_llm_client.py` - Local GGUF model client

## Quick Start

```bash
# Cloud mode (recommended)
set SECUREAI_USE_GEMINI=true
set SECUREAI_GEMINI_API_KEY=your_key
python -m api.server

# Local GPU mode (Linux)
python -m api.server

# Local CPU mode (Windows)
set SECUREAI_USE_LOCAL_LLM=true
python -m api.server
```

## API Endpoints

- `POST /analyze` - Analyze code for vulnerabilities
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

See [ARCHITECTURE.md](../ARCHITECTURE.md) for detailed system design.
