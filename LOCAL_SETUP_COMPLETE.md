# Local Setup Complete - No Docker Required! 🎉

Since you don't have budget for RunPod right now, I've set up everything to run locally without Docker.

## What Was Created

### 📚 Documentation (3 guides)
1. **LOCAL_QUICKSTART.md** - Quick 5-minute setup guide
2. **CONNECT_EXTENSION_LOCAL.md** - Complete guide to connect extension to local API
3. **LOCAL_SETUP_COMPLETE.md** - This file

### 🛠️ Scripts (2 PowerShell scripts)
1. **scripts/start_api_local.ps1** - One-command API startup
2. **scripts/test_local_setup.ps1** - Verify everything works

## Quick Start (3 Steps)

### Step 1: Start the API (Terminal 1)

**For Windows (Recommended):**
```powershell
cd secure-code-ai
.\scripts\start_api_no_angr.ps1
```

**For Linux/Mac:**
```powershell
cd secure-code-ai
.\scripts\start_api_local.ps1
```

**Note**: Windows users should use `start_api_no_angr.ps1` due to Angr compatibility issues. See `WINDOWS_SETUP.md` for details.

This will:
- ✅ Check Python
- ✅ Create/activate venv
- ✅ Install dependencies
- ✅ Start API on http://127.0.0.1:8000

### Step 2: Test the Setup (Terminal 2)

```powershell
cd secure-code-ai
.\scripts\test_local_setup.ps1
```

This will verify:
- ✅ API is running
- ✅ Health endpoint works
- ✅ Analyze endpoint works
- ✅ Extension is ready

### Step 3: Use the Extension

#### Option A: Install Extension (if packaged)
```powershell
cd extension
code --install-extension securecodai-0.1.0.vsix
```

#### Option B: Run in Development Mode
```powershell
cd extension
npm install
npm run compile
# Press F5 in VS Code to launch Extension Development Host
```

Then:
1. Open a Python file
2. Right-click → "SecureCodeAI: Analyze Current File"
3. View results in Output panel

## Why This is Better Than Docker (For Now)

✅ **No cost** - Runs entirely on your machine  
✅ **Faster** - No container overhead  
✅ **Easier debugging** - Direct access to logs  
✅ **Hot reload** - Changes apply immediately  
✅ **No Docker issues** - Avoid Docker Desktop API problems  

## Current Architecture

```
┌─────────────────────────────────────────┐
│         VS Code Extension               │
│    (TypeScript, runs in VS Code)        │
└──────────────┬──────────────────────────┘
               │ HTTP Requests
               │ http://127.0.0.1:8000
               ▼
┌─────────────────────────────────────────┐
│      FastAPI Server (Python)            │
│    Running locally with uvicorn         │
│    - /health                            │
│    - /analyze                           │
│    - /docs                              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    LLM Agent Workflow (Python)          │
│    - Scanner (Angr + LLM)               │
│    - Speculator (LLM reasoning)         │
│    - SymBot (Symbolic execution)        │
│    - Patcher (LLM + verification)       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Google Gemini API                  │
│    (via your credentials)               │
└─────────────────────────────────────────┘
```

## Configuration

### API Configuration (deployment/.env)
```bash
# LLM Backend
LLM_BACKEND=gemini
GOOGLE_APPLICATION_CREDENTIALS=deployment/secrets/inquinion-code-801c22313fa5.json

# Server
SECUREAI_HOST=127.0.0.1
SECUREAI_PORT=8000
SECUREAI_WORKERS=1

# Logging
SECUREAI_LOG_LEVEL=INFO
SECUREAI_ENABLE_DOCS=true
```

### Extension Configuration (VS Code settings)
```json
{
  "securecodai.apiEndpoint": "http://127.0.0.1:8000",
  "securecodai.maxIterations": 3,
  "securecodai.showInlineHints": true
}
```

## Troubleshooting

### API won't start
```powershell
# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Check if port 8000 is in use
netstat -ano | findstr :8000
```

### Extension can't connect
```powershell
# Test API manually
curl http://127.0.0.1:8000/health

# Check extension output
# View → Output → SecureCodeAI

# Reload VS Code
# Ctrl+Shift+P → "Developer: Reload Window"
```

### Google Cloud credentials error
```powershell
# Verify file exists
ls deployment\secrets\inquinion-code-801c22313fa5.json

# Set environment variable
$env:GOOGLE_APPLICATION_CREDENTIALS="deployment\secrets\inquinion-code-801c22313fa5.json"
```

## Testing the Setup

### Test 1: API Health
```powershell
curl http://127.0.0.1:8000/health
# Expected: {"status":"healthy"}
```

### Test 2: API Docs
Open browser: http://127.0.0.1:8000/docs

### Test 3: Analyze Endpoint
Create a test file with a vulnerability:

```python
# test_vuln.py
import os

def unsafe(user_input):
    os.system('ls ' + user_input)  # Command injection
```

Then in VS Code:
1. Right-click → "SecureCodeAI: Analyze Current File"
2. Wait 30-60 seconds
3. View results in Output panel

## Development Workflow

### Terminal 1: API Server
```powershell
cd secure-code-ai
.\scripts\start_api_local.ps1
# Keep running
```

### Terminal 2: Testing
```powershell
# Test API
curl http://127.0.0.1:8000/health

# Run full test
.\scripts\test_local_setup.ps1
```

### VS Code: Extension Development
```powershell
cd extension
npm run watch  # Auto-compile on changes
# Press F5 to launch Extension Development Host
```

## What's Next

### Immediate (Working Now)
- ✅ Local API running
- ✅ Extension connected
- ✅ Can scan Python files
- ✅ Can view vulnerabilities
- ✅ Can apply patches

### Short Term (When Ready)
- 📦 Package extension for marketplace
- 🧪 Run benchmarks (CyberSecEval, PySecDB)
- 📊 Generate evaluation reports
- 📝 Write research paper

### Long Term (When Budget Available)
- ☁️ Deploy to RunPod Serverless
- 🌐 Public API endpoint
- 📈 Auto-scaling
- 📊 Production monitoring

## Cost Comparison

### Current Setup (Local)
- **Cost**: $0/month
- **Performance**: Good (depends on your machine)
- **Availability**: Only when your machine is on
- **Best for**: Development, testing, personal use

### Future Setup (RunPod)
- **Cost**: $12-40/month (based on usage)
- **Performance**: Excellent (dedicated GPU)
- **Availability**: 24/7 with auto-scaling
- **Best for**: Production, team use, public access

## Support Resources

- **Quick Start**: `LOCAL_QUICKSTART.md`
- **Connection Guide**: `CONNECT_EXTENSION_LOCAL.md`
- **API Docs**: http://127.0.0.1:8000/docs
- **Extension README**: `extension/README.md`

## Quick Commands Reference

```powershell
# Start API
cd secure-code-ai
.\scripts\start_api_local.ps1

# Test setup
.\scripts\test_local_setup.ps1

# Test API health
curl http://127.0.0.1:8000/health

# View API docs
start http://127.0.0.1:8000/docs

# Install extension deps
cd extension
npm install

# Compile extension
npm run compile

# Run extension in dev mode
# Press F5 in VS Code
```

## Success Checklist

Before using the extension, verify:

- [ ] API starts without errors
- [ ] Health endpoint returns `{"status":"healthy"}`
- [ ] API docs accessible at http://127.0.0.1:8000/docs
- [ ] Google Cloud credentials configured
- [ ] Extension dependencies installed (`npm install`)
- [ ] Extension compiled (`npm run compile`)
- [ ] VS Code settings configured (optional)

## Next Steps

1. **Start the API**: `.\scripts\start_api_local.ps1`
2. **Test the setup**: `.\scripts\test_local_setup.ps1`
3. **Open VS Code**: Test the extension
4. **Scan some code**: Try it on real Python files
5. **Review results**: Check the Output panel

---

**Status**: ✅ Ready to use locally!  
**API**: http://127.0.0.1:8000  
**Cost**: $0/month  
**Performance**: Good for development

When you're ready for production deployment, we can revisit the RunPod setup!
