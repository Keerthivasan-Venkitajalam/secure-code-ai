#!/bin/bash
# SecureCodeAI - Container Entrypoint Script
# Handles model download and graceful shutdown

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}SecureCodeAI Container Starting...${NC}"

# Configuration
MODEL_NAME="${SECUREAI_MODEL_NAME:-deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct}"
MODEL_PATH="${SECUREAI_MODEL_PATH:-/models/deepseek-coder-v2-lite-instruct}"
ENABLE_GPU="${SECUREAI_ENABLE_GPU:-true}"

# Function to check if model exists
check_model_exists() {
    if [ -d "$MODEL_PATH" ] && [ -f "$MODEL_PATH/config.json" ]; then
        echo -e "${GREEN}✓ Model found at $MODEL_PATH${NC}"
        return 0
    else
        echo -e "${YELLOW}✗ Model not found at $MODEL_PATH${NC}"
        return 1
    fi
}

# Function to download model from HuggingFace
download_model() {
    echo -e "${YELLOW}Downloading model: $MODEL_NAME${NC}"
    echo -e "${YELLOW}This may take several minutes...${NC}"
    
    # Check if huggingface-cli is available
    if ! command -v huggingface-cli &> /dev/null; then
        echo -e "${YELLOW}Installing huggingface-cli...${NC}"
        pip install --no-cache-dir huggingface-hub[cli]
    fi
    
    # Download model using huggingface-cli
    echo -e "${YELLOW}Downloading to $MODEL_PATH...${NC}"
    huggingface-cli download "$MODEL_NAME" \
        --local-dir "$MODEL_PATH" \
        --local-dir-use-symlinks False
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Model downloaded successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Model download failed${NC}"
        return 1
    fi
}

# Function to handle graceful shutdown
graceful_shutdown() {
    echo -e "${YELLOW}Received shutdown signal, cleaning up...${NC}"
    
    # Send SIGTERM to the main process (uvicorn)
    if [ ! -z "$MAIN_PID" ]; then
        echo -e "${YELLOW}Stopping API server (PID: $MAIN_PID)...${NC}"
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        
        # Wait for graceful shutdown (max 30 seconds)
        for i in {1..30}; do
            if ! kill -0 "$MAIN_PID" 2>/dev/null; then
                echo -e "${GREEN}✓ API server stopped gracefully${NC}"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            echo -e "${RED}Force stopping API server...${NC}"
            kill -KILL "$MAIN_PID" 2>/dev/null || true
        fi
    fi
    
    echo -e "${GREEN}Cleanup complete, exiting${NC}"
    exit 0
}

# Register signal handlers for graceful shutdown
trap graceful_shutdown SIGTERM SIGINT

# Check GPU availability
if [ "$ENABLE_GPU" = "true" ]; then
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}✓ GPU detected:${NC}"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        echo -e "${YELLOW}⚠ GPU support enabled but nvidia-smi not found${NC}"
        echo -e "${YELLOW}  Running in CPU mode${NC}"
        export SECUREAI_ENABLE_GPU=false
    fi
else
    echo -e "${YELLOW}Running in CPU mode (GPU disabled)${NC}"
fi

# Check if model exists, download if not
if ! check_model_exists; then
    echo -e "${YELLOW}Model not found in persistent volume${NC}"
    echo -e "${YELLOW}Attempting to download from HuggingFace...${NC}"
    
    # Create model directory if it doesn't exist
    mkdir -p "$MODEL_PATH"
    
    # Download model
    if ! download_model; then
        echo -e "${RED}Failed to download model${NC}"
        echo -e "${RED}Please ensure:${NC}"
        echo -e "${RED}  1. Internet connection is available${NC}"
        echo -e "${RED}  2. HuggingFace model name is correct: $MODEL_NAME${NC}"
        echo -e "${RED}  3. You have access to the model (may require HF token)${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Using cached model from persistent volume${NC}"
fi

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo -e "  Model Path: $MODEL_PATH"
echo -e "  GPU Enabled: $ENABLE_GPU"
echo -e "  Host: ${SECUREAI_HOST:-0.0.0.0}"
echo -e "  Port: ${SECUREAI_PORT:-8000}"
echo -e "  Log Level: ${SECUREAI_LOG_LEVEL:-INFO}"

# Start the application
echo -e "${GREEN}Starting SecureCodeAI API Server...${NC}"

# Execute the command passed to the container
# Run in background so we can handle signals
"$@" &
MAIN_PID=$!

# Wait for the main process
wait $MAIN_PID
EXIT_CODE=$?

echo -e "${GREEN}API Server exited with code $EXIT_CODE${NC}"
exit $EXIT_CODE
