# Local Setup Guide - Run SecureCodeAI Without Cloud

This guide shows you how to run SecureCodeAI locally using Docker and connect it to the VS Code extension - no cloud deployment or costs required!

## Prerequisites

- Docker Desktop installed (Windows/Mac) or Docker Engine (Linux)
- VS Code installed
- 8GB+ RAM recommended
- (Optional) NVIDIA GPU for faster inference

## Quick Start (5 Minutes)

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Navigate to deployment directory
cd secure-code-ai/deployment

# 2. Create .env file
cp .env.example .env

# 3. Start the service
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Test the API
curl http://localhost:8000/health
```

### Option 2: Using Start Script

**Windows (PowerShell):**
```powershell
cd secure-code-ai
.\scripts\start_local.ps1
```

**Linux/Mac:**
```bash
cd secure-code-ai
chmod +x scripts/start_local.sh
./scripts/start_local.sh
```

## Detailed Setup

### Step 1: Configure Environment

Create `deployment/.env` from the example:

```bash
cd secure-code-ai/deployment
cp .env.example .env
```

Edit `.env` for local setup:

```bash
# Server Configuration
SECUREAI_HOST=0.0.0.0
SECUREAI_PORT=8000
SECUREAI_WORKERS=1

# LLM Backend - Choose one:
# Option A: Use Gemini (requires API key, free tier available)
LLM_BACKEND=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Option B: Use local model (no API key needed, but slower)
# LLM_BACKEND=local
# SECUREAI_MODEL_PATH=/models/deepseek-coder-v2-lite-instruct

# Logging
SECUREAI_LOG_LEVEL=INFO
SECUREAI_ENABLE_DOCS=true
```

### Step 2: Choose Your LLM Backend

#### Option A: Gemini (Recommended for Local Development)

**Pros**: Fast, no GPU needed, free tier available  
**Cons**: Requires internet, API key

1. Get free API key from: https://makersuite.google.com/app/apikey
2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
3. Set: `LLM_BACKEND=gemini`

#### Option B: Local Model (Fully Offline)

**Pros**: Completely offline, no API costs  
**Cons**: Slower, requires more RAM/disk

1. Download model (done automatically on first run)
2. Set: `LLM_BACKEND=local`
3. Requires: 8GB+ RAM, 10GB+ disk space

### Step 3: Start the Service

#### Using Docker Compose (Easiest)

```bash
cd secure-code-ai/deployment

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f secureai

# Stop when done
docker-compose down
```

#### Using Docker Directly

```bash
cd secure-code-ai

# Build image
docker build -t secureai:local -f deployment/Dockerfile .

# Run container
docker run -d \
  --name secureai \
  -p 8000:8000 \
  --env-file deployment/.env \
  secureai:local

# View logs
docker logs -f secureai

# Stop when done
docker stop secureai
docker rm secureai
```

### Step 4: Verify API is Running

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2026-01-27T..."}

# Check API docs
# Open in browser: http://localhost:8000/docs
```

### Step 5: Configure VS Code Extension

1. **Install the Extension**
   ```bash
   cd secure-code-ai/extension
   npm install
   npm run compile
   code --install-extension .
   ```

2. **Configure Extension Settings**
   
   Open VS Code Settings (Ctrl+,) and search for "SecureCodeAI":
   
   ```json
   {
     "secureCodeAI.apiEndpoint": "http://localhost:8000",
     "secureCodeAI.enabled": true
   }
   ```

   Or edit `.vscode/settings.json` in your workspace:
   
   ```json
   {
     "secureCodeAI.apiEndpoint": "http://localhost:8000"
   }
   ```

3. **Reload VS Code**
   - Press F1
   - Type "Reload Window"
   - Press Enter

### Step 6: Test the Extension

1. Open a Python file with a vulnerability:
   ```python
   # test_vuln.py
   import pickle
   
   def load_data(filename):
       with open(filename, 'rb') as f:
           return pickle.load(f)  # Insecure deserialization
   ```

2. Right-click in the editor
3. Select "SecureCodeAI: Analyze File"
4. Wait for results (15-30 seconds)
5. Review detected vulnerabilities
6. Apply suggested patches

## Troubleshooting

### Issue: Container Won't Start

**Check Docker is running:**
```bash
docker ps
```

**Check logs:**
```bash
docker-compose logs secureai
# or
docker logs secureai
```

**Common fixes:**
- Ensure port 8000 is not in use
- Check `.env` file exists and is configured
- Verify Docker has enough memory (8GB+)

### Issue: API Returns 500 Error

**Check if Gemini API key is valid:**
```bash
# Test Gemini API
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"code":"print(\"test\")", "language":"python"}'
```

**Solutions:**
- Verify `GEMINI_API_KEY` in `.env`
- Check Gemini API quota: https://makersuite.google.com/
- Try switching to local model (slower but no API needed)

### Issue: Extension Can't Connect

**Verify API is accessible:**
```bash
curl http://localhost:8000/health
```

**Check extension settings:**
- Open VS Code Settings
- Search "SecureCodeAI"
- Verify `apiEndpoint` is `http://localhost:8000`

**Check extension logs:**
- Open VS Code Output panel (Ctrl+Shift+U)
- Select "SecureCodeAI" from dropdown
- Look for connection errors

### Issue: Slow Performance

**For Gemini backend:**
- Check internet connection
- Verify API key is valid
- Check Gemini API status

**For local model:**
- Increase Docker memory limit (Docker Desktop → Settings → Resources)
- Use GPU if available (requires NVIDIA GPU + nvidia-docker)
- Consider switching to Gemini for faster results

### Issue: Model Download Fails (Local Backend)

**Manual download:**
```bash
# Download model manually
docker exec -it secureai bash
cd /models
huggingface-cli download deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
```

## Performance Optimization

### Use GPU Acceleration (NVIDIA Only)

1. **Install nvidia-docker:**
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

2. **Update docker-compose.yml:**
   ```yaml
   services:
     secureai:
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: 1
                 capabilities: [gpu]
   ```

3. **Restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Reduce Memory Usage

Edit `.env`:
```bash
# Use smaller model
SECUREAI_MODEL_NAME=deepseek-ai/DeepSeek-Coder-1.3B-Instruct

# Reduce workers
SECUREAI_WORKERS=1

# Reduce GPU memory
SECUREAI_GPU_MEMORY_UTILIZATION=0.7
```

## Development Workflow

### 1. Start Local API
```bash
cd secure-code-ai/deployment
docker-compose up -d
```

### 2. Develop Extension
```bash
cd secure-code-ai/extension
npm run watch  # Auto-recompile on changes
```

### 3. Test in VS Code
- Press F5 to launch Extension Development Host
- Test your changes
- Check logs in Output panel

### 4. Stop When Done
```bash
cd secure-code-ai/deployment
docker-compose down
```

## API Endpoints

Once running locally, you can access:

- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Analyze Endpoint**: POST http://localhost:8000/api/analyze
- **Patch Endpoint**: POST http://localhost:8000/api/patch

## Example API Usage

```bash
# Analyze code for vulnerabilities
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pickle\ndef load(f): return pickle.load(f)",
    "language": "python"
  }'

# Get patch for vulnerability
curl -X POST "http://localhost:8000/api/patch" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import pickle\ndef load(f): return pickle.load(f)",
    "vulnerability": "Insecure deserialization",
    "language": "python"
  }'
```

## Cost Comparison

| Setup | Cost | Speed | Requirements |
|-------|------|-------|--------------|
| Local + Gemini | Free* | Fast | Internet, API key |
| Local + Local Model | Free | Slow | 8GB RAM, 10GB disk |
| RunPod Cloud | $12-40/mo | Fast | Payment method |

*Gemini free tier: 60 requests/minute

## Next Steps

Once your local setup is working:

1. ✅ Test the extension with real code
2. ✅ Try different vulnerability types
3. ✅ Experiment with patch suggestions
4. 📖 Read extension guide: `extension/README.md`
5. 🚀 Consider cloud deployment later when needed

## Support

- **Extension Issues**: Check `extension/README.md`
- **API Issues**: Check `api/README.md`
- **Docker Issues**: Check `deployment/DOCKER_SETUP.md`

## Summary

You now have SecureCodeAI running locally! No cloud costs, no complex setup. Just Docker + VS Code.

**What you can do:**
- ✅ Analyze Python code for vulnerabilities
- ✅ Get AI-powered patch suggestions
- ✅ Use symbolic execution for verification
- ✅ All running on your local machine

**When to consider cloud:**
- Need to share with team
- Want faster performance
- Need 24/7 availability
- Have budget for hosting

For now, enjoy developing locally! 🎉
