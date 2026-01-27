# SecureCodeAI

**Neuro-Symbolic Vulnerability Detection and Patching System**

SecureCodeAI combines Large Language Models (LLMs) with symbolic execution to automatically detect and patch security vulnerabilities in source code. The system uses a multi-agent architecture powered by DeepSeek-Coder-V2-Lite-Instruct and provides both a REST API and command-line interface.

## 🚀 Quick Start - Run Locally (No Cloud Required!)

Get started in 10 minutes with zero cloud costs:

```bash
# 1. Get free Gemini API key from: https://makersuite.google.com/app/apikey

# 2. Configure environment
cd secure-code-ai/deployment
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here

# 3. Start backend (Windows)
cd ..
.\scripts\start_local.ps1

# Or on Linux/Mac
./scripts/start_local.sh

# 4. Install VS Code extension
cd extension
npm install && npm run compile
# Press F5 in VS Code to launch

# 5. Test it!
# Create test.py with vulnerable code and analyze it
```

**📖 Full Guide**: See [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md) for detailed instructions.

## Features

- 🔍 **Automated Vulnerability Detection** - Scans code using Bandit SAST and LLM analysis
- 🔬 **Formal Verification** - Uses symbolic execution (CrossHair) to verify vulnerabilities
- 🔧 **Automated Patching** - Generates and verifies security patches
- 🤖 **Multi-Agent Architecture** - Coordinates Scanner, Speculator, SymBot, and Patcher agents
- 🚀 **High-Performance Inference** - Powered by Google Gemini 2.5 Flash (Cloud) or vLLM/LlamaCpp (Local)
- 🐳 **Docker Containerized** - Easy deployment with Docker and docker-compose
- ☁️ **Serverless Ready** - Optimized for RunPod Serverless deployment
- 📊 **Production-Ready API** - FastAPI with health checks, rate limiting, and monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│              (VS Code Extension, CLI, Web UI)                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (Port 8000)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   /analyze   │  │   /health    │  │    /docs     │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                     │
│         ▼                                                     │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Workflow Orchestrator                     │       │
│  │  (Manages LangGraph execution & state)           │       │
│  └──────────────────┬───────────────────────────────┘       │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Agent Workflow                    │
│  ┌──────────┐  ┌────────────┐  ┌─────────┐  ┌──────────┐  │
│  │ Scanner  │→ │ Speculator │→ │ SymBot  │→ │ Patcher  │  │
│  └────┬─────┘  └─────┬──────┘  └────┬────┘  └────┬─────┘  │
│       │              │               │            │         │
│       └──────────────┴───────────────┴────────────┘         │
│                      │                                       │
│                      ▼                                       │
│              ┌───────────────┐                               │
│              │  vLLM Engine  │                               │
│              │  (DeepSeek)   │                               │
│              └───────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

### LLM-Powered Agents

SecureCodeAI uses intelligent LLM-powered agents that combine semantic understanding with formal verification:

- **Scanner Agent**: Uses AST analysis + LLM to generate vulnerability hypotheses and extract code slices
- **Speculator Agent**: Generates formal security contracts (icontract decorators) from hypotheses
- **SymBot Agent**: Performs symbolic execution using CrossHair to verify contracts
- **Patcher Agent**: Generates secure patches from counterexamples with self-correction loops

## Configuration

SecureCodeAI supports two modes of operation:

### 1. Cloud Mode (Recommended)
Uses Google's Gemini 2.5 Flash model. Fastest and most reliable.

- Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Set `SECUREAI_USE_GEMINI=true`
- Set `SECUREAI_GEMINI_API_KEY=your_key_here`

### 2. Local Mode
Uses local GGUF models (DeepSeek-Coder). Private but slower.

- **Windows**: Uses `ctransformers` or `llama-cpp-python` (CPU/GPU)
- **Linux**: Uses `vLLM` (High-performance GPU)

For detailed information about the LLM agent architecture, prompt templates, self-correction loops, and neuro-slicing algorithm, see [LLM_AGENT_ARCHITECTURE.md](LLM_AGENT_ARCHITECTURE.md).

## Quick Start

### Prerequisites

- **Python 3.10+**
- **16GB RAM minimum** (32GB recommended for local models)
- **8GB RAM minimum** (when using Gemini API)
- **GPU with 24GB VRAM** (optional, for local models)
- **Docker** (recommended for easy setup)

## Installation Options

### Option 1: Local Docker Setup (Recommended) ⭐

**Best for**: Development, testing, no cloud costs

```bash
# 1. Get free Gemini API key
# Visit: https://makersuite.google.com/app/apikey

# 2. Configure
cd secure-code-ai/deployment
cp .env.example .env
# Edit .env: Add GEMINI_API_KEY=your_key

# 3. Start (Windows)
cd ..
.\scripts\start_local.ps1

# Or Linux/Mac
./scripts/start_local.sh

# 4. Verify
curl http://localhost:8000/health
```

**📖 Full Guide**: [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md)

### Option 2: Cloud Deployment (RunPod)

**Best for**: Production, team sharing, 24/7 availability

```bash
# See deployment guides:
# - deployment/RUNPOD_ACCOUNT_SETUP.md
# - deployment/RUNPOD_DEPLOYMENT.md
```

**Cost**: $12-40/month depending on usage

### Option 3: Manual Python Setup

**Best for**: Development without Docker

```bash
# Clone repository
git clone https://github.com/Keerthivasan-Venkitajalam/secure-code-ai.git
cd secure-code-ai

# Create virtual environment
conda create -n secureai python=3.10 -y
conda activate secureai

# Install dependencies
pip install -r requirements.txt

# Set up Gemini
export GEMINI_API_KEY=your_key_here
export LLM_BACKEND=gemini

# Start server
python -m api.server
```

## VS Code Extension Setup

```bash
cd secure-code-ai/extension
npm install
npm run compile

# Option A: Development mode (F5 in VS Code)
# Option B: Install as VSIX
npm install -g @vscode/vsce
vsce package
code --install-extension securecodai-0.1.0.vsix
```

**Configure in VS Code Settings:**
```json
{
  "securecodai.apiEndpoint": "http://localhost:8000"
}
```

**📖 Extension Guide**: [extension/LOCAL_DEVELOPMENT.md](extension/LOCAL_DEVELOPMENT.md)

## Using the API

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-27T12:00:00Z"
}
```
```

#### Analyze Code

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "query = \"SELECT * FROM users WHERE username='\'' + username + '\''\"",
    "file_path": "app.py",
    "max_iterations": 3
  }'
```

Response:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "vulnerabilities": [
    {
      "location": "line 1",
      "vuln_type": "SQL Injection",
      "severity": "high",
      "description": "User input concatenated directly into SQL query",
      "confidence": 0.95
    }
  ],
  "patches": [
    {
      "code": "query = \"SELECT * FROM users WHERE username = ?\"",
      "diff": "- query = \"SELECT * FROM users WHERE username='\" + username + \"'\"\n+ query = \"SELECT * FROM users WHERE username = ?\"",
      "verified": true
    }
  ],
  "execution_time": 2.34,
  "errors": [],
  "logs": [],
  "workflow_complete": true
}
```

#### Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## Configuration

### Environment Variables

All configuration can be set via environment variables with the `SECUREAI_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECUREAI_HOST` | `0.0.0.0` | API server host |
| `SECUREAI_PORT` | `8000` | API server port |
| `SECUREAI_WORKERS` | `1` | Number of worker processes |
| `SECUREAI_MODEL_PATH` | `/models/deepseek-coder-v2-lite-instruct` | Path to model weights |
| `SECUREAI_MODEL_QUANTIZATION` | `awq` | Model quantization (awq, gptq, none) |
| `SECUREAI_GPU_MEMORY_UTILIZATION` | `0.9` | GPU memory utilization (0.0-1.0) |
| `SECUREAI_MAX_ITERATIONS` | `3` | Max patch refinement iterations |
| `SECUREAI_SYMBOT_TIMEOUT` | `30` | Symbolic execution timeout (seconds) |
| `SECUREAI_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SECUREAI_LOG_FORMAT` | `json` | Log format (json, text) |
| `SECUREAI_ENABLE_DOCS` | `true` | Enable /docs and /redoc endpoints |
| `SECUREAI_ENABLE_GPU` | `true` | Enable GPU acceleration |
| `SECUREAI_RATE_LIMIT` | `10` | Rate limit (requests per minute) |
| `SECUREAI_TENSOR_PARALLEL_SIZE` | `1` | Number of GPUs for tensor parallelism |

### Configuration File

Create a `.env` file in the project root:

```bash
# .env
SECUREAI_HOST=0.0.0.0
SECUREAI_PORT=8000
SECUREAI_MODEL_PATH=/models/deepseek-coder-v2-lite-instruct
SECUREAI_ENABLE_GPU=true
SECUREAI_LOG_LEVEL=INFO
SECUREAI_MAX_ITERATIONS=3
SECUREAI_RATE_LIMIT=10
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Copy environment template
cp deployment/.env.example deployment/.env

# Edit configuration
nano deployment/.env

# Start services
cd deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Building Docker Image

```bash
# CPU-only build
cd deployment
./build.sh

# GPU build
./build.sh --gpu

# Or manually
docker build -t secureai:latest -f deployment/Dockerfile .
```

### Running Docker Container

```bash
# Run with default settings
docker run -p 8000:8000 secureai:latest

# Run with GPU
docker run --gpus all -p 8000:8000 secureai:latest

# Run with custom configuration
docker run -p 8000:8000 \
  -e SECUREAI_LOG_LEVEL=DEBUG \
  -e SECUREAI_MAX_ITERATIONS=5 \
  -v $(pwd)/models:/models \
  secureai:latest
```

## RunPod Serverless Deployment

SecureCodeAI is optimized for deployment on RunPod Serverless with auto-scaling and scale-to-zero capabilities.

### Prerequisites

1. **RunPod Account:** Sign up at [runpod.io](https://runpod.io)
2. **RunPod CLI:** Install with `pip install runpod`
3. **Docker Registry:** Push image to Docker Hub or private registry

### Deployment Steps

```bash
# 1. Build and push Docker image
cd deployment
./build.sh --gpu
docker tag secureai:latest your-registry/secureai:latest
docker push your-registry/secureai:latest

# 2. Deploy to RunPod
./scripts/deploy_runpod.sh

# 3. Test deployment
curl https://your-endpoint.runpod.io/health
```

### RunPod Configuration

The deployment uses the following configuration (see `deployment/runpod.yaml`):

- **GPU:** 24GB VRAM minimum (A5000, A6000, or RTX 4090)
- **Auto-scaling:** Scale to zero after 5 minutes idle
- **Cold-start:** ~30 seconds (model loaded from persistent volume)
- **Persistent Volume:** Model weights cached for fast startup

For detailed deployment instructions, see [deployment/RUNPOD_DEPLOYMENT.md](deployment/RUNPOD_DEPLOYMENT.md).

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/test_analyze_integration.py

# Run property-based tests
pytest -m property
```

### Load Testing

```bash
# Install Locust
pip install locust

# Run load test
./scripts/run_load_test.sh

# Or manually
locust -f tests/load_test.py --host=http://localhost:8000
```

See [LOAD_TESTING.md](LOAD_TESTING.md) for detailed load testing guide.

### Code Quality

```bash
# Format code
black api/ tests/

# Sort imports
isort api/ tests/

# Type checking
mypy api/

# Linting
ruff check api/ tests/
```

## Project Structure

```
secure-code-ai/
├── api/                          # FastAPI application
│   ├── server.py                 # Main API server
│   ├── config.py                 # Configuration management
│   ├── models.py                 # Pydantic models
│   ├── orchestrator.py           # Workflow orchestrator
│   ├── vllm_client.py            # vLLM inference client
│   ├── logging_config.py         # Logging configuration
│   └── shutdown.py               # Graceful shutdown handler
├── agent/                        # Agent implementations
│   ├── scanner.py                # Scanner agent (Bandit)
│   ├── speculator.py             # Speculator agent (LLM)
│   ├── symbot.py                 # SymBot agent (CrossHair)
│   └── patcher.py                # Patcher agent (LLM)
├── deployment/                   # Deployment configurations
│   ├── Dockerfile                # Docker image definition
│   ├── docker-compose.yml        # Docker Compose config
│   ├── runpod.yaml               # RunPod configuration
│   ├── entrypoint.sh             # Container entrypoint
│   └── .env.example              # Environment template
├── tests/                        # Test suite
│   ├── test_analyze_integration.py
│   ├── test_concurrency.py
│   ├── test_config.py
│   ├── test_health.py
│   ├── test_orchestrator.py
│   ├── test_vllm_client.py
│   └── load_test.py              # Locust load tests
├── scripts/                      # Utility scripts
│   ├── deploy_runpod.sh          # RunPod deployment
│   ├── run_load_test.sh          # Load testing
│   └── run_full_test_suite.py    # Test runner
├── examples/                     # Example vulnerable code
├── models/                       # Model weights (gitignored)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Supported Vulnerabilities

- **SQL Injection** - Detects unsafe SQL query construction
- **Command Injection** - Identifies unsafe system command execution
- **Path Traversal** - Finds directory traversal vulnerabilities
- **XSS (Cross-Site Scripting)** - Detects unescaped user input in HTML
- **Hardcoded Credentials** - Identifies embedded secrets
- **Insecure Deserialization** - Finds unsafe pickle/yaml usage
- **SSRF (Server-Side Request Forgery)** - Detects unvalidated URL requests

## API Endpoints

### Core Endpoints

- `POST /analyze` - Analyze code for vulnerabilities
- `GET /health` - Health check endpoint
- `GET /health/ready` - Readiness check endpoint
- `GET /` - API information

### Documentation Endpoints

- `GET /docs` - Interactive Swagger UI
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI schema

## Performance

### Benchmarks

- **Throughput:** > 1 request/second for `/analyze` endpoint
- **Latency (p50):** < 2 seconds
- **Latency (p95):** < 5 seconds
- **Latency (p99):** < 10 seconds
- **Success Rate:** > 95%

### Resource Requirements

| Deployment | CPU | RAM | GPU | Disk |
|------------|-----|-----|-----|------|
| Development | 4 cores | 16GB | Optional | 20GB |
| Production | 8 cores | 32GB | 24GB VRAM | 50GB |
| RunPod Serverless | Auto | Auto | 24GB VRAM | 50GB |

## Troubleshooting

### Common Issues

**"vLLM engine not loaded"**
- Ensure model weights are downloaded
- Check `SECUREAI_MODEL_PATH` points to correct directory
- Verify GPU is available if `SECUREAI_ENABLE_GPU=true`

**"Connection refused on port 8000"**
- Check if server is running: `curl http://localhost:8000/health`
- Verify port is not in use: `lsof -i :8000` (Linux/Mac)
- Check firewall settings

**"Out of memory"**
- Reduce `SECUREAI_GPU_MEMORY_UTILIZATION` (default: 0.9)
- Use CPU mode: `SECUREAI_ENABLE_GPU=false`
- Close other applications

**"Rate limit exceeded (429)"**
- Increase rate limit: `SECUREAI_RATE_LIMIT=20`
- Wait before retrying
- Implement exponential backoff in client

### Logs

View logs for debugging:

```bash
# Docker logs
docker logs secureai-api

# Docker Compose logs
docker-compose logs -f

# Local server logs
# Logs are written to stdout in JSON format
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Format code (`black . && isort .`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use SecureCodeAI in your research, please cite:

```bibtex
@software{securecodai2024,
  title={SecureCodeAI: Neuro-Symbolic Vulnerability Detection and Patching},
  author={Venkitajalam, Keerthivasan},
  year={2024},
  url={https://github.com/Keerthivasan-Venkitajalam/secure-code-ai}
}
```

## Acknowledgments

- **DeepSeek-Coder-V2-Lite** - Base LLM model
- **vLLM** - High-performance inference engine
- **LangGraph** - Agent workflow orchestration
- **CrossHair** - Symbolic execution engine
- **Bandit** - Python SAST tool
- **FastAPI** - Modern web framework

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/discussions)

## Roadmap

- [ ] Support for more programming languages (JavaScript, Java, Go)
- [ ] VS Code extension
- [ ] Web UI dashboard
- [ ] Integration with CI/CD pipelines
- [ ] Custom vulnerability rules
- [ ] Multi-file analysis
- [ ] Incremental analysis
- [ ] Vulnerability database integration

---

**Built with ❤️ for secure software development**
