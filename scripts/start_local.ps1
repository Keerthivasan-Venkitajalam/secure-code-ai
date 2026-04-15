# Start SecureCodeAI locally using Docker Compose
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SecureCodeAI Local Startup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version
    Write-Host " Docker is installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host " Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
}

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host " Docker is running" -ForegroundColor Green
} catch {
    Write-Host " Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again"
    exit 1
}

Write-Host ""

# Navigate to deployment directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DeploymentDir = Join-Path $ProjectRoot "deployment"

Set-Location $DeploymentDir

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "  .env file not found" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host " Created .env file" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Please edit deployment/.env and configure:" -ForegroundColor Yellow
    Write-Host "   1. Choose LLM backend (gemini or local)"
    Write-Host "   2. Add GEMINI_API_KEY if using Gemini"
    Write-Host ""
    Write-Host "Then run this script again."
    exit 0
}

Write-Host " .env file found" -ForegroundColor Green
Write-Host ""

# Check if docker-compose.yml exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host " docker-compose.yml not found" -ForegroundColor Red
    exit 1
}

# Stop any existing containers
Write-Host "Stopping any existing containers..."
try {
    docker-compose down 2>$null
} catch {
    # Ignore errors if no containers are running
}
Write-Host ""

# Start the service
Write-Host "Starting SecureCodeAI..."
Write-Host ""
docker-compose up -d

# Wait for service to be ready
Write-Host ""
Write-Host "Waiting for service to start..."
Start-Sleep -Seconds 5

# Check if service is healthy
$MaxRetries = 12
$RetryCount = 0
$ServiceHealthy = $false

while ($RetryCount -lt $MaxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host " Service is healthy!" -ForegroundColor Green
            $ServiceHealthy = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    
    $RetryCount++
    Write-Host "Waiting... ($RetryCount/$MaxRetries)"
    Start-Sleep -Seconds 5
}

if (-not $ServiceHealthy) {
    Write-Host " Service failed to start" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs with: docker-compose logs"
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " SecureCodeAI is running!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Endpoints:"
Write-Host "  - Health: http://localhost:8000/health"
Write-Host "  - Docs:   http://localhost:8000/docs"
Write-Host "  - API:    http://localhost:8000/api"
Write-Host ""
Write-Host "VS Code Extension Configuration:"
Write-Host "  Set apiEndpoint to: http://localhost:8000"
Write-Host ""
Write-Host "Useful Commands:"
Write-Host "  - View logs:  docker-compose logs -f"
Write-Host "  - Stop:       docker-compose down"
Write-Host "  - Restart:    docker-compose restart"
Write-Host ""
Write-Host "Test the API:"
Write-Host "  curl http://localhost:8000/health"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
