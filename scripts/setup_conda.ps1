# SecureCodeAI - Windows Setup Script (PowerShell)
# Run this script to set up the conda environment on Windows

$ENV_NAME = "software-env"
$PYTHON_VERSION = "3.10"

Write-Host "🚀 Setting up SecureCodeAI environment: $ENV_NAME" -ForegroundColor Green
Write-Host ""

# Check if conda is installed
try {
    $condaVersion = conda --version
    Write-Host "✅ Found conda: $condaVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: conda not found. Please install Anaconda or Miniconda first." -ForegroundColor Red
    Write-Host "   Download: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}

# Create conda environment
Write-Host ""
Write-Host "📦 Creating conda environment: $ENV_NAME (Python $PYTHON_VERSION)" -ForegroundColor Cyan
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

# Activate environment
Write-Host ""
Write-Host "🔧 Activating environment..." -ForegroundColor Cyan
conda activate $ENV_NAME

# Install PyTorch with CUDA support
Write-Host ""
Write-Host "📥 Installing PyTorch with CUDA 11.8..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install project dependencies
Write-Host ""
Write-Host "📥 Installing SecureCodeAI dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

# Download model weights
Write-Host ""
Write-Host "📥 Downloading DeepSeek model weights (~32GB)..." -ForegroundColor Cyan
Write-Host "⏳ This may take 10-30 minutes depending on your internet speed..." -ForegroundColor Yellow
python scripts/download_model.py

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the environment:" -ForegroundColor Cyan
Write-Host "  conda activate $ENV_NAME"
Write-Host ""
Write-Host "To test the installation:" -ForegroundColor Cyan
Write-Host "  python poc/llm_poc.py"
