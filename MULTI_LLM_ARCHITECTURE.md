# Multi-LLM Architecture

SecureCodeAI now supports three different LLM backends, providing flexibility for different deployment scenarios.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer                               │
│  (Scanner, Speculator, SymBot, Patcher)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 agent/llm_client.py                          │
│           (Unified LLM Interface)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬───────────────┐
         ▼                       ▼               ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Gemini Client    │  │  vLLM Client     │  │ Local LLM Client │
│ (Cloud API)      │  │  (Linux GPU)     │  │ (Windows/CPU)    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Backend Comparison

| Feature | Gemini | vLLM | Local LLM |
|---------|--------|------|-----------|
| **Platform** | Cloud | Linux | Windows/Mac/Linux |
| **Hardware** | None | GPU (CUDA) | CPU/GPU |
| **Speed** |  Fast (< 1s) |  Fast (1-2s) |  Slow (5-10s) |
| **Privacy** |  Cloud |  On-premise |  On-premise |
| **Cost** |  API fees |  GPU hosting |  Free |
| **Setup** |  Easy |  Complex |  Easy |
| **Reliability** |  |  |  |

## Implementation Details

### 1. Gemini Client (`api/gemini_client.py`)

**When to use:**
- Production deployments
- Need fast inference
- Don't have GPU infrastructure
- Want latest model capabilities

**Configuration:**
```bash
set SECUREAI_USE_GEMINI=true
set SECUREAI_GEMINI_API_KEY=your_api_key_here
```

**Features:**
- Uses Google Gemini 2.5 Flash model
- Automatic retry with exponential backoff
- Self-correction loop support
- Syntax validation
- Async generation support

**Code example:**
```python
from api.gemini_client import GeminiClient

client = GeminiClient(api_key="your_key")
client.initialize()
response = client.generate("Analyze this code for SQL injection...")
```

### 2. vLLM Client (`api/vllm_client.py`)

**When to use:**
- Self-hosted deployments
- Have GPU infrastructure (Linux)
- Need full data privacy
- High throughput requirements

**Configuration:**
```bash
set SECUREAI_USE_GEMINI=false
set SECUREAI_USE_LOCAL_LLM=false
set SECUREAI_MODEL_PATH=models/deepseek-coder-v2-lite
```

**Features:**
- Optimized GPU inference
- Tensor parallelism support
- Quantization (AWQ, GPTQ)
- High throughput batching

**Requirements:**
- Linux OS
- CUDA-capable GPU (8GB+ VRAM)
- vLLM library

### 3. Local LLM Client (`api/local_llm_client.py`)

**When to use:**
- Development on Windows/Mac
- Offline environments
- Limited GPU resources
- Testing and experimentation

**Configuration:**
```bash
set SECUREAI_USE_GEMINI=false
set SECUREAI_USE_LOCAL_LLM=true
set SECUREAI_MODEL_PATH=models/deepseek-q2/DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf
```

**Features:**
- Cross-platform (Windows/Mac/Linux)
- CPU and GPU support
- GGUF model format
- Two backends: llama-cpp-python (preferred) or ctransformers (fallback)

**Model download:**
```bash
hf download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF \
  --include "DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf" \
  --local-dir models/deepseek-q2
```

## Agent Integration

The `agent/llm_client.py` module provides a unified interface that automatically selects the appropriate backend based on configuration:

```python
from agent.llm_client import LLMClient

# Automatically uses configured backend (Gemini/vLLM/Local)
llm = LLMClient()
response = llm.generate(prompt, max_tokens=2048, temperature=0.2)
```

**Duck typing support:**
- All clients implement `generate()` method
- All clients support `update_params()` for temperature/max_tokens
- All clients support async generation via `generate_async()`
- All clients support self-correction loops

## Configuration Priority

The system selects the LLM backend in this order:

1. **If `SECUREAI_USE_GEMINI=true`** → Use Gemini Client
2. **Else if `SECUREAI_USE_LOCAL_LLM=true`** → Use Local LLM Client
3. **Else** → Use vLLM Client (default)

## Performance Benchmarks

Based on DeepSeek-Coder-V2-Lite model:

| Backend | Scanner Time | Patcher Time | Total E2E |
|---------|--------------|--------------|-----------|
| Gemini | 0.8s | 1.2s | ~3s |
| vLLM (GPU) | 1.5s | 2.0s | ~5s |
| Local (CPU) | 8.0s | 12.0s | ~25s |
| Local (GPU) | 3.0s | 4.5s | ~10s |

*Note: Times are approximate and depend on hardware, model size, and prompt complexity.*

## Migration Guide

### From vLLM to Gemini

```bash
# Before
python -m api.server

# After
set SECUREAI_USE_GEMINI=true
set SECUREAI_GEMINI_API_KEY=your_key
python -m api.server
```

### From vLLM to Local LLM

```bash
# Download GGUF model
hf download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF \
  --include "DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf" \
  --local-dir models/deepseek-q2

# Configure
set SECUREAI_USE_LOCAL_LLM=true
set SECUREAI_MODEL_PATH=models/deepseek-q2/DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf

# Run
python -m api.server
```

## Troubleshooting

### Gemini Client Issues

**Error: "API Key is missing"**
```bash
set SECUREAI_GEMINI_API_KEY=your_actual_key
```

**Error: "google-generativeai not installed"**
```bash
pip install google-generativeai
```

### Local LLM Issues

**Error: "Neither llama-cpp-python nor ctransformers installed"**
```bash
pip install ctransformers
# Or for GPU support:
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

**Error: "Model file not found"**
- Verify model path in config
- Download model using `hf download` command above

### vLLM Issues

**Error: "vLLM not available on Windows"**
- Use Gemini or Local LLM instead
- vLLM only supports Linux

## Best Practices

1. **Production**: Use Gemini for reliability and speed
2. **Development**: Use Local LLM for offline work
3. **Self-hosted**: Use vLLM if you have GPU infrastructure
4. **Testing**: Use Local LLM with small GGUF models (Q2_K quantization)
5. **CI/CD**: Use Gemini to avoid infrastructure complexity

## Future Enhancements

- [ ] Support for OpenAI API
- [ ] Support for Anthropic Claude
- [ ] Support for Azure OpenAI
- [ ] Model caching and warm-up
- [ ] Automatic backend selection based on availability
- [ ] Load balancing across multiple backends
- [ ] Cost tracking and optimization

## Related Documentation

- [LLM_AGENT_ARCHITECTURE.md](LLM_AGENT_ARCHITECTURE.md) - Agent design and prompts
- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture
- [api/README.md](api/README.md) - API module documentation
- [README.md](README.md) - Quick start guide
