#!/bin/bash
# SecureCodeAI - RunPod Deployment Test Script
# This script validates a RunPod deployment by testing all critical functionality

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Configuration
ENDPOINT_URL=""
WAIT_FOR_COLD_START=false
TEST_SCALE_TO_ZERO=false
VERBOSE=false

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_test_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 --endpoint URL [OPTIONS]

Test RunPod deployment of SecureCodeAI

REQUIRED:
    --endpoint URL         RunPod endpoint URL (e.g., https://xxx.runpod.io)

OPTIONS:
    --test-cold-start      Test cold start behavior (requires waiting 5+ minutes)
    --test-scale-to-zero   Test scale-to-zero behavior (requires waiting 5+ minutes)
    --verbose              Show detailed request/response data
    --help                 Show this help message

EXAMPLES:
    # Basic health and functionality tests
    $0 --endpoint https://xxx.runpod.io

    # Full test suite including cold start
    $0 --endpoint https://xxx.runpod.io --test-cold-start --test-scale-to-zero

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --endpoint)
            ENDPOINT_URL="$2"
            shift 2
            ;;
        --test-cold-start)
            WAIT_FOR_COLD_START=true
            shift
            ;;
        --test-scale-to-zero)
            TEST_SCALE_TO_ZERO=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
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
if [ -z "$ENDPOINT_URL" ]; then
    print_error "Endpoint URL is required. Use --endpoint option."
    show_usage
    exit 1
fi

# Remove trailing slash from URL
ENDPOINT_URL="${ENDPOINT_URL%/}"

# Function to run a test
run_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    local test_name="$1"
    local test_command="$2"
    
    if [ "$VERBOSE" = true ]; then
        print_info "Running: $test_command"
    fi
    
    if eval "$test_command"; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_success "$test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_error "$test_name"
        return 1
    fi
}

# Function to make HTTP request and check response
http_get() {
    local url="$1"
    local expected_code="${2:-200}"
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$VERBOSE" = true ]; then
        print_info "Response code: $http_code"
        print_info "Response body: $body"
    fi
    
    if [ "$http_code" = "$expected_code" ]; then
        return 0
    else
        print_error "Expected HTTP $expected_code, got $http_code"
        return 1
    fi
}

# Function to make POST request
http_post() {
    local url="$1"
    local data="$2"
    local expected_code="${3:-200}"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$data" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$VERBOSE" = true ]; then
        print_info "Response code: $http_code"
        print_info "Response body: $body"
    fi
    
    if [ "$http_code" = "$expected_code" ]; then
        echo "$body"
        return 0
    else
        print_error "Expected HTTP $expected_code, got $http_code"
        return 1
    fi
}

# Start testing
print_info "Starting RunPod deployment tests"
print_info "Endpoint: $ENDPOINT_URL"
echo ""

# Test 1: Basic Health Check
print_test_header "1. Basic Health Check"
run_test "GET /health returns 200" "http_get '${ENDPOINT_URL}/health' 200"

# Test 2: Readiness Check
print_test_header "2. Readiness Check"
run_test "GET /health/ready returns 200" "http_get '${ENDPOINT_URL}/health/ready' 200"

# Test 3: Health Response Structure
print_test_header "3. Health Response Validation"
health_response=$(curl -s "${ENDPOINT_URL}/health")
if echo "$health_response" | grep -q '"status"' && \
   echo "$health_response" | grep -q '"vllm_loaded"' && \
   echo "$health_response" | grep -q '"workflow_ready"'; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "Health response contains required fields"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    print_error "Health response missing required fields"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 4: Analyze Endpoint - Valid Request
print_test_header "4. Analyze Endpoint - Valid Request"
print_info "Testing vulnerability analysis with SQL injection code..."

analyze_request='{
  "code": "import sqlite3\ndef get_user(user_id):\n    conn = sqlite3.connect(\"db.sqlite\")\n    cursor = conn.cursor()\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor.execute(query)\n    return cursor.fetchone()",
  "file_path": "test.py",
  "max_iterations": 2
}'

analyze_response=$(http_post "${ENDPOINT_URL}/analyze" "$analyze_request" 200)
if [ $? -eq 0 ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "POST /analyze returns 200 for valid request"
    
    # Validate response structure
    if echo "$analyze_response" | grep -q '"analysis_id"' && \
       echo "$analyze_response" | grep -q '"vulnerabilities"' && \
       echo "$analyze_response" | grep -q '"patches"'; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        print_success "Analyze response contains required fields"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_error "Analyze response missing required fields"
    fi
else
    TESTS_FAILED=$((TESTS_FAILED + 2))
    print_error "POST /analyze failed"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 2))

# Test 5: Analyze Endpoint - Invalid Request
print_test_header "5. Analyze Endpoint - Invalid Request"
invalid_request='{"code": ""}'
if http_post "${ENDPOINT_URL}/analyze" "$invalid_request" 400 >/dev/null 2>&1; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "POST /analyze returns 400 for empty code"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    print_error "POST /analyze should return 400 for empty code"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 6: Response Time
print_test_header "6. Response Time Check"
print_info "Measuring response time for health check..."
start_time=$(date +%s%N)
curl -s "${ENDPOINT_URL}/health" >/dev/null
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds

if [ $response_time -lt 1000 ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "Health check response time: ${response_time}ms (< 1000ms)"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    print_error "Health check response time: ${response_time}ms (>= 1000ms)"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 7: HTTPS Enabled
print_test_header "7. HTTPS Configuration"
if echo "$ENDPOINT_URL" | grep -q "^https://"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "Endpoint uses HTTPS"
else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    print_error "Endpoint should use HTTPS"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 8: API Documentation Disabled
print_test_header "8. API Documentation (Production)"
if http_get "${ENDPOINT_URL}/docs" 404 >/dev/null 2>&1; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    print_success "API docs disabled in production (404)"
else
    print_warning "API docs may be enabled (should be disabled in production)"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 9: Scale to Zero (Optional)
if [ "$TEST_SCALE_TO_ZERO" = true ]; then
    print_test_header "9. Scale to Zero Behavior"
    print_info "This test requires waiting 5+ minutes for scale-to-zero..."
    print_info "Sending initial request to ensure instance is active..."
    
    http_get "${ENDPOINT_URL}/health" 200 >/dev/null
    
    print_info "Waiting 5 minutes for scale-to-zero (300 seconds)..."
    for i in {1..30}; do
        echo -n "."
        sleep 10
    done
    echo ""
    
    print_info "Checking if instance scaled to zero..."
    # After 5 minutes, the instance should have scaled to zero
    # The next request should trigger a cold start
    
    print_info "Sending request after idle period..."
    start_time=$(date +%s)
    if http_get "${ENDPOINT_URL}/health" 200 >/dev/null 2>&1; then
        end_time=$(date +%s)
        cold_start_time=$((end_time - start_time))
        
        if [ $cold_start_time -gt 5 ]; then
            TESTS_PASSED=$((TESTS_PASSED + 1))
            print_success "Cold start detected (${cold_start_time}s > 5s)"
        else
            print_warning "No cold start detected (${cold_start_time}s). Instance may not have scaled to zero."
        fi
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_error "Request failed after idle period"
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

# Test 10: Cold Start Performance (Optional)
if [ "$WAIT_FOR_COLD_START" = true ]; then
    print_test_header "10. Cold Start Performance"
    print_info "Testing cold start time (requires scale-to-zero first)..."
    print_info "Waiting for scale-to-zero (5 minutes)..."
    
    # Wait for scale to zero
    sleep 300
    
    print_info "Triggering cold start..."
    start_time=$(date +%s)
    if http_get "${ENDPOINT_URL}/health/ready" 200 >/dev/null 2>&1; then
        end_time=$(date +%s)
        cold_start_time=$((end_time - start_time))
        
        if [ $cold_start_time -le 30 ]; then
            TESTS_PASSED=$((TESTS_PASSED + 1))
            print_success "Cold start time: ${cold_start_time}s (<= 30s)"
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
            print_error "Cold start time: ${cold_start_time}s (> 30s)"
        fi
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        print_error "Cold start failed"
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

# Test Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total Tests:  ${TESTS_TOTAL}"
echo -e "${GREEN}Passed:       ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed:       ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "All tests passed! ✓"
    exit 0
else
    print_error "Some tests failed. Please review the output above."
    exit 1
fi

