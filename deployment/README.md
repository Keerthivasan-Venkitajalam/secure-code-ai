# SecureCodeAI Deployment

This directory contains Docker configuration and deployment scripts for SecureCodeAI.

## Files

- `Dockerfile` - Main application container with CPU/GPU support
- `Dockerfile.vllm` - Standalone vLLM server container (legacy)
- `docker-compose.yml` - Local development setup
- `entrypoint.sh` - Container entrypoint with model download logic
- `build.sh` - Build script with GPU support
- `README.md` - This file

## Building the Container

### CPU-Only Build

```bash
cd deployment
./build.sh --tag v1.0.0
```

Or using docker directly:

```bash
docker build --build-arg GPU=false -t secureai:latest -f deployment/Dockerfile .
```

### GPU-Enabled Build

```bash
cd deployment
./build.sh --gpu --tag v1.0.0
```

Or using docker directly:

```bash
docker build --build-arg GPU=true -t secureai:gpu -f deployment/Dockerfile .
```

### Build Options

The `build.sh` script supports the following options:

- `--gpu` - Enable GPU support (installs CUDA dependencies and vLLM)
- `--tag TAG` - Set image tag (default: latest)
- `--name NAME` - Set image name (default: secureai)
- `--push` - Push image to registry after build
- `--registry URL` - Container registry URL
- `--help` - Show help message

## Running the Container

### CPU Mode

```bash
docker run -p 8000:8000 \
  -v $(pwd)/models:/models \
  -e SECUREAI_ENABLE_GPU=false \
  secureai:latest
```

### GPU Mode

```bash
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/models:/models \
  -e SECUREAI_ENABLE_GPU=true \
  secureai:gpu
```

### Environment Variables

The container supports the following environment variables:

- `SECUREAI_HOST` - API server host (default: 0.0.0.0)
- `SECUREAI_PORT` - API server port (default: 8000)
- `SECUREAI_MODEL_PATH` - Path to model weights (default: /models/deepseek-coder-v2-lite-instruct)
- `SECUREAI_MODEL_NAME` - HuggingFace model name (default: deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct)
- `SECUREAI_ENABLE_GPU` - Enable GPU acceleration (default: true)
- `SECUREAI_LOG_LEVEL` - Logging level (default: INFO)
- `SECUREAI_MAX_ITERATIONS` - Max patch refinement iterations (default: 3)
- `SECUREAI_RATE_LIMIT_REQUESTS` - Rate limit per minute (default: 10)
- `SECUREAI_ENABLE_DOCS` - Enable API docs (default: true)

## Model Download

The container automatically downloads the DeepSeek model from HuggingFace on first run if not found in the `/models` directory.

To use a persistent volume for model caching:

```bash
docker run -p 8000:8000 \
  -v secureai-models:/models \
  secureai:latest
```

To pre-download the model:

```bash
# Create volume
docker volume create secureai-models

# Download model
docker run --rm \
  -v secureai-models:/models \
  -e SECUREAI_MODEL_PATH=/models/deepseek-coder-v2-lite-instruct \
  secureai:latest \
  bash -c "huggingface-cli download deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct --local-dir /models/deepseek-coder-v2-lite-instruct"
```

## Health Checks

The container includes health checks that verify:

- API server is responding
- vLLM engine is loaded (if GPU enabled)
- Workflow orchestrator is ready

Check health status:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Graceful Shutdown

The container handles SIGTERM signals gracefully:

1. Stops accepting new requests
2. Waits for in-flight requests to complete (max 30s)
3. Cleans up vLLM engine resources
4. Exits cleanly

To stop the container gracefully:

```bash
docker stop <container-id>
```

## RunPod Deployment

SecureCodeAI can be deployed to RunPod Serverless for cost-effective, auto-scaling GPU inference.

### Quick Start

```bash
# Deploy to RunPod
cd scripts
./deploy_runpod.sh --registry docker.io/yourusername --tag v1.0.0
```

### Documentation

- **Deployment Guide**: See [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md) for detailed deployment instructions
- **Configuration**: See [runpod.yaml](runpod.yaml) for RunPod Serverless configuration
- **Test Plan**: See [RUNPOD_TEST_PLAN.md](RUNPOD_TEST_PLAN.md) for manual testing procedures

### Key Features

- **Auto-scaling**: Scale to zero after 5 minutes of inactivity
- **Cold Start**: ~30 second startup time from zero
- **GPU**: NVIDIA RTX A5000 (24GB VRAM)
- **Persistent Storage**: 50GB volume for model weights caching
- **Cost Efficiency**: Pay only for active compute time

## Troubleshooting

### Model Download Fails

If model download fails, check:

1. Internet connection is available
2. HuggingFace model name is correct
3. You have access to the model (may require HF token)

Set HuggingFace token:

```bash
docker run -p 8000:8000 \
  -v $(pwd)/models:/models \
  -e HUGGING_FACE_HUB_TOKEN=your_token_here \
  secureai:latest
```

### GPU Not Detected

If GPU is not detected:

1. Ensure NVIDIA drivers are installed on host
2. Ensure nvidia-docker2 is installed
3. Use `--gpus all` flag when running container
4. Check GPU availability: `nvidia-smi`

### Out of Memory

If you encounter OOM errors:

1. Reduce `SECUREAI_GPU_MEMORY_UTILIZATION` (default: 0.9)
2. Use model quantization (AWQ 4-bit is default)
3. Reduce `max_tokens` in vLLM configuration

## Development

For local development with hot-reload:

```bash
docker-compose up
```

This mounts the local code directory and enables auto-reload on code changes.
