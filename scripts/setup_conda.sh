#!/usr/bin/env bash
# Setup script for SecureCodeAI conda environment

set -e

ENV_NAME="software-env"
PYTHON_VERSION="3.10"

echo " Setting up SecureCodeAI environment: $ENV_NAME"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo " Error: conda not found. Please install Anaconda or Miniconda first."
    echo "   Download: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
echo " Creating conda environment: $ENV_NAME (Python $PYTHON_VERSION)"
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

# Activate environment
echo ""
echo " Activating environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $ENV_NAME

# Install PyTorch with CUDA support
echo ""
echo " Installing PyTorch with CUDA 11.8..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install project dependencies
echo ""
echo " Installing SecureCodeAI dependencies..."
pip install -r requirements.txt

# Download model weights
echo ""
echo " Downloading DeepSeek model weights (~32GB)..."
echo " This may take 10-30 minutes..."
python scripts/download_model.py

echo ""
echo " Setup complete!"
echo ""
echo "To activate the environment:"
echo "  conda activate $ENV_NAME"
echo ""
echo "To test the installation:"
echo "  python poc/llm_poc.py"
