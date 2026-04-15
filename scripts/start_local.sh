#!/bin/bash
# Start SecureCodeAI locally using Docker Compose

set -e

echo "=========================================="
echo "SecureCodeAI Local Startup Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed and running${NC}"
echo ""

# Navigate to deployment directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

cd "$DEPLOYMENT_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Please edit deployment/.env and configure:${NC}"
    echo "   1. Choose LLM backend (gemini or local)"
    echo "   2. Add GEMINI_API_KEY if using Gemini"
    echo ""
    echo "Then run this script again."
    exit 0
fi

echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    exit 1
fi

# Stop any existing containers
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true
echo ""

# Start the service
echo "Starting SecureCodeAI..."
echo ""
docker-compose up -d

# Wait for service to be ready
echo ""
echo "Waiting for service to start..."
sleep 5

# Check if service is healthy
MAX_RETRIES=12
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Service failed to start${NC}"
    echo ""
    echo "Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ SecureCodeAI is running!${NC}"
echo "=========================================="
echo ""
echo "API Endpoints:"
echo "  - Health: http://localhost:8000/health"
echo "  - Docs:   http://localhost:8000/docs"
echo "  - API:    http://localhost:8000/api"
echo ""
echo "VS Code Extension Configuration:"
echo "  Set apiEndpoint to: http://localhost:8000"
echo ""
echo "Useful Commands:"
echo "  - View logs:  docker-compose logs -f"
echo "  - Stop:       docker-compose down"
echo "  - Restart:    docker-compose restart"
echo ""
echo "Test the API:"
echo "  curl http://localhost:8000/health"
echo ""
echo "=========================================="
