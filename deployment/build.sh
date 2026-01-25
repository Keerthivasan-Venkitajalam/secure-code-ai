#!/bin/bash
# SecureCodeAI - Docker Build Script
# Builds container with optional GPU support

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
IMAGE_NAME="secureai"
IMAGE_TAG="latest"
GPU_ENABLED="false"
PUSH_IMAGE="false"
REGISTRY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU_ENABLED="true"
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE="true"
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --gpu              Enable GPU support (default: false)"
            echo "  --tag TAG          Image tag (default: latest)"
            echo "  --name NAME        Image name (default: secureai)"
            echo "  --push             Push image to registry after build"
            echo "  --registry URL     Container registry URL"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --gpu --tag v1.0.0"
            echo "  $0 --gpu --push --registry docker.io/myuser"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Construct full image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$IMAGE_TAG"
fi

# Display build configuration
echo -e "${GREEN}SecureCodeAI Docker Build${NC}"
echo -e "Image: $FULL_IMAGE_NAME"
echo -e "GPU Support: $GPU_ENABLED"
echo -e "Push to Registry: $PUSH_IMAGE"
echo ""

# Change to deployment directory
cd "$(dirname "$0")"

# Build the image
echo -e "${YELLOW}Building Docker image...${NC}"

if [ "$GPU_ENABLED" = "true" ]; then
    echo -e "${YELLOW}Building with GPU support (CUDA)${NC}"
    docker build \
        --build-arg GPU=true \
        -t "$FULL_IMAGE_NAME" \
        -f Dockerfile \
        ..
else
    echo -e "${YELLOW}Building CPU-only image${NC}"
    docker build \
        --build-arg GPU=false \
        -t "$FULL_IMAGE_NAME" \
        -f Dockerfile \
        ..
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# Push to registry if requested
if [ "$PUSH_IMAGE" = "true" ]; then
    if [ -z "$REGISTRY" ]; then
        echo -e "${RED}Error: --registry must be specified when using --push${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Pushing image to registry...${NC}"
    docker push "$FULL_IMAGE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Push successful${NC}"
    else
        echo -e "${RED}✗ Push failed${NC}"
        exit 1
    fi
fi

# Display image info
echo -e "${GREEN}Image built successfully:${NC}"
docker images "$FULL_IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo -e "${GREEN}To run the container:${NC}"
if [ "$GPU_ENABLED" = "true" ]; then
    echo -e "  docker run --gpus all -p 8000:8000 -v \$(pwd)/models:/models $FULL_IMAGE_NAME"
else
    echo -e "  docker run -p 8000:8000 -v \$(pwd)/models:/models $FULL_IMAGE_NAME"
fi
