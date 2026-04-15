# Multi-LLM Architecture

SecureCodeAI supports four LLM backends through a common orchestrator interface.

## Backend Selection Order

The backend is selected in this order at runtime (see `api/orchestrator.py`):

1. Ollama (`SECUREAI_USE_OLLAMA=true`)
2. Gemini (`SECUREAI_USE_GEMINI=true`)
3. Local GGUF (`SECUREAI_USE_LOCAL_LLM=true`)
4. vLLM (fallback)

If the selected backend fails to initialize, the workflow continues in degraded mode without LLM-assisted reasoning.

## Backends

### 1. Ollama (`api/ollama_client.py`)

Use when you want local inference with simple setup.

- Model config: `SECUREAI_OLLAMA_MODEL`
- Server URL: `SECUREAI_OLLAMA_URL`
- Default URL: `http://localhost:11434`

Example:

```bash
set SECUREAI_USE_OLLAMA=true
set SECUREAI_OLLAMA_MODEL=phi:latest
set SECUREAI_OLLAMA_URL=http://localhost:11434
python -m api.server
```

### 2. Gemini (`api/gemini_client.py`)

Use for managed cloud inference.

- Enable: `SECUREAI_USE_GEMINI=true`
- Key: `SECUREAI_GEMINI_API_KEY`

Example:

```bash
set SECUREAI_USE_OLLAMA=false
set SECUREAI_USE_GEMINI=true
set SECUREAI_GEMINI_API_KEY=your_key
python -m api.server
```

### 3. Local GGUF (`api/local_llm_client.py`)

Use for offline CPU/GPU local model execution.

- Enable: `SECUREAI_USE_LOCAL_LLM=true`
- Model path: `SECUREAI_MODEL_PATH`

Example:

```bash
set SECUREAI_USE_OLLAMA=false
set SECUREAI_USE_GEMINI=false
set SECUREAI_USE_LOCAL_LLM=true
set SECUREAI_MODEL_PATH=models/deepseek-q2/DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf
python -m api.server
```

### 4. vLLM (`api/vllm_client.py`)

Use for Linux GPU deployments and higher throughput.

- Fallback when other backends are disabled
- GPU control: `SECUREAI_ENABLE_GPU`, `SECUREAI_GPU_MEMORY_UTILIZATION`, `SECUREAI_TENSOR_PARALLEL_SIZE`

Example:

```bash
set SECUREAI_USE_OLLAMA=false
set SECUREAI_USE_GEMINI=false
set SECUREAI_USE_LOCAL_LLM=false
set SECUREAI_ENABLE_GPU=true
python -m api.server
```

## Capability Notes

- Scanner, Speculator, and Patcher use the selected LLM backend.
- SymBot does symbolic execution and does not require LLM inference.
- All backends expose the same generation shape to the agent layer.

## Related Docs

- [README.md](README.md)
- [api/README.md](api/README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SETUP.md](SETUP.md)
