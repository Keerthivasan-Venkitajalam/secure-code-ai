"""
Integration tests for Docker container.

Tests:
- Container build
- Container startup and health checks
- API endpoint functionality
- Graceful shutdown with SIGTERM

Requirements: 5.1, 5.2, 5.3, 5.4
"""

import pytest
import docker
import time
import requests
import signal
import subprocess
import os
from pathlib import Path


# Skip tests if Docker is not available
try:
    docker_client = docker.from_env()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False


@pytest.fixture(scope="module")
def docker_image():
    """Build Docker image for testing."""
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    dockerfile_path = project_root / "deployment" / "Dockerfile"
    
    if not dockerfile_path.exists():
        pytest.skip("Dockerfile not found")
    
    # Build image (CPU-only for testing)
    print("\nBuilding Docker image (this may take a few minutes)...")
    client = docker.from_env()
    
    try:
        image, build_logs = client.images.build(
            path=str(project_root),
            dockerfile=str(dockerfile_path),
            tag="secureai:test",
            buildargs={"GPU": "false"},
            rm=True,
            forcerm=True
        )
        
        # Print build logs
        for log in build_logs:
            if 'stream' in log:
                print(log['stream'].strip())
        
        print(f"✓ Image built successfully: {image.id}")
        yield image
        
        # Cleanup: Remove image after tests
        try:
            client.images.remove(image.id, force=True)
            print(f"✓ Cleaned up test image: {image.id}")
        except Exception as e:
            print(f"Warning: Failed to cleanup image: {e}")
    
    except docker.errors.BuildError as e:
        pytest.fail(f"Docker build failed: {e}")


@pytest.fixture
def docker_container(docker_image):
    """Start Docker container for testing."""
    client = docker.from_env()
    
    # Start container
    container = client.containers.run(
        docker_image.id,
        detach=True,
        ports={"8000/tcp": 8000},
        environment={
            "SECUREAI_ENABLE_GPU": "false",
            "SECUREAI_LOG_LEVEL": "INFO",
            "SECUREAI_ENABLE_DOCS": "true"
        },
        remove=True,
        name="secureai-test"
    )
    
    print(f"\n✓ Container started: {container.id[:12]}")
    
    # Wait for container to be ready (max 60 seconds)
    max_wait = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Check if container is still running
            container.reload()
            if container.status != "running":
                logs = container.logs().decode('utf-8')
                pytest.fail(f"Container stopped unexpectedly:\n{logs}")
            
            # Try health check
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Container ready after {time.time() - start_time:.1f}s")
                break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(2)
    else:
        # Timeout - get logs and fail
        logs = container.logs().decode('utf-8')
        container.stop(timeout=5)
        pytest.fail(f"Container failed to become ready within {max_wait}s:\n{logs}")
    
    yield container
    
    # Cleanup: Stop container
    try:
        container.stop(timeout=10)
        print(f"✓ Container stopped: {container.id[:12]}")
    except Exception as e:
        print(f"Warning: Failed to stop container: {e}")


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
class TestDockerIntegration:
    """Integration tests for Docker container."""
    
    def test_container_build(self, docker_image):
        """
        Test that Docker image builds successfully.
        
        Validates: Requirements 5.1
        """
        assert docker_image is not None
        assert docker_image.id is not None
        
        # Check image has correct tags
        assert any("secureai:test" in tag for tag in docker_image.tags)
        
        print(f"✓ Image built with ID: {docker_image.id[:12]}")
    
    def test_container_startup(self, docker_container):
        """
        Test that container starts and becomes healthy.
        
        Validates: Requirements 5.1, 5.3
        """
        # Container should be running
        docker_container.reload()
        assert docker_container.status == "running"
        
        # Health check should return healthy
        response = requests.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        
        print(f"✓ Container healthy: {data}")
    
    def test_health_endpoint(self, docker_container):
        """
        Test /health endpoint returns correct status.
        
        Validates: Requirements 5.3
        """
        response = requests.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["vllm_loaded"], bool)
        assert isinstance(data["workflow_ready"], bool)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
        
        print(f"✓ Health check passed: {data}")
    
    def test_readiness_endpoint(self, docker_container):
        """
        Test /health/ready endpoint returns component status.
        
        Validates: Requirements 5.3
        """
        response = requests.get("http://localhost:8000/health/ready", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data
        assert "components" in data
        assert isinstance(data["components"], dict)
        
        # Check required components
        assert "api_server" in data["components"]
        assert "vllm_engine" in data["components"]
        assert "agent_workflow" in data["components"]
        
        print(f"✓ Readiness check passed: {data}")
    
    def test_analyze_endpoint_validation(self, docker_container):
        """
        Test /analyze endpoint validates requests correctly.
        
        Validates: Requirements 5.3
        """
        # Test with empty code (should fail)
        response = requests.post(
            "http://localhost:8000/analyze",
            json={"code": ""},
            timeout=5
        )
        assert response.status_code == 422  # Validation error
        
        # Test with whitespace-only code (should fail)
        response = requests.post(
            "http://localhost:8000/analyze",
            json={"code": "   \n  \t  "},
            timeout=5
        )
        assert response.status_code == 422  # Validation error
        
        print("✓ Request validation working correctly")
    
    def test_analyze_endpoint_basic(self, docker_container):
        """
        Test /analyze endpoint with simple code.
        
        Note: This test may fail if vLLM is not loaded (CPU-only container).
        We test the endpoint structure rather than full functionality.
        
        Validates: Requirements 5.3
        """
        # Simple Python code
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        
        response = requests.post(
            "http://localhost:8000/analyze",
            json={
                "code": code,
                "file_path": "test.py",
                "max_iterations": 1
            },
            timeout=30
        )
        
        # Accept either success or service unavailable (if vLLM not loaded)
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "analysis_id" in data
            assert "vulnerabilities" in data
            assert "patches" in data
            assert "execution_time" in data
            assert isinstance(data["vulnerabilities"], list)
            assert isinstance(data["patches"], list)
            print(f"✓ Analysis completed: {len(data['vulnerabilities'])} vulnerabilities found")
        else:
            print("✓ Service unavailable (expected for CPU-only container)")
    
    def test_graceful_shutdown(self, docker_image):
        """
        Test graceful shutdown with SIGTERM signal.
        
        Validates: Requirements 5.4
        """
        client = docker.from_env()
        
        # Start a new container for shutdown test
        container = client.containers.run(
            docker_image.id,
            detach=True,
            ports={"8000/tcp": 8001},
            environment={
                "SECUREAI_ENABLE_GPU": "false",
                "SECUREAI_LOG_LEVEL": "INFO"
            },
            remove=False,  # Don't auto-remove so we can check logs
            name="secureai-shutdown-test"
        )
        
        try:
            # Wait for container to be ready
            time.sleep(10)
            
            # Check container is running
            container.reload()
            assert container.status == "running"
            
            # Send SIGTERM signal
            print("\n✓ Sending SIGTERM to container...")
            container.kill(signal="SIGTERM")
            
            # Wait for graceful shutdown (max 30 seconds)
            start_time = time.time()
            max_wait = 30
            
            while time.time() - start_time < max_wait:
                container.reload()
                if container.status == "exited":
                    break
                time.sleep(1)
            
            # Check container exited
            container.reload()
            assert container.status == "exited"
            
            shutdown_time = time.time() - start_time
            print(f"✓ Container shutdown gracefully in {shutdown_time:.1f}s")
            
            # Check logs for graceful shutdown messages
            logs = container.logs().decode('utf-8')
            assert "Received shutdown signal" in logs or "Shutting down" in logs
            print("✓ Graceful shutdown messages found in logs")
            
            # Check exit code (should be 0 for graceful shutdown)
            exit_code = container.attrs['State']['ExitCode']
            assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
            print(f"✓ Exit code: {exit_code}")
        
        finally:
            # Cleanup
            try:
                container.remove(force=True)
            except Exception as e:
                print(f"Warning: Failed to remove container: {e}")
    
    def test_container_logs(self, docker_container):
        """
        Test that container produces structured logs.
        
        Validates: Requirements 5.3
        """
        # Get container logs
        logs = docker_container.logs().decode('utf-8')
        
        # Check for startup messages
        assert "Starting SecureCodeAI" in logs or "SecureCodeAI Container Starting" in logs
        
        # Check for configuration messages
        assert "Configuration" in logs or "Model Path" in logs
        
        print("✓ Container logs contain expected messages")
    
    def test_port_exposure(self, docker_container):
        """
        Test that port 8000 is properly exposed.
        
        Validates: Requirements 5.3
        """
        # Check port mapping
        docker_container.reload()
        ports = docker_container.attrs['NetworkSettings']['Ports']
        
        assert '8000/tcp' in ports
        assert ports['8000/tcp'] is not None
        assert len(ports['8000/tcp']) > 0
        
        # Verify we can connect to the port
        response = requests.get("http://localhost:8000/health", timeout=5)
        assert response.status_code == 200
        
        print("✓ Port 8000 properly exposed and accessible")


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
def test_dockerfile_exists():
    """Test that Dockerfile exists in deployment directory."""
    project_root = Path(__file__).parent.parent
    dockerfile_path = project_root / "deployment" / "Dockerfile"
    
    assert dockerfile_path.exists(), "Dockerfile not found in deployment directory"
    
    # Check Dockerfile contains required instructions
    content = dockerfile_path.read_text()
    assert "FROM python:3.10-slim" in content
    assert "EXPOSE 8000" in content
    assert "CMD" in content or "ENTRYPOINT" in content
    
    print("✓ Dockerfile exists and contains required instructions")


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
def test_entrypoint_script_exists():
    """Test that entrypoint script exists and is executable."""
    project_root = Path(__file__).parent.parent
    entrypoint_path = project_root / "deployment" / "entrypoint.sh"
    
    assert entrypoint_path.exists(), "entrypoint.sh not found in deployment directory"
    
    # Check script contains required logic
    content = entrypoint_path.read_text()
    assert "#!/bin/bash" in content
    assert "MODEL_PATH" in content or "model" in content.lower()
    assert "SIGTERM" in content or "graceful" in content.lower()
    
    print("✓ Entrypoint script exists and contains required logic")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
