## DeepSeek Model Size Options for Your 16GB RAM Laptop

Your laptop (i9-13900H, RTX 4060 8GB, 16GB RAM) can run DeepSeek, but needs the right quantization:

| Quantization | Model Size | RAM Usage* | Quality | Status |
|--------------|-----------|-----------|---------|--------|
| Q4_K_M | 10.4 GB | ~11-12 GB | High | ❌ Too large (OOM) |
| **Q3_K_M** | **8.1 GB** | **~9-10 GB** | **Medium-High** | **✅ Downloading** |
| Q2_K | 5.9 GB | ~6-7 GB | Medium | ✅ Best fit |

*RAM usage includes model + Ollama overhead + Windows (2-3GB)

### Current Action
Downloading Q3_K_M (8.1 GB) - will work but may be tight on 16GB RAM.

### Recommended: Q2_K for Stability
If Q3 still has memory issues, download Q2:

```powershell
cd "C:\Users\keert\Downloads\Software Engineering\secure-code-ai\models"
huggingface-cli download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF `
  --include "DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf" `
  --local-dir "deepseek-q2"
```

### After Download
1. Create Modelfile in the download folder:
```
FROM ./DeepSeek-Coder-V2-Lite-Instruct-Q3_K_M.gguf
TEMPLATE "{{ .Prompt }}"
PARAMETER num_ctx 512
PARAMETER num_gpu 0
PARAMETER temperature 0.2
```

2. Build:
```powershell
cd deepseek-q3
ollama create deepseek-coder-q3 -f Modelfile
```

3. Update `poc/llm_poc.py` to use `deepseek-coder-q3`

### GPU Acceleration (Optional)
Your RTX 4060 has 8GB VRAM. You can offload layers to GPU:
- Change `PARAMETER num_gpu 0` to `PARAMETER num_gpu 20` (loads ~20 layers on GPU)
- This will speed up inference significantly
