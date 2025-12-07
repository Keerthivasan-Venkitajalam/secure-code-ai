# SecureCodeAI - Cleanup Script
# Remove unused conda environments to free up disk space

Write-Host "🧹 Conda Environment Cleanup Utility" -ForegroundColor Cyan
Write-Host ""

# List all environments
Write-Host "📋 Current environments:" -ForegroundColor Yellow
conda env list
Write-Host ""

# Prompt for environments to delete
Write-Host "❓ Which environments would you like to delete?" -ForegroundColor Yellow
Write-Host "   (Recommended: ai-assistant, slm_env, torch310, fnma)" -ForegroundColor Gray
Write-Host ""
Write-Host "   Common unused environments:" -ForegroundColor Gray
Write-Host "   - ai-assistant" -ForegroundColor Gray
Write-Host "   - slm_env (duplicate)" -ForegroundColor Gray
Write-Host "   - torch310" -ForegroundColor Gray
Write-Host "   - fnma (duplicate)" -ForegroundColor Gray
Write-Host "   - ca-env" -ForegroundColor Gray
Write-Host "   - tf_gpu_env" -ForegroundColor Gray
Write-Host ""

# Safe environments to keep
$keepEnvs = @("base", "software-env")

# Suggested environments to delete
$suggestedDelete = @("ai-assistant", "slm_env", "torch310", "fnma", "ca-env", "tf_gpu_env")

Write-Host "⚠️  This script will help you delete: $($suggestedDelete -join ', ')" -ForegroundColor Yellow
Write-Host "✅ Will keep: $($keepEnvs -join ', ')" -ForegroundColor Green
Write-Host ""

$confirm = Read-Host "Do you want to proceed with deleting these environments? (yes/no)"

if ($confirm -eq "yes" -or $confirm -eq "y") {
    foreach ($env in $suggestedDelete) {
        Write-Host ""
        Write-Host "🗑️  Deleting environment: $env" -ForegroundColor Cyan
        conda env remove -n $env -y
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ Successfully deleted $env" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Could not delete $env (might not exist)" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "🎉 Cleanup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💾 Checking disk space freed..." -ForegroundColor Cyan
    conda clean --all -y
    
    Write-Host ""
    Write-Host "📋 Remaining environments:" -ForegroundColor Yellow
    conda env list
} else {
    Write-Host ""
    Write-Host "❌ Cleanup cancelled" -ForegroundColor Red
    Write-Host ""
    Write-Host "To manually delete environments, run:" -ForegroundColor Gray
    Write-Host "   conda env remove -n <environment-name>" -ForegroundColor Gray
}
