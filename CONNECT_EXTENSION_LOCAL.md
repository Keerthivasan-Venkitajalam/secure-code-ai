# Connect VS Code Extension to Local API

This guide shows you how to run SecureCodeAI locally without Docker and connect the VS Code extension.

## Quick Setup (5 Minutes)

### Step 1: Start the Local API

Open PowerShell in the `secure-code-ai` directory:

```powershell
# Run the startup script
.\scripts\start_api_local.ps1
```

The script will:
- ✅ Check Python installation
- ✅ Create/activate virtual environment
- ✅ Install dependencies
- ✅ Check .env configuration
- ✅ Start the API server on http://127.0.0.1:8000

You should see:
```
========================================
Starting API Server...
========================================

API will be available at: http://127.0.0.1:8000
API docs available at: http://127.0.0.1:8000/docs

Press Ctrl+C to stop the server

INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 2: Test the API

Open a new PowerShell window:

```powershell
# Test health endpoint
curl http://127.0.0.1:8000/health

# Expected output: {"status":"healthy"}
```

Or open in browser: http://127.0.0.1:8000/docs

### Step 3: Install the Extension

#### Option A: Install from VSIX (if you have it)
```powershell
cd secure-code-ai/extension
code --install-extension securecodai-0.1.0.vsix
```

#### Option B: Run in Development Mode
```powershell
cd secure-code-ai/extension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Open in VS Code
code .

# Press F5 to launch Extension Development Host
```

### Step 4: Configure Extension (Optional)

The extension defaults to `http://localhost:8000`, but you can change it:

1. Open VS Code Settings (Ctrl+,)
2. Search for "SecureCodeAI"
3. Set "API Endpoint" to `http://127.0.0.1:8000`

Or edit `.vscode/settings.json`:
```json
{
  "securecodai.apiEndpoint": "http://127.0.0.1:8000",
  "securecodai.maxIterations": 3,
  "securecodai.showInlineHints": true
}
```

### Step 5: Test the Extension

1. Open a Python file with a vulnerability (or create one):

```python
# test_vuln.py
import pickle
import os

def unsafe_function(user_input):
    # SQL Injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_input
    
    # Command Injection vulnerability
    os.system("ls " + user_input)
    
    # Insecure Deserialization
    data = pickle.loads(user_input)
    
    return data
```

2. Right-click in the editor → "SecureCodeAI: Analyze Current File"

3. Wait for analysis (may take 30-60 seconds)

4. View results in the Output panel (View → Output → SecureCodeAI)

## Troubleshooting

### Issue: API won't start

**Check Python version:**
```powershell
python --version
# Should be 3.10 or higher
```

**Check if port 8000 is in use:**
```powershell
netstat -ano | findstr :8000
```

**Use a different port:**
```powershell
# Start API on port 8001
python -m uvicorn api.server:app --host 127.0.0.1 --port 8001 --reload

# Update extension settings
# securecodai.apiEndpoint: "http://127.0.0.1:8001"
```

### Issue: Extension can't connect

**Verify API is running:**
```powershell
curl http://127.0.0.1:8000/health
```

**Check extension output:**
1. View → Output
2. Select "SecureCodeAI" from dropdown
3. Look for connection errors

**Reload VS Code:**
- Ctrl+Shift+P → "Developer: Reload Window"

### Issue: Google Cloud credentials error

**Set environment variable:**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="deployment\secrets\inquinion-code-801c22313fa5.json"
```

**Or edit deployment/.env:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=deployment/secrets/inquinion-code-801c22313fa5.json
LLM_BACKEND=gemini
```

### Issue: Module not found errors

**Reinstall dependencies:**
```powershell
cd secure-code-ai
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Development Workflow

### Terminal 1: API Server
```powershell
cd secure-code-ai
.\scripts\start_api_local.ps1
# Keep this running
```

### Terminal 2: Extension Development (Optional)
```powershell
cd secure-code-ai\extension
npm run watch
# Watches for TypeScript changes
```

### VS Code: Extension Testing
- Press F5 to launch Extension Development Host
- Test extension in the new window
- Make changes to extension code
- Reload window (Ctrl+R) to see changes

## Extension Features

### Commands (Ctrl+Shift+P)
- **SecureCodeAI: Analyze Current File** - Scan open file
- **SecureCodeAI: Analyze Workspace** - Scan all Python files
- **SecureCodeAI: Apply Suggested Patch** - Apply a patch
- **SecureCodeAI: Configure API Endpoint** - Change API URL

### Context Menu (Right-click)
- **SecureCodeAI: Analyze Current File** - Quick scan

### Settings
- `securecodai.apiEndpoint` - API URL (default: http://localhost:8000)
- `securecodai.maxIterations` - Max patch attempts (default: 3)
- `securecodai.autoAnalyze` - Auto-scan on save (default: false)
- `securecodai.showInlineHints` - Show inline hints (default: true)

## API Endpoints

The local API provides:

- `GET /health` - Health check
- `POST /analyze` - Analyze code for vulnerabilities
- `GET /docs` - Interactive API documentation
- `GET /openapi.json` - OpenAPI specification

## Performance Tips

### Faster Analysis
1. Use smaller code files
2. Reduce `maxIterations` to 1-2 for testing
3. Use Gemini (faster than local models)

### Reduce Startup Time
1. Keep virtual environment activated
2. Don't restart API between tests
3. Use `--reload` flag for hot reload

## Next Steps

Once everything is working:

1. ✅ Local API running
2. ✅ Extension connected
3. ✅ Can scan files
4. ✅ Can view results

You can now:
- Test on real codebases
- Develop new features
- Run benchmarks
- Later: Package extension for marketplace

## Quick Reference

```powershell
# Start API
cd secure-code-ai
.\scripts\start_api_local.ps1

# Test API
curl http://127.0.0.1:8000/health

# View API docs
start http://127.0.0.1:8000/docs

# Stop API
# Press Ctrl+C in API terminal

# Install extension dependencies
cd extension
npm install

# Compile extension
npm run compile

# Run extension in dev mode
# Press F5 in VS Code
```

## Why Local is Better for Development

✅ **Faster startup** - No container overhead  
✅ **Easier debugging** - Direct Python debugging  
✅ **Hot reload** - Changes apply immediately  
✅ **Better logs** - See everything in terminal  
✅ **No Docker issues** - Avoid Docker Desktop problems  

You can always containerize later for production!

## Support

If you encounter issues:

1. Check API logs in terminal
2. Check extension output (View → Output → SecureCodeAI)
3. Check VS Code Developer Tools (Help → Toggle Developer Tools)
4. Review `LOCAL_QUICKSTART.md` for more details

---

**Status**: Ready to use!  
**API**: http://127.0.0.1:8000  
**Docs**: http://127.0.0.1:8000/docs
