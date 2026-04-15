# Windows Quickstart

This guide starts SecureCodeAI on Windows with the supported local script and verifies that the API is reachable.

## Prerequisites

- Python 3.10+
- Docker Desktop (optional, only if you use the Docker flow)
- PowerShell (standard on Windows)

## Option A: Native Python startup

```powershell
cd secure-code-ai
.\scripts\start_api_local.ps1
```

When startup completes, test health in a new PowerShell terminal:

```powershell
curl http://127.0.0.1:8000/health
```

If healthy, open API docs:

```powershell
start http://127.0.0.1:8000/docs
```

## Option B: Docker startup

```powershell
cd secure-code-ai
.\scripts\start_local.ps1
```

Then verify:

```powershell
curl http://localhost:8000/health
```

## Use with VS Code extension

1. Open the extension workspace.
2. Set API endpoint to http://localhost:8000.
3. Open a Python file.
4. Run SecureCodeAI analysis from the editor command.

## Troubleshooting

### PowerShell script execution blocked

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port 8000 already in use

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Missing dependencies

```powershell
cd secure-code-ai
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## More documentation

- Main guide: README.md
- Deployment details: deployment/README.md
- Extension usage: extension/README.md
