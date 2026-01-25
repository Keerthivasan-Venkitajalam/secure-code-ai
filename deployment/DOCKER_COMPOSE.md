# Docker Compose Local Testing Guide

This guide explains how to use Docker Compose for local development and testing of SecureCodeAI.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- (Optional) NVIDIA Docker runtime for GPU support

## Quick Start

### 1. Build and Start the Service

```bash
cd deployment
docker-compose up --build
```

This will:
- Build the Docker image with the latest code
- Start the SecureCodeAI API server on port 8000
- Mount local code directories for development
- Create a persistent volume for model weights

### 2. Verify Service is Running

Wait for the health check to pass (may take 1-2 minutes on first start):

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f secureai-api

# Test health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "vllm_loaded": true,
  "workflow_ready": true,
  "uptime_seconds": 45.2
}
```

### 3. Test the API

Send a test analysis request:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import sqlite3\ndef get_user(user_id):\n    conn = sqlite3.connect(\"db.sqlite\")\n    cursor = conn.cursor()\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor.execute(query)\n    return cursor.fetchone()",
    "file_path": "test.py",
    "max_iterations": 3
  }'
```

### 4. Stop the Service

```bash
docker-compose down
```

To also remove the model volume:
```bash
docker-compose down -v
```

## Configuration

### Environment Variables

Environment variables can be customized in the `docker-compose.yml` file or by creating a `.env` file:

```bash
cp .env.example .env
# Edit .env with your settings
```

Key configuration options:

- `SECUREAI_MODEL_PATH`: Path to model weights inside container
- `SECUREAI_MODEL_NAME`: HuggingFace model identifier
- `SECUREAI_ENABLE_GPU`: Enable GPU acceleration (requires NVIDIA runtime)
- `SECUREAI_LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `SECUREAI_MAX_ITERATIONS`: Maximum patch refinement iterations

### GPU Support

To enable GPU acceleration:

1. Install NVIDIA Docker runtime:
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

2. Update `docker-compose.yml`:
   - Set `GPU: "true"` in build args
   - Set `SECUREAI_ENABLE_GPU=true` in environment
   - Uncomment the `deploy.resources` section

3. Rebuild and start:
   ```bash
   docker-compose up --build
   ```

## Development Workflow

### Hot Reload

The docker-compose configuration mounts local code directories as read-only volumes:
- `../api:/app/api:ro`
- `../agent:/app/agent:ro`

To enable hot reload during development:

1. Remove `:ro` (read-only) flags from volume mounts in `docker-compose.yml`
2. Restart the service:
   ```bash
   docker-compose restart secureai-api
   ```

### Viewing Logs

```bash
# Follow logs in real-time
docker-compose logs -f secureai-api

# View last 100 lines
docker-compose logs --tail=100 secureai-api

# View logs with timestamps
docker-compose logs -t secureai-api
```

### Accessing the Container

```bash
# Open a shell in the running container
docker-compose exec secureai-api bash

# Run a command in the container
docker-compose exec secureai-api python -c "from api.config import config; print(config.model_path)"
```

## Troubleshooting

### Service Won't Start

1. Check logs for errors:
   ```bash
   docker-compose logs secureai-api
   ```

2. Verify Docker resources:
   ```bash
   docker system df
   docker system prune  # Clean up if needed
   ```

3. Rebuild from scratch:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up
   ```

### Model Download Issues

If the model fails to download on first start:

1. Check internet connectivity
2. Verify HuggingFace model name is correct
3. For private models, set HuggingFace token:
   ```bash
   export HF_TOKEN=your_token_here
   docker-compose up
   ```

### Health Check Failing

The health check may fail during initial startup while the model loads. Wait 1-2 minutes and check again:

```bash
# Check health endpoint directly
curl http://localhost:8000/health

# Check readiness
curl http://localhost:8000/health/ready
```

### Port Already in Use

If port 8000 is already in use, change it in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Map to different host port
```

## API Documentation

Once the service is running, access interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run integration tests against the Docker container:

```bash
# From the project root
cd ..
pytest tests/test_docker_integration.py -v
```

## Production Deployment

This docker-compose configuration is for local development and testing only. For production deployment:

- Use the standalone Dockerfile with proper build arguments
- Deploy to RunPod Serverless or similar GPU infrastructure
- Configure proper secrets management
- Enable HTTPS/TLS
- Set up monitoring and alerting

See `DOCKER_SETUP.md` for production deployment instructions.
