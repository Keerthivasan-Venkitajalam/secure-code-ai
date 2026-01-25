#!/bin/bash
# Test script for docker-compose deployment
# Tests: service startup, health check, and API functionality

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SecureCodeAI Docker Compose Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="secureai-api"
API_URL="http://localhost:8000"
MAX_WAIT_TIME=120  # Maximum wait time in seconds
HEALTH_CHECK_INTERVAL=5  # Seconds between health checks

# Function to print test status
print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up...${NC}"
    docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Register cleanup on exit
trap cleanup EXIT

# Test 1: Check if docker-compose file exists
print_test "Checking if docker-compose.yml exists..."
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "docker-compose.yml not found"
    exit 1
fi
print_success "docker-compose.yml found"

# Test 2: Validate docker-compose configuration
print_test "Validating docker-compose configuration..."
if docker-compose -f "$COMPOSE_FILE" config > /dev/null 2>&1; then
    print_success "docker-compose configuration is valid"
else
    print_error "docker-compose configuration is invalid"
    exit 1
fi

# Test 3: Build and start the service
print_test "Building and starting service (this may take a few minutes)..."
if docker-compose -f "$COMPOSE_FILE" up -d --build; then
    print_success "Service started successfully"
else
    print_error "Failed to start service"
    docker-compose -f "$COMPOSE_FILE" logs
    exit 1
fi

# Test 4: Wait for service to be ready
print_test "Waiting for service to be ready (max ${MAX_WAIT_TIME}s)..."
ELAPSED=0
READY=false

while [ $ELAPSED -lt $MAX_WAIT_TIME ]; do
    # Check if container is running
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "$SERVICE_NAME.*Up"; then
        print_error "Container is not running"
        docker-compose -f "$COMPOSE_FILE" logs --tail=50
        exit 1
    fi
    
    # Try health check
    if curl -sf "$API_URL/health" > /dev/null 2>&1; then
        READY=true
        break
    fi
    
    echo -e "${YELLOW}Waiting... (${ELAPSED}s/${MAX_WAIT_TIME}s)${NC}"
    sleep $HEALTH_CHECK_INTERVAL
    ELAPSED=$((ELAPSED + HEALTH_CHECK_INTERVAL))
done

if [ "$READY" = false ]; then
    print_error "Service did not become ready within ${MAX_WAIT_TIME}s"
    echo ""
    echo "Container logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=100
    exit 1
fi

print_success "Service is ready (took ${ELAPSED}s)"

# Test 5: Verify health endpoint
print_test "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s "$API_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    print_success "Health endpoint returned valid response"
    echo "Response: $HEALTH_RESPONSE"
else
    print_error "Health endpoint returned invalid response"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 6: Verify readiness endpoint
print_test "Testing /health/ready endpoint..."
READY_RESPONSE=$(curl -s "$API_URL/health/ready")
if echo "$READY_RESPONSE" | grep -q '"ready"'; then
    print_success "Readiness endpoint returned valid response"
    echo "Response: $READY_RESPONSE"
else
    print_error "Readiness endpoint returned invalid response"
    echo "Response: $READY_RESPONSE"
    exit 1
fi

# Test 7: Test /analyze endpoint with sample code
print_test "Testing /analyze endpoint with sample vulnerable code..."
ANALYZE_REQUEST='{
  "code": "import sqlite3\ndef get_user(user_id):\n    conn = sqlite3.connect(\"db.sqlite\")\n    cursor = conn.cursor()\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor.execute(query)\n    return cursor.fetchone()",
  "file_path": "test.py",
  "max_iterations": 1
}'

ANALYZE_RESPONSE=$(curl -s -X POST "$API_URL/analyze" \
    -H "Content-Type: application/json" \
    -d "$ANALYZE_REQUEST")

if echo "$ANALYZE_RESPONSE" | grep -q '"analysis_id"'; then
    print_success "/analyze endpoint returned valid response"
    echo "Response preview: $(echo "$ANALYZE_RESPONSE" | head -c 200)..."
else
    print_error "/analyze endpoint returned invalid response"
    echo "Response: $ANALYZE_RESPONSE"
    exit 1
fi

# Test 8: Verify API documentation is accessible
print_test "Testing API documentation endpoints..."
if curl -sf "$API_URL/docs" > /dev/null 2>&1; then
    print_success "/docs endpoint is accessible"
else
    print_warning "/docs endpoint is not accessible (may be disabled)"
fi

if curl -sf "$API_URL/redoc" > /dev/null 2>&1; then
    print_success "/redoc endpoint is accessible"
else
    print_warning "/redoc endpoint is not accessible (may be disabled)"
fi

# Test 9: Check container logs for errors
print_test "Checking container logs for errors..."
ERROR_COUNT=$(docker-compose -f "$COMPOSE_FILE" logs | grep -i "error" | grep -v "ERROR_RESPONSE" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No errors found in logs"
else
    print_warning "Found $ERROR_COUNT error messages in logs"
    echo "Recent errors:"
    docker-compose -f "$COMPOSE_FILE" logs | grep -i "error" | grep -v "ERROR_RESPONSE" | tail -5
fi

# Test 10: Verify volumes are mounted
print_test "Verifying volume mounts..."
VOLUME_INFO=$(docker-compose -f "$COMPOSE_FILE" ps -q | xargs docker inspect --format '{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}')
if echo "$VOLUME_INFO" | grep -q "/models"; then
    print_success "Models volume is mounted"
else
    print_warning "Models volume mount not found"
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}All critical tests passed!${NC}"
echo ""
echo "Service is running at: $API_URL"
echo "API Documentation: $API_URL/docs"
echo ""
echo "To view logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "To stop service: docker-compose -f $COMPOSE_FILE down"
echo ""

# Don't cleanup automatically - let user inspect
trap - EXIT
echo -e "${YELLOW}Service is still running. Run 'docker-compose down' to stop.${NC}"
