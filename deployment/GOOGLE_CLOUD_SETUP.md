# Google Cloud Vertex AI Setup Guide

This guide shows you how to use Google Cloud Vertex AI with SecureCodeAI instead of the Gemini API key.

## What is Vertex AI?

Vertex AI is Google Cloud's enterprise AI platform that provides access to Gemini models with:
- Higher rate limits than free Gemini API
- Better reliability and SLA
- Enterprise features (audit logs, VPC, etc.)
- Pay-as-you-go pricing

## Prerequisites

- Google Cloud Project: `inquinion-code`
- Service Account credentials (provided)
- Docker installed

## Quick Setup

### Step 1: Save Service Account Credentials

Create the credentials file:

```bash
cd secure-code-ai/deployment
mkdir -p secrets
```

Create `secrets/inquinion-code-801c22313fa5.json` with this content:

```json
{
  "type": "service_account",
  "project_id": "inquinion-code",
  "private_key_id": "801c22313fa5faf67a6dac20cd5eac2d1bac69c9",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCpS8DkuZ8EyDNY\nf0W4uh/hnUioB39tDdF4eLPTzywllGhA+WM0kZH1KDKlurI4Uc4UxE6VLzD7d+wY\n+xKk60kALLk8TlfxS0dHmZt+XkGtUHmZWH3cjtODV7+VYKYD2yWsnE5+Oi2cDGyd\nAiFd4vND0ub7JuZWaty1HAQ9k5pMfb8aIRN9RAShygmD8jK7CUKVNgTH0DZo2wsi\nfysKjgW/b7mh98NTAIFYzulC5dZjdtEOgHQpDUzvrwdd+MZVQeVDhdLAwDq5kO6H\nN8CmbxsAVqZxu1P1eR1AT5itEaBzxPPYll0pitYA8teuaOmiA629i8p7da3kDuwi\nbmADmboDAgMBAAECggEAC31AS7Ar55ItUeMz+HPBOCQ0IHB/KF0uCxlTSEZLaQgn\nrx59qhKlr4KZNVV0mjfgXtkXutjSCoQ6pKiyvOMu4sZ7kmkqtLh2z5gld6+ukLQ2\ncb68rpw5ed9u+Wnuulzus0aEWTKvkmM8InJY5gXsm9ITVOtwlGAk4bGouVkWuVFu\n6WrpA3TxMnSK4tcbRO+MG2yFZGh3lDmsSlmGfR1ZoIYrpFEAvfWUCfghVXW8p7rl\n258dM+aLVbQ99mrajmfi1od82QlaG+WNQsfagZn49jfXBQbbAWrP3hn7G8OZ4oaH\n1RpyEPFSRWh4GFtrs0GGOA048jgmf0QSkAXQuY4hoQKBgQDqGU2L1LQfarkRoK56\nWQ/pZfvQ11fRL0toQK78HU+5eVecX7qqTgpxzS1Vpj9kgu9wDTeV2xtav0IVOt7u\nPntKvJXdw9lx/CDI7o6TIa+O8rXHdFSw5Rbll5aYgDhH7dzko9yeON5JqYpODwmu\n27Y6++YNt8n/jz4LFZ0C1+TJEQKBgQC5ImmFaWduwamS8mccviKnT9iOZ+SCgFfe\n+LtlFzGEBEJaPhOYSGuTXFjONex8k0D4cwV6TkRCkIirdLqp1ea+13Y3/nGu3OJo\n/0LwE+Mkquh/i/X0iBifU5VhFGJftefFKzF5+28txQOluJJvGDHtYUT7ZpL8UWgJ\neDz5XM/x0wKBgQCnZDxs9kVuCZQYJLteRPz5ubDcXn8u1xCmlUoKgLMXPssEx/bj\n/DW/tiTqj5vYtT+c8faDM09WDlikcZoi5Y6nnD3Ve0urE8wloV9Vmcq8/pQ48Nf2\nPXmn5kMK/PRBirZez0Tb5nIcXhzFQD9+RyEBAEo6GOdZ1AVbS7Mf61xu4QKBgQCU\n/LmYsNOZUWbrKAKNIgJ3TQ2ExN0jnK+ac+czGnAxws+3Gf/g7F8OTyH0iXbQZhzC\nFKaS38uVGgWynZTeupIggPrVYwIP7BiU0OAInqiMSLIkevkrmh7ekYBEiQgF6Dkl\n9nWxqgO1/LfLtPa7SuhbFY1TGCAvyD+GZ2oCb4u1GwKBgENnLrIyA7pOVhpNRq4C\nnbTEH+G9t0bJgLZUAFF9ShYWV0X0TUzko9xzwrBpayYJZ3WSMIL++peqCkQVID6Q\n8KZcNp+oCgNbzbp5YcdD2YQG/CZ07lWvgFWdAvODLMVf+WvJNFuldENvzDHGK59H\njgEpfcLMcFNC+YSGBcFiXfcX\n-----END PRIVATE KEY-----\n",
  "client_email": "vertex-ai-dev@inquinion-code.iam.gserviceaccount.com",
  "client_id": "110093830692433121365",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/vertex-ai-dev%40inquinion-code.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

**Important**: Add `secrets/` to `.gitignore` to avoid committing credentials!

### Step 2: Configure Environment

Edit `deployment/.env`:

```bash
# ============================================
# AI / LLM - Vertex AI Configuration
# ============================================

# LLM Model
LLM_BACKEND=gemini
LLM_MODEL=gemini/gemini-2.0-flash-exp
CREW_LLM_MODEL=gemini/gemini-2.0-flash-exp

# Embeddings (if needed)
EMBEDDINGS_BACKEND=vertex
EMBEDDINGS_MODEL=text-embedding-005
EMBEDDINGS_BATCH_SIZE=1
PREWARM_EMBEDDINGS=false

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=inquinion-code
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/inquinion-code-801c22313fa5.json
VERTEX_AI_LOCATION=us-central1

# Server Configuration
SECUREAI_HOST=0.0.0.0
SECUREAI_PORT=8000
SECUREAI_LOG_LEVEL=INFO
```

### Step 3: Update Docker Compose

Edit `deployment/docker-compose.yml` to mount the secrets:

```yaml
version: '3.8'

services:
  secureai:
    build:
      context: ..
      dockerfile: deployment/Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      # Mount secrets directory
      - ./secrets:/app/secrets:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/inquinion-code-801c22313fa5.json
    restart: unless-stopped
```

### Step 4: Start the Service

```bash
cd secure-code-ai

# Windows
.\scripts\start_local.ps1

# Linux/Mac
./scripts/start_local.sh
```

### Step 5: Verify

```bash
# Test health
curl http://localhost:8000/health

# Test analysis
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pickle\npickle.load(open(\"data.pkl\", \"rb\"))",
    "language": "python"
  }'
```

## Configuration Details

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `LLM_BACKEND` | `gemini` | Use Gemini via Vertex AI |
| `LLM_MODEL` | `gemini/gemini-2.0-flash-exp` | Model to use |
| `GOOGLE_CLOUD_PROJECT` | `inquinion-code` | Your GCP project |
| `GOOGLE_APPLICATION_CREDENTIALS` | `/app/secrets/...json` | Path to service account key |
| `VERTEX_AI_LOCATION` | `us-central1` | GCP region |

### Available Models

You can use any Gemini model available in Vertex AI:

```bash
# Gemini 2.0 Flash (Recommended - Fast & Cheap)
LLM_MODEL=gemini/gemini-2.0-flash-exp

# Gemini 1.5 Pro (More capable, slower)
LLM_MODEL=gemini/gemini-1.5-pro

# Gemini 1.5 Flash (Balanced)
LLM_MODEL=gemini/gemini-1.5-flash
```

## Security Best Practices

### 1. Protect Credentials

```bash
# Add to .gitignore
echo "deployment/secrets/" >> .gitignore
echo "**/*.json" >> .gitignore  # Be careful with this one

# Set proper permissions (Linux/Mac)
chmod 600 deployment/secrets/*.json
```

### 2. Use Read-Only Mount

In `docker-compose.yml`, always use `:ro` (read-only):

```yaml
volumes:
  - ./secrets:/app/secrets:ro  # Read-only!
```

### 3. Rotate Credentials Regularly

- Rotate service account keys every 90 days
- Use Google Cloud Console to manage keys
- Delete old keys after rotation

### 4. Limit Service Account Permissions

Ensure the service account only has:
- `Vertex AI User` role
- `Service Account Token Creator` (if needed)

## Troubleshooting

### Issue: Authentication Failed

**Error**: `google.auth.exceptions.DefaultCredentialsError`

**Solutions**:

1. **Check file path**:
   ```bash
   # Inside container
   docker exec -it secureai ls -la /app/secrets/
   ```

2. **Verify JSON format**:
   ```bash
   cat deployment/secrets/inquinion-code-801c22313fa5.json | python -m json.tool
   ```

3. **Check environment variable**:
   ```bash
   docker exec -it secureai env | grep GOOGLE
   ```

### Issue: Permission Denied

**Error**: `Permission denied: 'inquinion-code-801c22313fa5.json'`

**Solution**:
```bash
# Fix permissions
chmod 644 deployment/secrets/*.json
```

### Issue: Project Not Found

**Error**: `Project inquinion-code not found`

**Solution**:
- Verify project ID in Google Cloud Console
- Ensure service account belongs to this project
- Check billing is enabled

### Issue: API Not Enabled

**Error**: `Vertex AI API has not been used in project`

**Solution**:
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=inquinion-code
```

Or visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com

### Issue: Quota Exceeded

**Error**: `Quota exceeded for quota metric 'Requests'`

**Solution**:
- Check quotas in Google Cloud Console
- Request quota increase if needed
- Implement rate limiting in your application

## Cost Estimation

### Vertex AI Pricing (as of 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Gemini 2.0 Flash | $0.075 | $0.30 |
| Gemini 1.5 Flash | $0.075 | $0.30 |
| Gemini 1.5 Pro | $1.25 | $5.00 |

### Example Costs

**Scenario**: 200 analyses/day, 30 days

- Average input: 2,000 tokens/request
- Average output: 500 tokens/request

**Using Gemini 2.0 Flash**:
- Input: 200 × 30 × 2,000 = 12M tokens = $0.90
- Output: 200 × 30 × 500 = 3M tokens = $0.90
- **Total**: ~$1.80/month

**Much cheaper than RunPod!** ($12-40/month)

## Monitoring

### View Logs

```bash
# Docker logs
docker-compose logs -f secureai

# Check for auth errors
docker-compose logs secureai | grep -i "auth\|credential"
```

### Monitor Usage

Visit Google Cloud Console:
- **Vertex AI Dashboard**: https://console.cloud.google.com/vertex-ai
- **API Metrics**: https://console.cloud.google.com/apis/dashboard
- **Billing**: https://console.cloud.google.com/billing

### Set Budget Alerts

1. Go to: https://console.cloud.google.com/billing/budgets
2. Create budget: $10/month
3. Set alerts at 50%, 80%, 100%

## Comparison: Gemini API vs Vertex AI

| Feature | Gemini API (Free) | Vertex AI |
|---------|-------------------|-----------|
| **Cost** | Free (60 req/min) | Pay-as-you-go (~$2/mo) |
| **Rate Limits** | 60 req/min | Higher (configurable) |
| **SLA** | None | 99.9% uptime |
| **Enterprise Features** | No | Yes (VPC, audit logs) |
| **Setup Complexity** | Easy (API key) | Medium (service account) |
| **Best For** | Development | Production |

## Migration from Gemini API

If you were using Gemini API key before:

### Old Configuration (.env)
```bash
LLM_BACKEND=gemini
GEMINI_API_KEY=AIzaSy...
```

### New Configuration (.env)
```bash
LLM_BACKEND=gemini
GOOGLE_CLOUD_PROJECT=inquinion-code
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/inquinion-code-801c22313fa5.json
VERTEX_AI_LOCATION=us-central1
```

**No code changes needed!** The LLM client automatically detects Vertex AI credentials.

## Advanced Configuration

### Use Different Regions

```bash
# Europe
VERTEX_AI_LOCATION=europe-west1

# Asia
VERTEX_AI_LOCATION=asia-northeast1
```

### Configure Retry Logic

```bash
# In .env
VERTEX_AI_MAX_RETRIES=3
VERTEX_AI_TIMEOUT=60
```

### Enable Request Logging

```bash
# In .env
SECUREAI_LOG_LEVEL=DEBUG
VERTEX_AI_LOG_REQUESTS=true
```

## Next Steps

1. ✅ Save service account credentials
2. ✅ Update `.env` configuration
3. ✅ Update `docker-compose.yml`
4. ✅ Start the service
5. ✅ Test with sample code
6. 📊 Monitor usage in Google Cloud Console
7. 💰 Set up budget alerts

## Support

- **Google Cloud Docs**: https://cloud.google.com/vertex-ai/docs
- **Vertex AI Pricing**: https://cloud.google.com/vertex-ai/pricing
- **Service Account Guide**: https://cloud.google.com/iam/docs/service-accounts

---

**You're now using enterprise-grade Vertex AI with SecureCodeAI!** 🎉

Enjoy better reliability and lower costs than RunPod.
