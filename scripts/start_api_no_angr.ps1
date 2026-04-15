#!/usr/bin/env pwsh
# Start SecureCodeAI API without Angr (Windows-compatible)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SecureCodeAI API Startup (No Angr)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Running without binary analysis support" -ForegroundColor Yellow
Write-Host "      (Angr has compatibility issues on Windows)" -ForegroundColor Yellow
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "api/server.py")) {
    Write-Host " Error: Must run from secure-code-ai directory" -ForegroundColor Red
    Write-Host "   Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "   Please run: cd secure-code-ai" -ForegroundColor Yellow
    exit 1
}

Write-Host " In correct directory" -ForegroundColor Green

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host " Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host " Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "  Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host " Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Set environment variable to skip angr
$env:SKIP_ANGR = "true"
Write-Host " Set SKIP_ANGR=true" -ForegroundColor Green

# Check .env file
if (-not (Test-Path "deployment/.env")) {
    Write-Host "  .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item "deployment/.env.example" "deployment/.env"
    Write-Host " .env file created" -ForegroundColor Green
}

# Check Google Cloud credentials
$credsPath = "deployment/secrets/inquinion-code-801c22313fa5.json"
if (Test-Path $credsPath) {
    Write-Host " Google Cloud credentials found" -ForegroundColor Green
    $env:GOOGLE_APPLICATION_CREDENTIALS = $credsPath
} else {
    Write-Host "  Google Cloud credentials not found at: $credsPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting API Server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API will be available at: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "API docs available at: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Features available:" -ForegroundColor Cyan
Write-Host "   Scanner (AST + LLM)" -ForegroundColor Green
Write-Host "   Speculator (LLM reasoning)" -ForegroundColor Green
Write-Host "   SymBot (Symbolic execution)" -ForegroundColor Green
Write-Host "   Patcher (LLM + verification)" -ForegroundColor Green
Write-Host "   Binary Analyzer (Angr - Windows incompatible)" -ForegroundColor Red
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
