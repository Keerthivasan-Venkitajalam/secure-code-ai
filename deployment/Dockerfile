# SecureCodeAI - FastAPI Application Dockerfile
# Supports both CPU and GPU deployment via build argument

# Build argument for GPU support
ARG GPU=false

# Use CUDA base image if GPU enabled, otherwise use slim Python
FROM python:3.10-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA toolkit if GPU enabled
ARG GPU=false
RUN if [ "$GPU" = "true" ]; then \
    apt-get update && apt-get install -y \
        nvidia-cuda-toolkit \
        nvidia-cudnn \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install GPU-specific dependencies if enabled
ARG GPU=false
RUN if [ "$GPU" = "true" ]; then \
    pip install --no-cache-dir \
        vllm>=0.6.0 \
        flash-attn>=2.5.0; \
    fi

# Copy application code
COPY api/ /app/api/
COPY agent/ /app/agent/
COPY __init__.py /app/

# Create models directory for persistent volume mount
RUN mkdir -p /models

# Expose port 8000
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SECUREAI_HOST=0.0.0.0
ENV SECUREAI_PORT=8000
ENV SECUREAI_MODEL_PATH=/models/deepseek-coder-v2-lite-instruct
ENV SECUREAI_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Copy entrypoint script
COPY deployment/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - run uvicorn server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
