# Quick Start with Vertex AI - Ready to Go! 🚀

Your SecureCodeAI is now configured to use Google Cloud Vertex AI. Everything is set up and ready to run!

## What's Already Configured

✅ **Vertex AI Credentials**: Saved in `deployment/secrets/`  
✅ **Environment Variables**: Configured in `deployment/.env`  
✅ **Docker Compose**: Updated to mount secrets  
✅ **Security**: Secrets directory added to `.gitignore`

## Start in 3 Steps

### Step 1: Start the Backend

```powershell
# Windows (you're on Windows)
cd secure-code-ai
.\scripts\start_local.ps1
```

Wait for: `✅ SecureCodeAI is running!`

### Step 2: Test the API

```powershell
# Test health
curl http://localhost:8000/health

# Test analysis
curl -X POST "http://localhost:8000/api/analyze" `
  -H "Content-Type: application/json" `
  -d '{\"code\":\"import pickle\npickle.load(open(\\\"data.pkl\\\", \\\"rb\\\"))\",\"language\":\"python\"}'
```

### Step 3: Use VS Code Extension

```bash
cd extension
npm install
npm run compile
# Press F5 in VS Code
```

## Configuration Details

### Current Setup

```bash
# Project
GOOGLE_CLOUD_PROJECT=inquinion-code

# Model (Fast & Cheap)
LLM_MODEL=gemini/gemini-2.0-flash-exp

# Region
VERTEX_AI_LOCATION=us-central1

# Credentials
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/inquinion-code-801c22313fa5.json
```

### Cost Estimate

**For 200 analyses/day:**
- Input tokens: ~12M/month = $0.90
- Output tokens: ~3M/month = $0.90
- **Total: ~$1.80/month**

Much cheaper than RunPod ($12-40/month)!

## Available Models

You can switch models by editing `deployment/.env`:

```bash
# Gemini 2.0 Flash (Current - Recommended)
LLM_MODEL=gemini/gemini-2.0-flash-exp

# Gemini 1.5 Pro (More capable, 5x more expensive)
LLM_MODEL=gemini/gemini-1.5-pro

# Gemini 1.5 Flash (Balanced)
LLM_MODEL=gemini/gemini-1.5-flash
```

Then restart:
```powershell
docker-compose restart
```

## Fallback: Gemini API Key

If Vertex AI has issues, you can use the Gemini API key:

Edit `deployment/.env`:
```bash
# Comment out Vertex AI
# GOOGLE_CLOUD_PROJECT=inquinion-code
# GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/inquinion-code-801c22313fa5.json

# Use Gemini API key instead
GEMINI_API_KEY=AIzaSyBM1PQ7DpoZuVr0ShVBdDyaRcaPW3RU99U
```

Restart:
```powershell
docker-compose restart
```

## Verify Setup

### Check Credentials

```powershell
# Verify file exists
Test-Path secure-code-ai\deployment\secrets\inquinion-code-801c22313fa5.json

# Should return: True
```

### Check Environment

```powershell
# View configuration
Get-Content secure-code-ai\deployment\.env | Select-String "GOOGLE"
```

### Check Docker

```powershell
# View logs
docker-compose logs -f secureai-api

# Check for auth errors
docker-compose logs secureai-api | Select-String "auth|credential"
```

## Troubleshooting

### Issue: Authentication Failed

**Check credentials are mounted:**
```powershell
docker exec -it secureai-api ls -la /app/secrets/
```

**Should see**: `inquinion-code-801c22313fa5.json`

### Issue: API Not Enabled

Visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com

Click "Enable" for Vertex AI API.

### Issue: Permission Denied

```powershell
# Fix permissions
icacls "secure-code-ai\deployment\secrets\*.json" /grant Everyone:R
```

## Monitor Usage

### Google Cloud Console

- **Vertex AI**: https://console.cloud.google.com/vertex-ai?project=inquinion-code
- **API Metrics**: https://console.cloud.google.com/apis/dashboard?project=inquinion-code
- **Billing**: https://console.cloud.google.com/billing

### Set Budget Alert

1. Go to: https://console.cloud.google.com/billing/budgets
2. Create budget: $10/month
3. Set alerts at 50%, 80%, 100%

## Test Examples

### Example 1: Insecure Deserialization

```python
# test_pickle.py
import pickle

def load_data(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)  # Vulnerable!
```

### Example 2: SQL Injection

```python
# test_sql.py
import sqlite3

def get_user(username):
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return conn.execute(query).fetchone()  # Vulnerable!
```

### Example 3: Command Injection

```python
# test_cmd.py
import os

def ping_host(host):
    os.system(f"ping {host}")  # Vulnerable!
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Local Machine                        │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │   VS Code        │  HTTP   │   Docker         │          │
│  │   Extension      │◄───────►│   Container      │          │
│  └──────────────────┘         └────────┬─────────┘          │
│                                         │                     │
│                                         │ Mounts              │
│                                         ▼                     │
│                              ┌──────────────────┐            │
│                              │  Secrets Dir     │            │
│                              │  (Credentials)   │            │
│                              └────────┬─────────┘            │
└───────────────────────────────────────┼───────────────────────┘
                                        │
                                        │ Authenticates
                                        ▼
                               ┌────────────────────┐
                               │  Google Cloud      │
                               │  Vertex AI         │
                               │  (us-central1)     │
                               └────────┬───────────┘
                                        │
                                        ▼
                               ┌────────────────────┐
                               │  Gemini 2.0 Flash  │
                               │  Model             │
                               └────────────────────┘
```

## Comparison

| Feature | Vertex AI (Current) | Gemini API | RunPod |
|---------|---------------------|------------|--------|
| **Cost** | ~$2/month | Free (limited) | $12-40/month |
| **Speed** | Fast | Fast | Fast |
| **Rate Limits** | High | 60 req/min | Custom |
| **Setup** | Done! ✅ | Easy | Complex |
| **Best For** | Production | Development | GPU workloads |

## Next Steps

1. ✅ **Start backend**: `.\scripts\start_local.ps1`
2. ✅ **Test API**: `curl http://localhost:8000/health`
3. ✅ **Install extension**: `cd extension && npm install`
4. ✅ **Test vulnerabilities**: Try the examples above
5. 📊 **Monitor usage**: Check Google Cloud Console
6. 💰 **Set budget**: Create budget alert

## Support

- **Setup Guide**: [deployment/GOOGLE_CLOUD_SETUP.md](deployment/GOOGLE_CLOUD_SETUP.md)
- **Local Development**: [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md)
- **Extension Guide**: [extension/LOCAL_DEVELOPMENT.md](extension/LOCAL_DEVELOPMENT.md)
- **Google Cloud Docs**: https://cloud.google.com/vertex-ai/docs

---

**You're all set!** 🎉

Your SecureCodeAI is configured with enterprise-grade Vertex AI and ready to detect vulnerabilities.

**Total cost**: ~$2/month  
**Setup time**: Already done!  
**Performance**: Fast (Gemini 2.0 Flash)

Just run `.\scripts\start_local.ps1` and you're good to go! 🚀
