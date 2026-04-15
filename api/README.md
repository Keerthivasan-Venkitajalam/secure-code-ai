# SecureCodeAI API Module

This module provides the FastAPI backend for analysis, semantic search, and knowledge-base stats.

## Key Files

- `server.py`: FastAPI app and endpoints
- `models.py`: Request/response models
- `config.py`: Environment-based configuration
- `orchestrator.py`: Workflow and backend initialization
- `ollama_client.py`: Ollama backend client
- `gemini_client.py`: Gemini backend client
- `local_llm_client.py`: Local GGUF backend client
- `vllm_client.py`: vLLM backend client

## API Endpoints

- `POST /analyze`: vulnerability analysis and patch generation
- `POST /search_similar`: semantic search against pattern knowledge base
- `GET /knowledge_base/stats`: knowledge-base counts and categories
- `GET /health`: liveness/health
- `GET /health/ready`: readiness
- `GET /docs`, `GET /redoc`: API docs (when enabled)

## LLM Backends

The orchestrator initializes backends in priority order:

1. Ollama (`SECUREAI_USE_OLLAMA`)
2. Gemini (`SECUREAI_USE_GEMINI`)
3. Local GGUF (`SECUREAI_USE_LOCAL_LLM`)
4. vLLM fallback

## Semantic Scanning Configuration

These settings are defined in `api/config.py`:

- `SECUREAI_ENABLE_SEMANTIC_SCANNING`
- `SECUREAI_KNOWLEDGE_BASE_PATH`
- `SECUREAI_EMBEDDING_MODEL_NAME`
- `SECUREAI_EMBEDDING_MODEL_PATH`
- `SECUREAI_VECTOR_STORE_PATH`
- `SECUREAI_SIMILARITY_THRESHOLD`
- `SECUREAI_TOP_K_RESULTS`
- `SECUREAI_ENABLE_HARDWARE_VALIDATION`
- `SECUREAI_ENABLE_LIFECYCLE_VALIDATION`
- `SECUREAI_ENABLE_API_TYPO_DETECTION`
- `SECUREAI_EMBEDDING_BATCH_SIZE`
- `SECUREAI_VECTOR_STORE_MAX_MEMORY_MB`
- `SECUREAI_SEMANTIC_SCAN_TIMEOUT`
- `SECUREAI_VECTOR_STORE_HNSW_EF`
- `SECUREAI_EMBEDDING_CACHE_SIZE`

## Quick Start

```bash
pip install -r requirements.txt
python -m api.server
```

For local configuration, copy `deployment/.env.example` to `deployment/.env` and set values for your environment.

## Related Docs

- [README.md](../README.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [SEMANTIC_SCANNING_GUIDE.md](../SEMANTIC_SCANNING_GUIDE.md)
- [KNOWLEDGE_BASE_MANAGEMENT.md](../KNOWLEDGE_BASE_MANAGEMENT.md)
