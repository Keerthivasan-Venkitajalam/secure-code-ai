# Setup Guide

## Requirements

- 16GB RAM (6GB+ free)
- Python 3.10+
- Ollama
- 10GB disk space

## Install

### 1. Get Prerequisites

**Windows:** Download [Conda](https://docs.conda.io/en/latest/miniconda.html) and [Ollama](https://ollama.com/download)

**Linux:**
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install --cask miniconda
brew install ollama
```

### 2. Setup Project

```bash
git clone https://github.com/Keerthivasan-Venkitajalam/secure-code-ai.git
cd secure-code-ai

conda create -n software-env python=3.10 -y
conda activate software-env
pip install requests
```

### 3. Download Model

Pick one based on your RAM:

| Quantization | Size | Free RAM Needed |
|-------------|------|-----------------|
| Q4_K_M | 10.4 GB | 12GB+ |
| Q3_K_M | 8.13 GB | 10GB+ |
| Q2_K | 5.99 GB | 8GB+ (recommended) |

```bash
pip install huggingface-hub

# Q2_K (recommended for 16GB systems)
huggingface-cli download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF \
  --include "DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf" \
  --local-dir models/deepseek-q2
```

Or download manually from [HuggingFace](https://huggingface.co/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF)

### 4. Build Model

```bash
cd models/deepseek-q2
ollama create deepseek-coder-v2-lite-instruct -f Modelfile
ollama list  # verify
cd ../..
```

### 5. Test

```bash
python poc/llm_poc.py
```

Should see vulnerability analysis output.

## GPU Acceleration (Optional)

If you have NVIDIA GPU:

```bash
nvidia-smi  # check GPU

# Edit models/deepseek-q2/Modelfile
# Change: PARAMETER num_gpu 0 → PARAMETER num_gpu 20

cd models/deepseek-q2
ollama create deepseek-coder-v2-lite-instruct -f Modelfile
cd ../..
```

## Common Issues

**"unable to allocate CPU buffer"**
- Close Chrome/Edge and other apps
- Use Q2_K instead of Q4/Q3
- Check free RAM: `Get-CimInstance Win32_OperatingSystem` (Windows) or `free -h` (Linux)

**"Model not found"**
```bash
ollama list
cd models/deepseek-q2
ollama create deepseek-coder-v2-lite-instruct -f Modelfile
```

**"Connection refused"**
```bash
ollama serve
```

**Slow performance**
- Enable GPU (see above)
- Reduce context in Modelfile: `PARAMETER num_ctx 512`
