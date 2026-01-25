# Load Testing Guide

This document describes how to perform load testing on the SecureCodeAI API to measure performance, throughput, and system behavior under concurrent load.

## Prerequisites

1. **Install Locust:**
   ```bash
   pip install locust
   ```

2. **Start the API Server:**
   ```bash
   # From the project root
   python -m api.server
   ```
   
   The server should be running on `http://localhost:8000`

3. **Verify Server is Running:**
   ```bash
   curl http://localhost:8000/health
   ```

## Running Load Tests

### Quick Start

**Linux/Mac:**
```bash
chmod +x scripts/run_load_test.sh
./scripts/run_load_test.sh
```

**Windows:**
```powershell
.\scripts\run_load_test.ps1
```

### Manual Execution

Run a 60-second load test with 10 concurrent users:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=60s \
    --headless \
    --html=load_test_results/report.html \
    --csv=load_test_results/data
```

### Interactive Mode (Web UI)

For interactive load testing with real-time charts:

```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser.

## Test Configuration

### Default Settings

- **Concurrent Users:** 10
- **Spawn Rate:** 2 users/second
- **Duration:** 60 seconds
- **Target Host:** http://localhost:8000

### Task Distribution

The load test simulates realistic user behavior with weighted tasks:

| Task | Weight | Description |
|------|--------|-------------|
| `/analyze` | 10 | Analyze code for vulnerabilities (most common) |
| `/health` | 3 | Health check endpoint |
| `/health/ready` | 1 | Readiness check endpoint |

### Sample Code Snippets

The test uses 6 different code samples to simulate variety:
1. SQL Injection vulnerability
2. Command Injection vulnerability
3. Path Traversal vulnerability
4. XSS vulnerability
5. Hardcoded credentials
6. Safe code (no vulnerabilities)

## Metrics Collected

### Throughput
- **Requests/second:** Total number of requests processed per second
- **Target:** > 1 req/s for `/analyze` endpoint

### Latency
- **p50 (Median):** 50% of requests complete within this time
- **p95:** 95% of requests complete within this time
- **p99:** 99% of requests complete within this time
- **Max:** Maximum response time observed

### Success Rate
- **Success Rate:** Percentage of requests that completed successfully (200 OK)
- **Failure Rate:** Percentage of requests that failed
- **Target:** > 95% success rate

### Resource Usage
- **Memory:** Monitor for memory leaks during sustained load
- **CPU:** Monitor CPU utilization
- **Queue Depth:** Track request queue depth from `/health` endpoint

## Interpreting Results

### Good Performance Indicators

✓ **Throughput:** > 1 req/s for `/analyze` endpoint  
✓ **Latency p50:** < 2 seconds  
✓ **Latency p95:** < 5 seconds  
✓ **Latency p99:** < 10 seconds  
✓ **Success Rate:** > 95%  
✓ **No Memory Leaks:** Stable memory usage over time  

### Warning Signs

⚠ **High Latency:** p95 > 10 seconds indicates performance issues  
⚠ **High Failure Rate:** > 5% failures indicates stability issues  
⚠ **Memory Growth:** Continuously increasing memory indicates leaks  
⚠ **Rate Limiting:** Many 429 responses indicates rate limit too low  

## Example Output

```
Summary Statistics:
  Total Requests: 450
  Total Failures: 5
  Failure Rate: 1.11%
  Average Response Time: 1250.45ms
  Median Response Time (p50): 980.23ms
  95th Percentile (p95): 2340.67ms
  99th Percentile (p99): 3120.89ms
  Max Response Time: 4567.12ms
  Min Response Time: 234.56ms
  Requests/sec: 7.50

Per-Endpoint Statistics:

  /analyze:
    Requests: 320
    Failures: 4
    Avg Response Time: 1450.23ms
    p50: 1200.45ms
    p95: 2800.34ms
    p99: 3500.67ms

  /health:
    Requests: 96
    Failures: 1
    Avg Response Time: 45.67ms
    p50: 42.34ms
    p95: 78.90ms
    p99: 95.12ms

  /health/ready:
    Requests: 34
    Failures: 0
    Avg Response Time: 38.45ms
    p50: 35.67ms
    p95: 56.78ms
    p99: 67.89ms
```

## Advanced Testing Scenarios

### Stress Testing

Test system limits by gradually increasing load:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users=50 \
    --spawn-rate=5 \
    --run-time=300s \
    --headless
```

### Spike Testing

Test system recovery from sudden load spikes:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users=100 \
    --spawn-rate=50 \
    --run-time=120s \
    --headless
```

### Endurance Testing

Test for memory leaks over extended periods:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=3600s \
    --headless
```

## Troubleshooting

### Server Not Responding

**Problem:** Load test fails with connection errors

**Solution:**
1. Verify server is running: `curl http://localhost:8000/health`
2. Check server logs for errors
3. Ensure no firewall blocking localhost:8000

### High Failure Rate

**Problem:** > 10% of requests failing

**Possible Causes:**
- Server overloaded (reduce concurrent users)
- Rate limiting too aggressive (increase rate limit)
- Application errors (check server logs)

### Memory Leaks

**Problem:** Memory usage continuously increases

**Solution:**
1. Monitor memory with: `ps aux | grep python`
2. Check for unclosed resources in code
3. Review vLLM engine cleanup logic
4. Use memory profiler: `python -m memory_profiler api/server.py`

### Rate Limiting

**Problem:** Many 429 (Too Many Requests) responses

**Solution:**
1. Increase rate limit in configuration:
   ```bash
   export SECUREAI_RATE_LIMIT=20  # requests per minute
   ```
2. Or reduce concurrent users in load test

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Test

on:
  push:
    branches: [main]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust
      
      - name: Start API server
        run: |
          python -m api.server &
          sleep 10
      
      - name: Run load test
        run: |
          locust -f tests/load_test.py \
            --host=http://localhost:8000 \
            --users=10 \
            --spawn-rate=2 \
            --run-time=60s \
            --headless \
            --html=load_test_report.html
      
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: load-test-results
          path: load_test_report.html
```

## Best Practices

1. **Baseline First:** Run load tests on a known-good version to establish baseline metrics
2. **Consistent Environment:** Always test in the same environment (same hardware, same config)
3. **Warm-up Period:** Allow 10-30 seconds for the system to warm up before measuring
4. **Multiple Runs:** Run tests multiple times and average results
5. **Monitor Resources:** Watch CPU, memory, disk I/O during tests
6. **Realistic Scenarios:** Use realistic code samples and request patterns
7. **Document Results:** Keep a log of load test results over time

## References

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://www.blazemeter.com/blog/performance-testing-best-practices)
- [API Load Testing Guide](https://www.nginx.com/blog/load-testing-apis/)
