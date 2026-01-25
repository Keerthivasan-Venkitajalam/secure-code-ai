#!/bin/bash
# SecureCodeAI - RunPod Deployment Script
# This script builds the Docker image, pushes it to a registry, and deploys to RunPod Serverless

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="secureai"
IMAGE_TAG="gpu-latest"
REGISTRY=""
RUNPOD_CONFIG="deployment/runpod.yaml"
SKIP_BUILD=false
SKIP_PUSH=false
SKIP_DEPLOY=false
VERIFY_HEALTH=true
ENVIRONMENT="production"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy SecureCodeAI to RunPod Serverless

OPTIONS:
    --registry URL          Container registry URL (required, e.g., docker.io/username)
    --tag TAG              Image tag (default: gpu-latest)
    --name NAME            Image name (default: secureai)
    --config FILE          RunPod config file (default: deployment/runpod.yaml)
    --skip-build           Skip Docker image build
    --skip-push            Skip pushing image to registry
    --skip-deploy          Skip RunPod deployment (build and push only)
    --no-verify            Skip health check verification
    --environment ENV      Deployment environment (default: production)
    --help                 Show this help message

EXAMPLES:
    # Full deployment
    $0 --registry docker.io/myuser --tag v1.0.0

    # Build and push only (no deployment)
    $0 --registry docker.io/myuser --tag v1.0.0 --skip-deploy

    # Deploy existing image
    $0 --registry docker.io/myuser --tag v1.0.0 --skip-build --skip-push

REQUIREMENTS:
    - Docker installed and running
    - RunPod CLI installed (pip install runpod)
    - RunPod API key configured (runpod config)
    - Access to container registry

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --config)
            RUNPOD_CONFIG="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        --skip-deploy)
            SKIP_DEPLOY=true
            shift
            ;;
        --no-verify)
            VERIFY_HEALTH=false
            shift
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$REGISTRY" ]; then
    print_error "Registry URL is required. Use --registry option."
    show_usage
    exit 1
fi

# Construct full image name
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

print_info "Starting RunPod deployment for SecureCodeAI"
print_info "Image: ${FULL_IMAGE_NAME}"
print_info "Environment: ${ENVIRONMENT}"
echo ""

# Step 1: Build Docker image
if [ "$SKIP_BUILD" = false ]; then
    print_info "Step 1/4: Building Docker image with GPU support..."
    
    # Navigate to project root
    cd "$(dirname "$0")/.."
    
    # Build image
    if docker build \
        --build-arg GPU=true \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -t "${FULL_IMAGE_NAME}" \
        -f deployment/Dockerfile \
        .; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
    echo ""
else
    print_warning "Skipping Docker build (--skip-build)"
    echo ""
fi

# Step 2: Push image to registry
if [ "$SKIP_PUSH" = false ]; then
    print_info "Step 2/4: Pushing image to registry..."
    
    # Login to registry (if needed)
    print_info "Logging in to registry..."
    if ! docker login "${REGISTRY%%/*}" 2>/dev/null; then
        print_warning "Docker login may be required. Please login manually if push fails."
    fi
    
    # Push image
    if docker push "${FULL_IMAGE_NAME}"; then
        print_success "Image pushed to registry: ${FULL_IMAGE_NAME}"
    else
        print_error "Failed to push image to registry"
        exit 1
    fi
    echo ""
else
    print_warning "Skipping image push (--skip-push)"
    echo ""
fi

# Step 3: Deploy to RunPod
if [ "$SKIP_DEPLOY" = false ]; then
    print_info "Step 3/4: Deploying to RunPod Serverless..."
    
    # Check if runpod CLI is installed
    if ! command -v runpod &> /dev/null; then
        print_error "RunPod CLI not found. Install with: pip install runpod"
        exit 1
    fi
    
    # Check if config file exists
    if [ ! -f "$RUNPOD_CONFIG" ]; then
        print_error "RunPod config file not found: $RUNPOD_CONFIG"
        exit 1
    fi
    
    # Update config with actual image name
    print_info "Updating RunPod config with image: ${FULL_IMAGE_NAME}"
    
    # Create temporary config with updated image
    TEMP_CONFIG=$(mktemp)
    sed "s|image:.*|image: ${FULL_IMAGE_NAME}|g" "$RUNPOD_CONFIG" > "$TEMP_CONFIG"
    
    # Deploy to RunPod
    print_info "Deploying to RunPod..."
    if runpod deploy --config "$TEMP_CONFIG" --environment "$ENVIRONMENT"; then
        print_success "Deployment to RunPod initiated"
        
        # Get endpoint URL
        ENDPOINT_URL=$(runpod endpoint list --format json | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
        if [ -n "$ENDPOINT_URL" ]; then
            print_success "Endpoint URL: ${ENDPOINT_URL}"
        fi
    else
        print_error "RunPod deployment failed"
        rm -f "$TEMP_CONFIG"
        exit 1
    fi
    
    # Cleanup temp config
    rm -f "$TEMP_CONFIG"
    echo ""
else
    print_warning "Skipping RunPod deployment (--skip-deploy)"
    echo ""
fi

# Step 4: Verify deployment
if [ "$SKIP_DEPLOY" = false ] && [ "$VERIFY_HEALTH" = true ]; then
    print_info "Step 4/4: Verifying deployment health..."
    
    # Get endpoint URL
    ENDPOINT_URL=$(runpod endpoint list --format json 2>/dev/null | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ -z "$ENDPOINT_URL" ]; then
        print_warning "Could not retrieve endpoint URL. Skipping health check."
        print_info "You can manually check health at: https://your-endpoint-url/health"
    else
        print_info "Waiting for endpoint to become ready (this may take up to 60 seconds)..."
        
        # Wait for health check to pass
        MAX_RETRIES=12
        RETRY_COUNT=0
        HEALTH_CHECK_PASSED=false
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            print_info "Health check attempt $((RETRY_COUNT + 1))/${MAX_RETRIES}..."
            
            # Check health endpoint
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${ENDPOINT_URL}/health/ready" 2>/dev/null || echo "000")
            
            if [ "$HTTP_CODE" = "200" ]; then
                HEALTH_CHECK_PASSED=true
                break
            fi
            
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                sleep 5
            fi
        done
        
        if [ "$HEALTH_CHECK_PASSED" = true ]; then
            print_success "Health check passed! Endpoint is ready."
            print_success "API URL: ${ENDPOINT_URL}"
            print_info "Test the API with: curl ${ENDPOINT_URL}/health"
        else
            print_warning "Health check did not pass within timeout."
            print_info "The endpoint may still be starting up. Check status with:"
            print_info "  runpod endpoint status"
            print_info "  curl ${ENDPOINT_URL}/health"
        fi
    fi
    echo ""
else
    print_warning "Skipping health check verification"
    echo ""
fi

# Summary
print_success "Deployment process completed!"
echo ""
print_info "Next steps:"
print_info "  1. Check deployment status: runpod endpoint status"
print_info "  2. View logs: runpod logs"
print_info "  3. Test API: curl https://your-endpoint-url/health"
print_info "  4. Monitor metrics in RunPod dashboard"
echo ""
print_info "To update the deployment, run this script again with a new tag."
print_info "To rollback, deploy a previous image tag."

