# Load Testing Script for SecureCodeAI API (PowerShell)
#
# This script runs load tests using Locust to measure:
# - Throughput (requests/second)
# - Latency (p50, p95, p99)
# - System behavior under concurrent load
#
# Prerequisites:
# - API server must be running on http://localhost:8000
# - Locust must be installed: pip install locust
#
# Usage:
#   .\scripts\run_load_test.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "SecureCodeAI Load Testing" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if locust is installed
try {
    $null = Get-Command locust -ErrorAction Stop
} catch {
    Write-Host "Error: Locust is not installed" -ForegroundColor Red
    Write-Host "Install with: pip install locust" -ForegroundColor Yellow
    exit 1
}

# Check if API server is running
Write-Host "Checking if API server is running..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ API server is running" -ForegroundColor Green
} catch {
    Write-Host "Error: API server is not running on http://localhost:8000" -ForegroundColor Red
    Write-Host "Start the server with: python -m api.server" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Create results directory
$ResultsDir = "load_test_results"
if (!(Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReportFile = "$ResultsDir\load_test_$Timestamp.txt"

Write-Host "Running load test..."
Write-Host "  Users: 10 concurrent"
Write-Host "  Spawn rate: 2 users/second"
Write-Host "  Duration: 60 seconds"
Write-Host "  Results will be saved to: $ReportFile"
Write-Host ""

# Run load test
$locustArgs = @(
    "-f", "tests\load_test.py",
    "--host=http://localhost:8000",
    "--users=10",
    "--spawn-rate=2",
    "--run-time=60s",
    "--headless",
    "--html=$ResultsDir\load_test_$Timestamp.html",
    "--csv=$ResultsDir\load_test_$Timestamp"
)

# Run locust and capture output
$output = & locust $locustArgs 2>&1 | Tee-Object -FilePath $ReportFile

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Load Test Complete" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to:"
Write-Host "  - Text report: $ReportFile"
Write-Host "  - HTML report: $ResultsDir\load_test_$Timestamp.html"
Write-Host "  - CSV data: $ResultsDir\load_test_$Timestamp_stats.csv"
Write-Host ""

# Check for memory leaks (basic check)
Write-Host "Checking for potential memory issues..."
$content = Get-Content $ReportFile -Raw
if ($content -match "MemoryError|OutOfMemory") {
    Write-Host "⚠ WARNING: Potential memory issues detected" -ForegroundColor Yellow
} else {
    Write-Host "✓ No obvious memory issues detected" -ForegroundColor Green
}

Write-Host ""
Write-Host "To view detailed results, open:"
Write-Host "  $ResultsDir\load_test_$Timestamp.html" -ForegroundColor Cyan
