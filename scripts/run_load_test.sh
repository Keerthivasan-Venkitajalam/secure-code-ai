#!/bin/bash
# Load Testing Script for SecureCodeAI API
#
# This script runs load tests using Locust to measure:
# - Throughput (requests/second)
# - Latency (p50, p95, p99)
# - System behavior under concurrent load
#
# Prerequisites:
# - API server must be running on http://localhost:8000
# - Locust must be installed: pip install locust
#
# Usage:
#   ./scripts/run_load_test.sh

set -e

echo "=================================="
echo "SecureCodeAI Load Testing"
echo "=================================="
echo ""

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "Error: Locust is not installed"
    echo "Install with: pip install locust"
    exit 1
fi

# Check if API server is running
echo "Checking if API server is running..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Error: API server is not running on http://localhost:8000"
    echo "Start the server with: python -m api.server"
    exit 1
fi

echo "✓ API server is running"
echo ""

# Create results directory
RESULTS_DIR="load_test_results"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$RESULTS_DIR/load_test_${TIMESTAMP}.txt"

echo "Running load test..."
echo "  Users: 10 concurrent"
echo "  Spawn rate: 2 users/second"
echo "  Duration: 60 seconds"
echo "  Results will be saved to: $REPORT_FILE"
echo ""

# Run load test
locust \
    -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=60s \
    --headless \
    --html="$RESULTS_DIR/load_test_${TIMESTAMP}.html" \
    --csv="$RESULTS_DIR/load_test_${TIMESTAMP}" \
    2>&1 | tee "$REPORT_FILE"

echo ""
echo "=================================="
echo "Load Test Complete"
echo "=================================="
echo ""
echo "Results saved to:"
echo "  - Text report: $REPORT_FILE"
echo "  - HTML report: $RESULTS_DIR/load_test_${TIMESTAMP}.html"
echo "  - CSV data: $RESULTS_DIR/load_test_${TIMESTAMP}_stats.csv"
echo ""

# Check for memory leaks (basic check)
echo "Checking for potential memory issues..."
if grep -q "MemoryError\|OutOfMemory" "$REPORT_FILE"; then
    echo "⚠ WARNING: Potential memory issues detected"
else
    echo "✓ No obvious memory issues detected"
fi

echo ""
echo "To view detailed results, open:"
echo "  $RESULTS_DIR/load_test_${TIMESTAMP}.html"
