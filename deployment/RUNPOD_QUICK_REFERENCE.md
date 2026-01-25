# RunPod Deployment Quick Reference

Quick commands and references for deploying and managing SecureCodeAI on RunPod Serverless.

## Prerequisites

```bash
# Install RunPod CLI
pip install runpod

# Configure API key
runpod config

# Login to Docker registry
docker login docker.io
```

## Deployment Commands

### Full Deployment (One Command)

```bash
cd scripts
./deploy_runpod.sh --registry docker.io/username --tag v1.0.0
```

### Step-by-Step Deployment

```bash
# 1. Build GPU image
cd deployment
./build.sh --gpu --tag v1.0.0

# 2. Tag and push
docker tag secureai:v1.0.0 docker.io/username/secureai:v1.0.0
docker push docker.io/username/secureai:v1.0.0

# 3. Deploy to RunPod
runpod deploy --config deployment/runpod.yaml --environment production

# 4. Get endpoint URL
runpod endpoint list
```

### Deploy Existing Image

```bash
./deploy_runpod.sh \
  --registry docker.io/username \
  --tag v1.0.0 \
  --skip-build
```

### Build and Push Only (No Deploy)

```bash
./deploy_runpod.sh \
  --registry docker.io/username \
  --tag v1.0.0 \
  --skip-deploy
```

## Testing Commands

### Quick Test (5 minutes)

```bash
cd scripts
./test_runpod_deployment.sh --endpoint https://xxx.runpod.io
```

### Full Test Suite (15+ minutes)

```bash
./test_runpod_deployment.sh \
  --endpoint https://xxx.runpod.io \
  --test-cold-start \
  --test-scale-to-zero \
  --verbose
```

### Manual Health Check

```bash
# Basic health
curl https://xxx.runpod.io/health

# Readiness check
curl https://xxx.runpod.io/health/ready
```

### Test Analysis Endpoint

```bash
curl -X POST https://xxx.runpod.io/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import sqlite3\ndef get_user(user_id):\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    return query",
    "file_path": "test.py",
    "max_iterations": 3
  }'
```

## Management Commands

### View Logs

```bash
# Stream logs
runpod logs --follow

# Last 100 lines
runpod logs --tail 100
```

### Check Status

```bash
# Endpoint status
runpod endpoint status

# List all endpoints
runpod endpoint list

# Get metrics
runpod metrics --endpoint your-endpoint-id
```

### Update Deployment

```bash
# Deploy new version
./deploy_runpod.sh --registry docker.io/username --tag v1.1.0

# Rollback to previous version
./deploy_runpod.sh --registry docker.io/username --tag v1.0.0 --skip-build
```

### Delete Deployment

```bash
runpod endpoint delete your-endpoint-id
```

## Configuration Files

| File | Purpose |
|------|---------|
| `deployment/runpod.yaml` | RunPod Serverless configuration |
| `deployment/Dockerfile` | Container image definition |
| `scripts/deploy_runpod.sh` | Deployment automation script |
| `scripts/test_runpod_deployment.sh` | Test automation script |

## Environment Variables

Key environment variables in `runpod.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECUREAI_MODEL_PATH` | `/runpod-volume/models/...` | Model weights path |
| `SECUREAI_ENABLE_GPU` | `true` | Enable GPU acceleration |
| `SECUREAI_GPU_MEMORY_UTILIZATION` | `0.9` | GPU memory usage |
| `SECUREAI_MAX_ITERATIONS` | `3` | Max patch refinement |
| `SECUREAI_LOG_LEVEL` | `INFO` | Logging level |
| `SECUREAI_ENABLE_DOCS` | `false` | API docs (disabled in prod) |

## Scaling Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `minReplicas` | `0` | Scale to zero when idle |
| `maxReplicas` | `10` | Max concurrent instances |
| `idleTimeout` | `300` | 5 minutes before scale-to-zero |
| `coldStartTimeout` | `30` | 30 seconds cold start limit |
| `targetConcurrency` | `1` | One request per instance |

## Resource Allocation

| Resource | Specification |
|----------|---------------|
| GPU | NVIDIA RTX A5000 (24GB VRAM) |
| CPU | 8 cores |
| Memory | 32GB RAM |
| Storage | 50GB persistent volume |

## Common Issues

| Issue | Solution |
|-------|----------|
| Cold start timeout | Increase `coldStartTimeout` in `runpod.yaml` |
| Out of memory | Reduce `SECUREAI_GPU_MEMORY_UTILIZATION` to 0.8 |
| Health check fails | Wait 60s for initialization |
| Model not found | Check `SECUREAI_MODEL_PATH` is correct |
| 503 errors | Instance not ready, wait for readiness check |

## Cost Estimates

Approximate RunPod Serverless costs:
- **GPU Time**: $0.50-0.70/hour (RTX A5000)
- **Storage**: $0.10/GB/month (50GB = $5/month)
- **Idle Time**: $0 (scale to zero)

Example: 1000 requests/month @ 30s each = ~8 hours = $5-6/month + storage

## Documentation Links

- **Deployment Guide**: [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md)
- **Test Plan**: [RUNPOD_TEST_PLAN.md](RUNPOD_TEST_PLAN.md)
- **Implementation Summary**: [RUNPOD_IMPLEMENTATION_SUMMARY.md](RUNPOD_IMPLEMENTATION_SUMMARY.md)
- **RunPod Docs**: https://docs.runpod.io/

## Support

- **RunPod Discord**: https://discord.gg/runpod
- **RunPod Support**: https://www.runpod.io/support
- **GitHub Issues**: https://github.com/yourusername/secure-code-ai/issues

