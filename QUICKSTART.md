# Quickstart

This guide starts SecureCodeAI on Windows, macOS, and Linux, then verifies API health.

## Prerequisites

- Python 3.10+
- Docker Desktop / Docker Engine (optional, for Docker flow)
- Node.js 18+ (optional, for extension build)

## Option A: Native startup

### Windows (PowerShell)

```powershell
cd secure-code-ai
.\scripts\start_api_local.ps1
```

If Angr-related issues occur on Windows, use:

```powershell
cd secure-code-ai
.\scripts\start_api_no_angr.ps1
```

### macOS / Linux

```bash
cd secure-code-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```

## Option B: Docker startup

### Windows (PowerShell)

```powershell
cd secure-code-ai
.\scripts\start_local.ps1
```

### macOS / Linux

```bash
cd secure-code-ai
chmod +x scripts/start_local.sh
./scripts/start_local.sh
```

## Verify API

Run from any platform:

```bash
curl http://127.0.0.1:8000/health
```

If healthy, open docs in browser:

- http://127.0.0.1:8000/docs

## Use with VS Code extension

1. Open the extension workspace.
2. Set API endpoint to `http://localhost:8000`.
3. Open a Python file.
4. Run SecureCodeAI analysis from the editor command.

## Troubleshooting

### Windows: script execution blocked

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS/Linux: script permission denied

```bash
chmod +x scripts/start_local.sh
```

### Port 8000 already in use (Windows)

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Port 8000 already in use (macOS/Linux)

```bash
lsof -i :8000
kill -9 <PID>
```

### Missing dependencies

```bash
pip install -r requirements.txt
```

## More documentation

- Main guide: README.md
- Setup details: SETUP.md
- Deployment details: deployment/README.md
- Extension usage: extension/README.md
