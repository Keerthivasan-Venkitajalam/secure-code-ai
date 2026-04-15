#!/usr/bin/env pwsh
# Test local SecureCodeAI setup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SecureCodeAI Local Setup Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Test 1: Check if API is running
Write-Host "Test 1: Checking if API is running..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $content = $response.Content | ConvertFrom-Json
        if ($content.status -eq "healthy") {
            Write-Host " API is running and healthy" -ForegroundColor Green
        } else {
            Write-Host " API returned unexpected status: $($content.status)" -ForegroundColor Red
            $allPassed = $false
        }
    } else {
        Write-Host " API returned status code: $($response.StatusCode)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " API is not running or not accessible" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   Please start the API with: .\scripts\start_api_local.ps1" -ForegroundColor Yellow
    $allPassed = $false
}
Write-Host ""

# Test 2: Check API documentation
Write-Host "Test 2: Checking API documentation..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host " API documentation is accessible" -ForegroundColor Green
        Write-Host "   URL: http://127.0.0.1:8000/docs" -ForegroundColor Gray
    } else {
        Write-Host " API documentation returned status: $($response.StatusCode)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " API documentation is not accessible" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Test 3: Check OpenAPI spec
Write-Host "Test 3: Checking OpenAPI specification..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/openapi.json" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        $spec = $response.Content | ConvertFrom-Json
        Write-Host " OpenAPI spec is available" -ForegroundColor Green
        Write-Host "   Title: $($spec.info.title)" -ForegroundColor Gray
        Write-Host "   Version: $($spec.info.version)" -ForegroundColor Gray
    } else {
        Write-Host " OpenAPI spec returned status: $($response.StatusCode)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " OpenAPI spec is not accessible" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Test 4: Test analyze endpoint with sample code
Write-Host "Test 4: Testing analyze endpoint..." -ForegroundColor Cyan
$testCode = @"
import os

def vulnerable_function(user_input):
    # Command injection vulnerability
    os.system('ls ' + user_input)
    return True
"@

$body = @{
    code = $testCode
    file_path = "test.py"
    max_iterations = 1
} | ConvertTo-Json

try {
    Write-Host "   Sending test request (this may take 30-60 seconds)..." -ForegroundColor Gray
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/analyze" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -UseBasicParsing `
        -TimeoutSec 120
    
    if ($response.StatusCode -eq 200) {
        $result = $response.Content | ConvertFrom-Json
        Write-Host " Analyze endpoint is working" -ForegroundColor Green
        Write-Host "   Analysis ID: $($result.analysis_id)" -ForegroundColor Gray
        Write-Host "   Vulnerabilities found: $($result.vulnerabilities.Count)" -ForegroundColor Gray
        Write-Host "   Patches generated: $($result.patches.Count)" -ForegroundColor Gray
        Write-Host "   Execution time: $($result.execution_time)s" -ForegroundColor Gray
    } else {
        Write-Host " Analyze endpoint returned status: $($response.StatusCode)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host " Analyze endpoint test failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   This might be due to missing LLM backend configuration" -ForegroundColor Yellow
    $allPassed = $false
}
Write-Host ""

# Test 5: Check extension configuration
Write-Host "Test 5: Checking VS Code extension..." -ForegroundColor Cyan
if (Test-Path "extension/package.json") {
    $packageJson = Get-Content "extension/package.json" | ConvertFrom-Json
    Write-Host " Extension found" -ForegroundColor Green
    Write-Host "   Name: $($packageJson.displayName)" -ForegroundColor Gray
    Write-Host "   Version: $($packageJson.version)" -ForegroundColor Gray
    
    # Check if node_modules exists
    if (Test-Path "extension/node_modules") {
        Write-Host " Extension dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  Extension dependencies not installed" -ForegroundColor Yellow
        Write-Host "   Run: cd extension && npm install" -ForegroundColor Yellow
    }
    
    # Check if compiled
    if (Test-Path "extension/out") {
        Write-Host " Extension compiled" -ForegroundColor Green
    } else {
        Write-Host "  Extension not compiled" -ForegroundColor Yellow
        Write-Host "   Run: cd extension && npm run compile" -ForegroundColor Yellow
    }
} else {
    Write-Host " Extension not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($allPassed) {
    Write-Host " All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your local setup is ready to use!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open VS Code" -ForegroundColor White
    Write-Host "  2. Open a Python file" -ForegroundColor White
    Write-Host "  3. Right-click  'SecureCodeAI: Analyze Current File'" -ForegroundColor White
    Write-Host ""
    Write-Host "Or run extension in dev mode:" -ForegroundColor Cyan
    Write-Host "  cd extension" -ForegroundColor White
    Write-Host "  Press F5 in VS Code" -ForegroundColor White
} else {
    Write-Host "  Some tests failed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Cyan
    Write-Host "  1. Make sure API is running: .\scripts\start_api_local.ps1" -ForegroundColor White
    Write-Host "  2. Check .env file: deployment\.env" -ForegroundColor White
    Write-Host "  3. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  4. Check Google Cloud credentials are configured" -ForegroundColor White
    Write-Host ""
    Write-Host "For more help, see: CONNECT_EXTENSION_LOCAL.md" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
