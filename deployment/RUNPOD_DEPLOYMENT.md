# RunPod Serverless Deployment Guide

This guide covers deploying SecureCodeAI to RunPod Serverless for cost-effective, auto-scaling GPU inference.

## Overview

RunPod Serverless provides:
- **GPU Access**: NVIDIA RTX A5000 (24GB VRAM) for model inference
- **Auto-scaling**: Scale to zero after 5 minutes of inactivity
- **Cold Start**: ~30 second startup time from zero
- **Cost Efficiency**: Pay only for active compute time
- **Persistent Storage**: 50GB volume for model weights caching

## Prerequisites

### 1. Install RunPod CLI

```bash
pip install runpod
```

### 2. Configure RunPod API Key

Get your API key from [RunPod Dashboard](https://www.runpod.io/console/user/settings) and configure:

```bash
runpod config
# Enter your API key when prompted
```

### 3. Container Registry Access

You need access to a container registry (Docker Hub, GitHub Container Registry, etc.):

```bash
# Docker Hub example
docker login docker.io
```

### 4. Build GPU-Enabled Image

The deployment requires a GPU-enabled Docker image:

```bash
cd deployment
./build.sh --gpu --tag v1.0.0
```

## Deployment Steps

### Quick Deployment

Deploy with a single command:

```bash
cd scripts
./deploy_runpod.sh --registry docker.io/yourusername --tag v1.0.0
```

This will:
1. Build the GPU-enabled Docker image
2. Push the image to your registry
3. Deploy to RunPod Serverless
4. Verify the deployment health

### Step-by-Step Deployment

#### 1. Build and Push Image

```bash
# Build GPU image
cd deployment
./build.sh --gpu --tag v1.0.0 --name secureai

# Tag for registry
docker tag secureai:v1.0.0 docker.io/yourusername/secureai:v1.0.0

# Push to registry
docker push docker.io/yourusername/secureai:v1.0.0
```

#### 2. Update RunPod Configuration

Edit `deployment/runpod.yaml` and update the image URL:

```yaml
container:
  image: docker.io/yourusername/secureai:v1.0.0
```

#### 3. Deploy to RunPod

```bash
runpod deploy --config deployment/runpod.yaml --environment production
```

#### 4. Verify Deployment

```bash
# Get endpoint URL
runpod endpoint list

# Check health
curl https://your-endpoint-url.runpod.io/health

# Check readiness
curl https://your-endpoint-url.runpod.io/health/ready
```

## Configuration

### Environment Variables

The RunPod deployment uses these environment variables (configured in `runpod.yaml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECUREAI_HOST` | `0.0.0.0` | API server host |
| `SECUREAI_PORT` | `8000` | API server port |
| `SECUREAI_MODEL_PATH` | `/runpod-volume/models/...` | Model weights path |
| `SECUREAI_ENABLE_GPU` | `true` | Enable GPU acceleration |
| `SECUREAI_GPU_MEMORY_UTILIZATION` | `0.9` | GPU memory usage (0.1-1.0) |
| `SECUREAI_LOG_LEVEL` | `INFO` | Logging level |
| `SECUREAI_MAX_ITERATIONS` | `3` | Max patch refinement loops |
| `SECUREAI_RATE_LIMIT_REQUESTS` | `10` | Requests per minute limit |
| `SECUREAI_ENABLE_DOCS` | `false` | Enable API docs (disabled in prod) |

### Scaling Configuration

Auto-scaling settings in `runpod.yaml`:

```yaml
scaling:
  minReplicas: 0          # Scale to zero when idle
  maxReplicas: 10         # Max concurrent instances
  idleTimeout: 300        # 5 minutes idle before scale-to-zero
  coldStartTimeout: 30    # 30 seconds cold start timeout
  targetConcurrency: 1    # One request per instance
```

### Resource Allocation

GPU and compute resources:

```yaml
container:
  gpu:
    type: NVIDIA_RTX_A5000  # 24GB VRAM
    count: 1
  resources:
    cpu: 8
    memory: 32Gi
```

### Persistent Volume

Model weights are cached in a persistent volume:

```yaml
volumes:
  - name: model-cache
    mountPath: /runpod-volume
    size: 50Gi
```

## Testing the Deployment

### Health Check

```bash
# Basic health check
curl https://your-endpoint.runpod.io/health

# Expected response:
{
  "status": "healthy",
  "vllm_loaded": true,
  "workflow_ready": true,
  "uptime_seconds": 123.45
}
```

### Readiness Check

```bash
# Component readiness check
curl https://your-endpoint.runpod.io/health/ready

# Expected response:
{
  "ready": true,
  "components": {
    "api_server": true,
    "vllm_engine": true,
    "agent_workflow": true
  }
}
```

### Analysis Request

```bash
# Test vulnerability analysis
curl -X POST https://your-endpoint.runpod.io/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import sqlite3\ndef get_user(user_id):\n    conn = sqlite3.connect(\"db.sqlite\")\n    cursor = conn.cursor()\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor.execute(query)\n    return cursor.fetchone()",
    "file_path": "app.py",
    "max_iterations": 3
  }'
```

## Monitoring

### View Logs

```bash
# Stream logs
runpod logs --follow

# View recent logs
runpod logs --tail 100
```

### Check Metrics

```bash
# Endpoint status
runpod endpoint status

# List all endpoints
runpod endpoint list

# Get detailed metrics
runpod metrics --endpoint your-endpoint-id
```

### RunPod Dashboard

Monitor your deployment in the [RunPod Dashboard](https://www.runpod.io/console):
- Request count and latency
- GPU utilization
- Memory usage
- Error rates
- Cost tracking

## Scaling Behavior

### Scale to Zero

After 5 minutes of inactivity:
1. RunPod stops the container
2. GPU resources are released
3. No charges incurred while idle
4. Persistent volume retains model weights

### Cold Start

When a request arrives after scale-to-zero:
1. RunPod starts a new container (~10s)
2. Container loads model from persistent volume (~20s)
3. Total cold start: ~30 seconds
4. Subsequent requests are fast (no cold start)

### Auto-Scaling

Under load:
1. RunPod creates additional instances (up to maxReplicas)
2. Each instance handles one concurrent request
3. Load balancing across instances
4. Instances scale down when load decreases

## Cost Optimization

### Estimated Costs

RunPod Serverless pricing (approximate):
- **GPU Time**: $0.50-0.70/hour (RTX A5000)
- **Storage**: $0.10/GB/month (persistent volume)
- **Idle Time**: $0 (scale to zero)

Example monthly cost:
- 1000 requests/month
- 30 seconds per request
- Total GPU time: ~8.3 hours
- Cost: ~$5-6/month + storage

### Cost Reduction Tips

1. **Optimize Cold Start**: Pre-download models to persistent volume
2. **Batch Requests**: Process multiple files in one request
3. **Adjust Idle Timeout**: Increase if you have regular traffic patterns
4. **Use Spot Instances**: Enable in `runpod.yaml` for 50% savings (with interruption risk)
5. **Monitor Usage**: Track metrics to identify optimization opportunities

## Troubleshooting

### Cold Start Timeout

If cold start exceeds 30 seconds:

1. **Check Model Download**: Ensure model is cached in persistent volume
2. **Increase Timeout**: Update `coldStartTimeout` in `runpod.yaml`
3. **Optimize Image**: Reduce image size, pre-install dependencies

### Out of Memory

If you encounter OOM errors:

1. **Reduce GPU Memory**: Lower `SECUREAI_GPU_MEMORY_UTILIZATION` to 0.8
2. **Use Quantization**: Ensure AWQ 4-bit quantization is enabled
3. **Upgrade GPU**: Use RTX A6000 (48GB) or A100 (80GB)

### Health Check Failures

If health checks fail:

1. **Check Logs**: `runpod logs --tail 100`
2. **Verify Model Path**: Ensure `SECUREAI_MODEL_PATH` is correct
3. **Increase Delay**: Update `initialDelaySeconds` in `runpod.yaml`
4. **Test Locally**: Run container locally to debug

### Deployment Fails

If deployment fails:

1. **Verify Image**: Ensure image is pushed to registry and accessible
2. **Check API Key**: Verify RunPod API key is configured
3. **Review Config**: Validate `runpod.yaml` syntax
4. **Check Quota**: Ensure you have available GPU quota

## Updating the Deployment

### Deploy New Version

```bash
# Build new version
cd deployment
./build.sh --gpu --tag v1.1.0

# Deploy update
cd ../scripts
./deploy_runpod.sh --registry docker.io/yourusername --tag v1.1.0
```

### Rollback

```bash
# Deploy previous version
./deploy_runpod.sh --registry docker.io/yourusername --tag v1.0.0 --skip-build
```

### Zero-Downtime Updates

RunPod supports rolling updates:
1. Deploy new version
2. RunPod gradually shifts traffic to new instances
3. Old instances drain and terminate
4. No downtime during update

## Security

### API Key Management

- Store RunPod API key securely (use environment variables)
- Rotate keys regularly
- Use separate keys for staging/production

### Network Security

- RunPod provides HTTPS by default
- Configure CORS in `runpod.yaml`
- Use API authentication (add to your application)

### Container Security

- Use minimal base images
- Scan images for vulnerabilities
- Keep dependencies updated
- Disable API docs in production (`SECUREAI_ENABLE_DOCS=false`)

## Support

### RunPod Resources

- [RunPod Documentation](https://docs.runpod.io/)
- [RunPod Discord](https://discord.gg/runpod)
- [RunPod Support](https://www.runpod.io/support)

### SecureCodeAI Resources

- [GitHub Repository](https://github.com/yourusername/secure-code-ai)
- [Issue Tracker](https://github.com/yourusername/secure-code-ai/issues)
- [Documentation](../README.md)

