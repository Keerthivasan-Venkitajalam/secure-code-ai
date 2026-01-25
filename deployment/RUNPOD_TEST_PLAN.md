# RunPod Deployment Test Plan

This document provides a comprehensive manual test plan for validating the SecureCodeAI RunPod Serverless deployment.

## Test Environment

- **Platform**: RunPod Serverless
- **GPU**: NVIDIA RTX A5000 (24GB VRAM)
- **Container**: secureai:gpu-v1.0.0
- **Endpoint**: https://your-endpoint.runpod.io

## Prerequisites

Before testing:
1. Deploy to RunPod staging environment
2. Note the endpoint URL
3. Ensure you have `curl` installed
4. Have the test script ready: `scripts/test_runpod_deployment.sh`

## Automated Test Suite

### Quick Test (5 minutes)

Run the automated test script for basic validation:

```bash
cd scripts
./test_runpod_deployment.sh --endpoint https://your-endpoint.runpod.io
```

This tests:
- ✓ Health check endpoint
- ✓ Readiness check endpoint
- ✓ Health response structure
- ✓ Analyze endpoint with valid request
- ✓ Analyze endpoint with invalid request
- ✓ Response time
- ✓ HTTPS configuration
- ✓ API documentation disabled

### Full Test Suite (15+ minutes)

Run the full test suite including scale-to-zero and cold start:

```bash
./test_runpod_deployment.sh \
  --endpoint https://your-endpoint.runpod.io \
  --test-cold-start \
  --test-scale-to-zero \
  --verbose
```

This includes all quick tests plus:
- ✓ Scale-to-zero behavior (5 min wait)
- ✓ Cold start performance (30s target)

## Manual Test Cases

### Test 1: Basic Health Check

**Objective**: Verify the API server is running and healthy.

**Steps**:
1. Send GET request to `/health`
   ```bash
   curl https://your-endpoint.runpod.io/health
   ```

**Expected Result**:
- HTTP 200 OK
- Response body:
  ```json
  {
    "status": "healthy",
    "vllm_loaded": true,
    "workflow_ready": true,
    "uptime_seconds": 123.45,
    "request_queue_depth": 0
  }
  ```

**Pass Criteria**:
- ✓ Status code is 200
- ✓ `status` field is "healthy"
- ✓ `vllm_loaded` is true
- ✓ `workflow_ready` is true

---

### Test 2: Readiness Check

**Objective**: Verify all components are initialized and ready.

**Steps**:
1. Send GET request to `/health/ready`
   ```bash
   curl https://your-endpoint.runpod.io/health/ready
   ```

**Expected Result**:
- HTTP 200 OK
- Response body:
  ```json
  {
    "ready": true,
    "components": {
      "api_server": true,
      "vllm_engine": true,
      "agent_workflow": true
    }
  }
  ```

**Pass Criteria**:
- ✓ Status code is 200
- ✓ `ready` field is true
- ✓ All components are true

---

### Test 3: Vulnerability Analysis - SQL Injection

**Objective**: Test the core analysis functionality with a SQL injection vulnerability.

**Steps**:
1. Send POST request to `/analyze` with vulnerable code:
   ```bash
   curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "code": "import sqlite3\ndef get_user(user_id):\n    conn = sqlite3.connect(\"db.sqlite\")\n    cursor = conn.cursor()\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor.execute(query)\n    return cursor.fetchone()",
       "file_path": "app.py",
       "max_iterations": 3
     }'
   ```

**Expected Result**:
- HTTP 200 OK
- Response contains:
  - `analysis_id`: UUID string
  - `vulnerabilities`: Array with at least one SQL injection vulnerability
  - `patches`: Array with at least one patch
  - `execution_time`: Float (seconds)
  - `workflow_complete`: true

**Pass Criteria**:
- ✓ Status code is 200
- ✓ Response contains `analysis_id`
- ✓ At least one vulnerability detected
- ✓ At least one patch provided
- ✓ Execution time < 60 seconds

---

### Test 4: Invalid Request Handling

**Objective**: Verify proper error handling for invalid requests.

**Steps**:
1. Send request with empty code:
   ```bash
   curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{"code": ""}'
   ```

2. Send request with missing required field:
   ```bash
   curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

3. Send request with invalid max_iterations:
   ```bash
   curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{"code": "print(1)", "max_iterations": 100}'
   ```

**Expected Result**:
- HTTP 400 Bad Request for all cases
- Response body contains error details

**Pass Criteria**:
- ✓ All requests return 400
- ✓ Error messages are descriptive

---

### Test 5: Response Time

**Objective**: Verify response times meet performance requirements.

**Steps**:
1. Measure health check response time:
   ```bash
   time curl https://your-endpoint.runpod.io/health
   ```

2. Measure analysis response time:
   ```bash
   time curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{"code": "print(1)", "file_path": "test.py"}'
   ```

**Expected Result**:
- Health check: < 1 second
- Analysis (simple code): < 30 seconds
- Analysis (complex code): < 60 seconds

**Pass Criteria**:
- ✓ Health check responds in < 1s
- ✓ Simple analysis completes in < 30s
- ✓ Complex analysis completes in < 60s

---

### Test 6: Scale to Zero Behavior

**Objective**: Verify the instance scales to zero after 5 minutes of inactivity.

**Steps**:
1. Send a request to ensure instance is active:
   ```bash
   curl https://your-endpoint.runpod.io/health
   ```

2. Wait 5 minutes without sending any requests

3. Check RunPod dashboard to verify instance count is 0

4. Send another request:
   ```bash
   curl https://your-endpoint.runpod.io/health
   ```

5. Observe cold start behavior

**Expected Result**:
- After 5 minutes: Instance count = 0 in dashboard
- Next request: Cold start occurs (takes longer)
- Request succeeds after cold start

**Pass Criteria**:
- ✓ Instance scales to zero after 5 min idle
- ✓ Cold start request succeeds
- ✓ No data loss or errors

---

### Test 7: Cold Start Performance

**Objective**: Verify cold start completes within 30 seconds.

**Steps**:
1. Ensure instance is scaled to zero (wait 5+ minutes)

2. Measure time for first request after scale-to-zero:
   ```bash
   time curl https://your-endpoint.runpod.io/health/ready
   ```

3. Record the total time

**Expected Result**:
- Cold start completes in ≤ 30 seconds
- Request succeeds with 200 OK
- Subsequent requests are fast (no cold start)

**Pass Criteria**:
- ✓ Cold start time ≤ 30 seconds
- ✓ Request succeeds
- ✓ Subsequent requests < 1 second

---

### Test 8: Concurrent Requests

**Objective**: Verify the system handles concurrent requests correctly.

**Steps**:
1. Send 5 concurrent requests:
   ```bash
   for i in {1..5}; do
     curl -X POST https://your-endpoint.runpod.io/analyze \
       -H "Content-Type: application/json" \
       -d '{"code": "print('$i')", "file_path": "test'$i'.py"}' &
   done
   wait
   ```

2. Verify all requests complete successfully

**Expected Result**:
- All 5 requests return 200 OK
- Each request has unique `analysis_id`
- No state interference between requests
- RunPod may scale to multiple instances

**Pass Criteria**:
- ✓ All requests succeed
- ✓ Unique analysis IDs
- ✓ No errors or timeouts

---

### Test 9: HTTPS and Security

**Objective**: Verify HTTPS is enabled and security features are configured.

**Steps**:
1. Verify HTTPS:
   ```bash
   curl -v https://your-endpoint.runpod.io/health 2>&1 | grep "SSL"
   ```

2. Verify API docs are disabled:
   ```bash
   curl https://your-endpoint.runpod.io/docs
   ```

3. Test CORS (if applicable):
   ```bash
   curl -H "Origin: https://example.com" \
        -H "Access-Control-Request-Method: POST" \
        -X OPTIONS https://your-endpoint.runpod.io/analyze
   ```

**Expected Result**:
- HTTPS connection established
- `/docs` returns 404 (disabled in production)
- CORS headers present (if configured)

**Pass Criteria**:
- ✓ HTTPS enabled
- ✓ API docs disabled
- ✓ CORS configured correctly

---

### Test 10: Error Recovery

**Objective**: Verify the system recovers from errors gracefully.

**Steps**:
1. Send a request that may cause an error (e.g., very large code):
   ```bash
   curl -X POST https://your-endpoint.runpod.io/analyze \
     -H "Content-Type: application/json" \
     -d '{"code": "'$(python -c 'print("x" * 100000)')'"}'
   ```

2. Send a normal request immediately after:
   ```bash
   curl https://your-endpoint.runpod.io/health
   ```

**Expected Result**:
- First request may fail with 500 or 400
- Second request succeeds
- System remains operational

**Pass Criteria**:
- ✓ System doesn't crash
- ✓ Subsequent requests work
- ✓ Error is logged properly

---

### Test 11: Persistent Volume

**Objective**: Verify model weights are cached in persistent volume.

**Steps**:
1. Check logs for model loading:
   ```bash
   runpod logs --tail 100
   ```

2. Look for model download or cache hit messages

3. Trigger a cold start and verify model loads from cache (not downloaded)

**Expected Result**:
- First deployment: Model downloaded to `/runpod-volume/models/`
- Subsequent cold starts: Model loaded from cache
- No repeated downloads

**Pass Criteria**:
- ✓ Model cached in persistent volume
- ✓ Cold starts use cached model
- ✓ No unnecessary downloads

---

### Test 12: Monitoring and Metrics

**Objective**: Verify monitoring and metrics are available.

**Steps**:
1. Check RunPod dashboard for metrics:
   - Request count
   - Request duration
   - Error rate
   - GPU utilization
   - Memory usage

2. View logs:
   ```bash
   runpod logs --follow
   ```

3. Check for structured JSON logs

**Expected Result**:
- Metrics visible in dashboard
- Logs are structured JSON
- Logs contain request_id, execution_time, etc.

**Pass Criteria**:
- ✓ Metrics available in dashboard
- ✓ Logs are structured
- ✓ Key fields present in logs

---

## Test Results Template

Use this template to record test results:

```
Test Date: YYYY-MM-DD
Tester: [Name]
Endpoint: https://your-endpoint.runpod.io
Image Tag: gpu-v1.0.0

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Basic Health Check | ✓ PASS | |
| 2 | Readiness Check | ✓ PASS | |
| 3 | Vulnerability Analysis | ✓ PASS | |
| 4 | Invalid Request Handling | ✓ PASS | |
| 5 | Response Time | ✓ PASS | |
| 6 | Scale to Zero | ✓ PASS | |
| 7 | Cold Start Performance | ✓ PASS | |
| 8 | Concurrent Requests | ✓ PASS | |
| 9 | HTTPS and Security | ✓ PASS | |
| 10 | Error Recovery | ✓ PASS | |
| 11 | Persistent Volume | ✓ PASS | |
| 12 | Monitoring and Metrics | ✓ PASS | |

Overall Result: ✓ PASS / ✗ FAIL

Issues Found:
- [List any issues]

Recommendations:
- [List any recommendations]
```

## Troubleshooting

### Test Failures

If tests fail, check:

1. **Logs**: `runpod logs --tail 100`
2. **Endpoint Status**: `runpod endpoint status`
3. **Configuration**: Verify `runpod.yaml` settings
4. **Image**: Ensure correct image is deployed
5. **Resources**: Check GPU/memory availability

### Common Issues

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Health check fails | Container not started | Wait 60s for initialization |
| Cold start timeout | Model not cached | Pre-download model to volume |
| Analysis fails | vLLM not loaded | Check GPU availability |
| 503 errors | Instance not ready | Wait for readiness check |
| Slow responses | GPU memory low | Reduce `gpu_memory_utilization` |

## Sign-off

After completing all tests:

- [ ] All automated tests pass
- [ ] All manual tests pass
- [ ] No critical issues found
- [ ] Performance meets requirements
- [ ] Security configured correctly
- [ ] Monitoring working
- [ ] Documentation updated

**Approved by**: _______________  
**Date**: _______________

