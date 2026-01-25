# Docker Container Setup - Implementation Summary

## Overview

Task 12 "Create Docker container" has been successfully implemented. The SecureCodeAI application is now fully containerized with support for both CPU and GPU deployment, automatic model downloading, and graceful shutdown handling.

## What Was Implemented

### 1. Dockerfile (`deployment/Dockerfile`)

A production-ready Dockerfile that:
- Uses Python 3.10-slim as the base image
- Supports GPU acceleration via `--build-arg GPU=true`
- Installs all system dependencies (git, curl, build-essential)
- Installs Python dependencies from requirements.txt
- Installs GPU-specific packages (vLLM, flash-attn) when GPU enabled
- Copies application code (api/, agent/)
- Exposes port 8000 for the FastAPI server
- Includes health checks for monitoring
- Uses a custom entrypoint script for initialization

**Requirements Validated:** 5.1, 5.3, 5.5, 9.5

### 2. Entrypoint Script (`deployment/entrypoint.sh`)

A bash script that handles:
- **Model Download Logic**: Automatically downloads DeepSeek model from HuggingFace if not found in `/models` directory
- **Persistent Volume Support**: Checks for cached models in mounted volumes
- **GPU Detection**: Detects NVIDIA GPU availability and configures accordingly
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals properly
- **Configuration Display**: Shows startup configuration for debugging
- **Error Handling**: Provides clear error messages if model download fails

**Requirements Validated:** 5.2, 5.4

### 3. Build Script (`deployment/build.sh`)

A convenience script for building Docker images with options:
- `--gpu`: Enable GPU support
- `--tag TAG`: Set image tag
- `--name NAME`: Set image name
- `--push`: Push to container registry
- `--registry URL`: Specify registry URL
- `--help`: Show usage information

### 4. Graceful Shutdown Handler (`api/shutdown.py`)

A Python module that:
- Registers signal handlers for SIGTERM and SIGINT
- Executes cleanup callbacks on shutdown
- Ensures vLLM engine is properly cleaned up
- Ensures workflow orchestrator resources are released
- Prevents resource leaks during container termination

**Requirements Validated:** 5.4

### 5. Integration Tests (`tests/test_docker_integration.py`)

Comprehensive integration tests that verify:
- Docker image builds successfully
- Container starts and becomes healthy
- Health check endpoints work correctly
- API endpoints validate requests properly
- Graceful shutdown with SIGTERM works
- Port 8000 is properly exposed
- Container logs contain expected messages

**Requirements Validated:** 5.1, 5.2, 5.3, 5.4

### 6. Documentation (`deployment/README.md`)

Complete documentation covering:
- Building CPU and GPU images
- Running containers with proper configuration
- Environment variable reference
- Model download and caching
- Health checks and monitoring
- Graceful shutdown behavior
- RunPod deployment instructions
- Troubleshooting guide

## Quick Start

### Build the Container

**CPU-only:**
```bash
cd secure-code-ai/deployment
./build.sh --tag v1.0.0
```

**With GPU support:**
```bash
cd secure-code-ai/deployment
./build.sh --gpu --tag v1.0.0
```

### Run the Container

**CPU mode:**
```bash
docker run -p 8000:8000 \
  -v $(pwd)/models:/models \
  -e SECUREAI_ENABLE_GPU=false \
  secureai:v1.0.0
```

**GPU mode:**
```bash
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/models:/models \
  -e SECUREAI_ENABLE_GPU=true \
  secureai:v1.0.0
```

### Test the Container

```bash
# Run integration tests
python -m pytest secure-code-ai/tests/test_docker_integration.py -v

# Check health
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/health/ready

# Test analysis endpoint
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def add(a, b): return a + b", "file_path": "test.py"}'
```

## Key Features

### 1. Automatic Model Download

The container automatically downloads the DeepSeek-Coder-V2-Lite-Instruct model from HuggingFace on first run. The model is cached in the `/models` directory, which can be mounted as a persistent volume to avoid re-downloading on container restart.

### 2. GPU Support

GPU support is enabled via build argument:
- `--build-arg GPU=false`: CPU-only build (smaller image)
- `--build-arg GPU=true`: GPU-enabled build (includes CUDA, vLLM, flash-attn)

At runtime, GPU usage is controlled by the `SECUREAI_ENABLE_GPU` environment variable.

### 3. Graceful Shutdown

The container handles shutdown signals properly:
1. Receives SIGTERM from Docker/Kubernetes
2. Stops accepting new requests
3. Waits for in-flight requests to complete (max 30s)
4. Cleans up vLLM engine resources
5. Exits cleanly with code 0

### 4. Health Monitoring

Two health check endpoints:
- `/health`: Overall service health status
- `/health/ready`: Component-level readiness checks

Docker health checks run every 30 seconds with a 60-second startup grace period.

### 5. Configuration via Environment Variables

All configuration is done via environment variables with the `SECUREAI_` prefix:
- `SECUREAI_HOST`: API server host (default: 0.0.0.0)
- `SECUREAI_PORT`: API server port (default: 8000)
- `SECUREAI_MODEL_PATH`: Path to model weights
- `SECUREAI_ENABLE_GPU`: Enable GPU acceleration
- `SECUREAI_LOG_LEVEL`: Logging level
- And more (see deployment/README.md)

## Testing

The integration tests verify all requirements:

```bash
# Run all Docker integration tests
python -m pytest secure-code-ai/tests/test_docker_integration.py -v

# Run specific test
python -m pytest secure-code-ai/tests/test_docker_integration.py::TestDockerIntegration::test_graceful_shutdown -v
```

**Note:** Full integration tests require Docker to be installed and running. Tests will be skipped if Docker is not available.

## Files Created/Modified

### New Files:
- `deployment/Dockerfile` - Main application container
- `deployment/entrypoint.sh` - Container entrypoint with model download
- `deployment/build.sh` - Build script with GPU support
- `deployment/README.md` - Deployment documentation
- `deployment/DOCKER_SETUP.md` - This file
- `api/shutdown.py` - Graceful shutdown handler
- `tests/test_docker_integration.py` - Integration tests

### Modified Files:
- `api/server.py` - Added signal handler registration

## Next Steps

The Docker container is now ready for:

1. **Local Testing**: Use docker-compose for development (Task 13)
2. **RunPod Deployment**: Deploy to RunPod Serverless (Task 14)
3. **Production Use**: Deploy to any container orchestration platform

## Requirements Coverage

This implementation satisfies the following requirements from the design document:

- **Requirement 5.1**: Docker container includes all dependencies ✓
- **Requirement 5.2**: Model download from HuggingFace or persistent volume ✓
- **Requirement 5.3**: Port 8000 exposed for HTTP traffic ✓
- **Requirement 5.4**: Graceful shutdown on SIGTERM ✓
- **Requirement 5.5**: GPU support via build argument ✓
- **Requirement 9.5**: GPU configuration via environment variable ✓

## Troubleshooting

### Model Download Fails

If the model download fails:
1. Check internet connectivity
2. Verify HuggingFace model name is correct
3. Set HuggingFace token if model requires authentication:
   ```bash
   docker run -e HUGGING_FACE_HUB_TOKEN=your_token secureai:v1.0.0
   ```

### GPU Not Detected

If GPU is not detected:
1. Ensure NVIDIA drivers are installed on host
2. Install nvidia-docker2: `sudo apt-get install nvidia-docker2`
3. Restart Docker daemon: `sudo systemctl restart docker`
4. Use `--gpus all` flag when running container

### Container Exits Immediately

Check container logs:
```bash
docker logs <container-id>
```

Common issues:
- Model download failed (check internet connection)
- Port 8000 already in use (use different port: `-p 8001:8000`)
- Insufficient memory (increase Docker memory limit)

## Support

For issues or questions:
1. Check the deployment/README.md for detailed documentation
2. Review container logs: `docker logs <container-id>`
3. Run integration tests to verify setup
4. Check the requirements and design documents in `.kiro/specs/backend-api-deployment/`
