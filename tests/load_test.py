"""
Load testing script for SecureCodeAI API using Locust.

This script simulates concurrent users making requests to the /analyze endpoint
to measure throughput, latency, and system behavior under load.

Usage:
    # Install locust first
    pip install locust
    
    # Run load test with 10 concurrent users
    locust -f tests/load_test.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=60s --headless
    
    # Run with web UI
    locust -f tests/load_test.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import json
import time
from datetime import datetime


# Sample code snippets for testing
SAMPLE_CODES = [
    # SQL Injection vulnerability
    """
def get_user(username):
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return db.execute(query)
""",
    # Command Injection vulnerability
    """
import os

def ping_host(host):
    os.system(f"ping -c 1 {host}")
""",
    # Path Traversal vulnerability
    """
def read_file(filename):
    with open(f"/var/www/uploads/{filename}", 'r') as f:
        return f.read()
""",
    # XSS vulnerability
    """
from flask import Flask, request

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q')
    return f"<h1>Results for: {query}</h1>"
""",
    # Hardcoded credentials
    """
def connect_to_db():
    username = "admin"
    password = "password123"
    return connect(username, password)
""",
    # Simple safe code
    """
def add_numbers(a, b):
    return a + b
""",
]


class SecureCodeAIUser(HttpUser):
    """
    Simulated user that makes requests to the SecureCodeAI API.
    """
    
    # Wait between 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.request_count = 0
        self.start_time = time.time()
    
    @task(10)
    def analyze_code(self):
        """
        Main task: Analyze code for vulnerabilities.
        Weight: 10 (most common operation)
        """
        code = SAMPLE_CODES[self.request_count % len(SAMPLE_CODES)]
        
        payload = {
            "code": code,
            "file_path": f"test_{self.request_count}.py",
            "max_iterations": 3
        }
        
        with self.client.post(
            "/analyze",
            json=payload,
            catch_response=True,
            name="/analyze"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Validate response structure
                    required_fields = [
                        "analysis_id",
                        "vulnerabilities",
                        "patches",
                        "execution_time",
                        "errors",
                        "logs"
                    ]
                    
                    for field in required_fields:
                        if field not in data:
                            response.failure(f"Missing field: {field}")
                            return
                    
                    # Log execution time
                    exec_time = data.get("execution_time", 0)
                    if exec_time > 10.0:
                        response.failure(f"Execution time too high: {exec_time}s")
                    else:
                        response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 429:
                # Rate limit hit - this is expected under load
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
        
        self.request_count += 1
    
    @task(3)
    def check_health(self):
        """
        Health check task.
        Weight: 3 (less frequent than analyze)
        """
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Validate health response
                    required_fields = [
                        "status",
                        "vllm_loaded",
                        "workflow_ready",
                        "uptime_seconds",
                        "request_queue_depth"
                    ]
                    
                    for field in required_fields:
                        if field not in data:
                            response.failure(f"Missing field: {field}")
                            return
                    
                    response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def check_readiness(self):
        """
        Readiness check task.
        Weight: 1 (least frequent)
        """
        with self.client.get(
            "/health/ready",
            catch_response=True,
            name="/health/ready"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Validate readiness response
                    if "ready" not in data or "components" not in data:
                        response.failure("Missing required fields")
                        return
                    
                    response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


# Event listeners for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print(f"\n{'='*80}")
    print(f"Load Test Started: {datetime.now().isoformat()}")
    print(f"Target Host: {environment.host}")
    print(f"{'='*80}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    print(f"\n{'='*80}")
    print(f"Load Test Completed: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Print summary statistics
    stats = environment.stats
    
    print("Summary Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"  Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"  Median Response Time (p50): {stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"  95th Percentile (p95): {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  99th Percentile (p99): {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    print(f"\nPer-Endpoint Statistics:")
    
    for name, entry in stats.entries.items():
        if entry.num_requests > 0:
            print(f"\n  {name}:")
            print(f"    Requests: {entry.num_requests}")
            print(f"    Failures: {entry.num_failures}")
            print(f"    Avg Response Time: {entry.avg_response_time:.2f}ms")
            print(f"    p50: {entry.get_response_time_percentile(0.5):.2f}ms")
            print(f"    p95: {entry.get_response_time_percentile(0.95):.2f}ms")
            print(f"    p99: {entry.get_response_time_percentile(0.99):.2f}ms")


if __name__ == "__main__":
    # This allows running the script directly for testing
    import os
    os.system("locust -f tests/load_test.py --host=http://localhost:8000")
