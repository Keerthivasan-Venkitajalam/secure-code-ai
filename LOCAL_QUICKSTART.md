# Local QuickStart Guide (No Docker Required)

Since you're having Docker issues, let's run SecureCodeAI directly on your machine and connect it to the VS Code extension.

## Prerequisites

- Python 3.10 or higher
- VS Code installed
- Google Cloud credentials (you already have this)

## Step 1: Install Dependencies

```powershell
cd secure-code-ai

# Create virtual environment (if not already done)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```powershell
# Copy environment template
cp deployment\.env.example deployment\.env

# Edit deployment\.env and set:
# - GOOGLE_APPLICATION_CREDENTIALS path
# - LLM_BACKEND=gemini
# - Other settings as needed
```

Your `.env` should have:
```bash
# LLM Backend
LLM_BACKEND=gemini
GOOGLE_APPLICATION_CREDENTIALS=deployment/secrets/inquinion-code-801c22313fa5.json

# Server Configuration
SECUREAI_HOST=127.0.0.1
SECUREAI_PORT=8000
SECUREAI_WORKERS=1

# Logging
SECUREAI_LOG_LEVEL=INFO
SECUREAI_LOG_FORMAT=json

# Feature Flags
SECUREAI_ENABLE_DOCS=true
SECUREAI_ENABLE_GPU=false
```

## Step 3: Start the API Server

```powershell
# Make sure you're in secure-code-ai directory
cd secure-code-ai

# Activate venv if not already
.\venv\Scripts\Activate.ps1

# Start the server
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 4: Test the API

Open a new PowerShell window:

```powershell
# Test health endpoint
curl http://127.0.0.1:8000/health

# Should return: {"status":"healthy"}

# Test API docs
# Open browser: http://127.0.0.1:8000/docs
```

## Step 5: Configure VS Code Extension

1. **Open Extension Settings**
   - Open VS Code
   - Go to Settings (Ctrl+,)
   - Search for "SecureCodeAI"

2. **Set API Endpoint**
   - Find "SecureCodeAI: API Endpoint"
   - Set to: `http://127.0.0.1:8000`

3. **Or Edit settings.json**
   ```json
   {
     "secureCodeAI.apiEndpoint": "http://127.0.0.1:8000"
   }
   ```

## Step 6: Test the Extension

1. Open a Python file with a vulnerability
2. Right-click → "Scan for Vulnerabilities"
3. The extension should connect to your local API

## Troubleshooting

### Issue: Module not found errors

**Solution**:
```powershell
# Make sure you're in the right directory
cd secure-code-ai

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Google Cloud credentials error

**Solution**:
```powershell
# Verify the credentials file exists
ls deployment\secrets\inquinion-code-801c22313fa5.json

# Set environment variable
$env:GOOGLE_APPLICATION_CREDENTIALS="deployment\secrets\inquinion-code-801c22313fa5.json"
```

### Issue: Port 8000 already in use

**Solution**:
```powershell
# Use a different port
python -m uvicorn api.server:app --host 127.0.0.1 --port 8001 --reload

# Update extension settings to use port 8001
```

### Issue: Extension can't connect

**Solution**:
1. Check API is running: `curl http://127.0.0.1:8000/health`
2. Check extension settings have correct endpoint
3. Check VS Code Output panel for errors
4. Reload VS Code window (Ctrl+Shift+P → "Reload Window")

## Development Workflow

### Terminal 1: Run API Server
```powershell
cd secure-code-ai
.\venv\Scripts\Activate.ps1
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Run Extension (for development)
```powershell
cd secure-code-ai\extension
npm install
npm run compile
# Press F5 in VS Code to launch Extension Development Host
```

## Next Steps

Once this is working:
1. ✅ Local API running
2. ✅ Extension connected
3. ✅ Can scan for vulnerabilities
4. Later: Fix Docker setup for production deployment

## Quick Commands

```powershell
# Start API
cd secure-code-ai
.\venv\Scripts\Activate.ps1
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload

# Test API
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs

# Stop API
# Press Ctrl+C in the terminal
```

## Performance Note

Running without Docker is actually faster for development because:
- No container overhead
- Direct file access
- Faster startup time
- Easier debugging

You can always containerize later for production deployment!
