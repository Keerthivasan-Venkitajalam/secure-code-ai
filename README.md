# SecureCodeAI

Local vulnerability detection using DeepSeek-Coder-V2-Lite-Instruct. Analyzes Python code for SQL injection, command injection, and path traversal vulnerabilities.

## Features

- Runs locally via Ollama (6GB model, no cloud API)
- DeepSeek-Coder-V2-Lite-Instruct (16B parameters, 2.4B active)
- Works on 16GB RAM laptops
- Detects common security vulnerabilities

## Installation

Requires: 16GB RAM, Python 3.10+, Ollama

```bash
git clone https://github.com/Keerthivasan-Venkitajalam/secure-code-ai.git
cd secure-code-ai

conda create -n software-env python=3.10 -y
conda activate software-env
pip install requests

# Download model (6GB) from HuggingFace
huggingface-cli download bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF \
  --include "DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf" \
  --local-dir models/deepseek-q2

# Build Ollama model
cd models/deepseek-q2
ollama create deepseek-coder-v2-lite-instruct -f Modelfile
cd ../..

# Test
python poc/llm_poc.py
```

## Usage

```bash
# Default example
python poc/llm_poc.py

# Analyze file
python poc/llm_poc.py --file examples/vulnerable_command_injection.py

# Analyze code
python poc/llm_poc.py --code "exec('rm -rf /' + user_input)"
```

## Example Output

```
VULNERABILITY ANALYSIS:
1. Vulnerable line(s): query = f"SELECT * FROM users WHERE username='{username}'"
2. Vulnerability type: SQL Injection
3. Exploit scenario: Attacker inputs '; DROP TABLE users; -- to execute arbitrary SQL
4. Mitigation: Use parameterized queries
```

## Project Structure

```
poc/llm_poc.py              # Main analyzer
examples/                    # Vulnerable code samples
models/deepseek-q2/         # Model config
scripts/                     # Utilities
```

## Modelfile Config

```
FROM ./DeepSeek-Coder-V2-Lite-Instruct-Q2_K.gguf
PARAMETER num_ctx 1024
PARAMETER num_gpu 0         # Set to 20 for GPU
PARAMETER num_thread 4
PARAMETER temperature 0.2
```

## Supported Vulnerabilities

- SQL Injection
- Command Injection  
- Path Traversal

## Troubleshooting

**"unable to allocate CPU buffer"** - Close memory-heavy apps or use Q2_K quantization

**Ollama connection error** - Run `ollama serve`

**Slow inference** - Enable GPU by setting `num_gpu 20` in Modelfile

## License

MIT
