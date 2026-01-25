"""
Unit tests for health check endpoints.
Tests /health and /health/ready endpoints with various service states.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
import time

from api.server import app, service_state
from api.models import AnalyzeResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_service_state():
    """Reset service state before each test."""
    service_state.vllm_loaded = False
    service_state.workflow_ready = False
    service_state.request_queue_depth = 0
    service_state.start_time = time.time()
    yield
    # Cleanup after test
    service_state.vllm_loaded = False
    service_state.workflow_ready = False
    service_state.request_queue_depth = 0


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_unhealthy_when_vllm_not_loaded(self, client):
        """Test /health returns unhealthy when vLLM not loaded."""
        service_state.vllm_loaded = False
        service_state.workflow_ready = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["vllm_loaded"] is False
        assert data["workflow_ready"] is True
        assert data["uptime_seconds"] >= 0
        assert data["request_queue_depth"] == 0
    
    def test_health_unhealthy_when_workflow_not_ready(self, client):
        """Test /health returns unhealthy when workflow not ready."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["vllm_loaded"] is True
        assert data["workflow_ready"] is False
    
    def test_health_healthy_when_all_components_ready(self, client):
        """Test /health returns healthy when all components ready."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["vllm_loaded"] is True
        assert data["workflow_ready"] is True
        assert data["uptime_seconds"] >= 0
        assert data["request_queue_depth"] == 0
    
    def test_health_reports_queue_depth(self, client):
        """Test /health reports current request queue depth."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = True
        service_state.request_queue_depth = 5
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["request_queue_depth"] == 5
    
    def test_health_reports_uptime(self, client):
        """Test /health reports accurate uptime."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = True
        service_state.start_time = time.time() - 100.0  # 100 seconds ago
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Uptime should be approximately 100 seconds
        assert data["uptime_seconds"] >= 100.0
        assert data["uptime_seconds"] < 101.0  # Allow small margin
    
    def test_health_unhealthy_when_both_not_ready(self, client):
        """Test /health returns unhealthy when both components not ready."""
        service_state.vllm_loaded = False
        service_state.workflow_ready = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["vllm_loaded"] is False
        assert data["workflow_ready"] is False


class TestReadinessEndpoint:
    """Test /health/ready endpoint."""
    
    def test_readiness_not_ready_when_vllm_not_loaded(self, client):
        """Test /health/ready returns not ready when vLLM not loaded."""
        service_state.vllm_loaded = False
        service_state.workflow_ready = True
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ready"] is False
        assert data["components"]["api_server"] is True
        assert data["components"]["vllm_engine"] is False
        assert data["components"]["agent_workflow"] is True
    
    def test_readiness_not_ready_when_workflow_not_ready(self, client):
        """Test /health/ready returns not ready when workflow not ready."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = False
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ready"] is False
        assert data["components"]["api_server"] is True
        assert data["components"]["vllm_engine"] is True
        assert data["components"]["agent_workflow"] is False
    
    def test_readiness_ready_when_all_components_ready(self, client):
        """Test /health/ready returns ready when all components ready."""
        service_state.vllm_loaded = True
        service_state.workflow_ready = True
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ready"] is True
        assert data["components"]["api_server"] is True
        assert data["components"]["vllm_engine"] is True
        assert data["components"]["agent_workflow"] is True
    
    def test_readiness_not_ready_when_both_not_ready(self, client):
        """Test /health/ready returns not ready when both components not ready."""
        service_state.vllm_loaded = False
        service_state.workflow_ready = False
        
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ready"] is False
        assert data["components"]["api_server"] is True
        assert data["components"]["vllm_engine"] is False
        assert data["components"]["agent_workflow"] is False
    
    def test_readiness_api_server_always_true(self, client):
        """Test /health/ready always reports api_server as true."""
        # Test with various states
        for vllm_state in [True, False]:
            for workflow_state in [True, False]:
                service_state.vllm_loaded = vllm_state
                service_state.workflow_ready = workflow_state
                
                response = client.get("/health/ready")
                
                assert response.status_code == 200
                data = response.json()
                
                # API server should always be true if endpoint responds
                assert data["components"]["api_server"] is True


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "SecureCodeAI API"
        assert data["version"] == "0.1.0"
        assert "endpoints" in data
        assert data["endpoints"]["analyze"] == "/analyze"
        assert data["endpoints"]["health"] == "/health"
        assert data["endpoints"]["readiness"] == "/health/ready"


class TestAnalyzeEndpoint:
    """Test /analyze endpoint (placeholder tests)."""
    
    def test_analyze_accepts_valid_request(self, client):
        """Test /analyze accepts valid request."""
        # Mock orchestrator
        from api import server
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-123",
                vulnerabilities=[],
                patches=[],
                execution_time=0.1,
                errors=[],
                logs=[],
                workflow_complete=False
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        request_data = {
            "code": "print('hello world')",
            "file_path": "test.py",
            "max_iterations": 3
        }
        
        response = client.post("/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analysis_id" in data
        assert "vulnerabilities" in data
        assert "patches" in data
        assert "execution_time" in data
        assert data["workflow_complete"] is False  # Not yet implemented
    
    def test_analyze_rejects_empty_code(self, client):
        """Test /analyze rejects empty code."""
        request_data = {
            "code": "",
            "file_path": "test.py"
        }
        
        response = client.post("/analyze", json=request_data)
        
        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422
    
    def test_analyze_uses_default_values(self, client):
        """Test /analyze uses default values when not provided."""
        # Mock orchestrator
        from api import server
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-123",
                vulnerabilities=[],
                patches=[],
                execution_time=0.1,
                errors=[],
                logs=[],
                workflow_complete=False
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        request_data = {
            "code": "print('hello world')"
        }
        
        response = client.post("/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should succeed with defaults
        assert "analysis_id" in data
    
    def test_analyze_increments_queue_depth(self, client):
        """Test /analyze increments and decrements queue depth."""
        # Mock orchestrator
        from api import server
        mock_orchestrator = Mock()
        mock_orchestrator.analyze_code = AsyncMock(
            return_value=AnalyzeResponse(
                analysis_id="test-123",
                vulnerabilities=[],
                patches=[],
                execution_time=0.1,
                errors=[],
                logs=[],
                workflow_complete=False
            )
        )
        server.service_state.orchestrator = mock_orchestrator
        
        initial_depth = server.service_state.request_queue_depth
        
        request_data = {
            "code": "print('hello world')"
        }
        
        response = client.post("/analyze", json=request_data)
        
        assert response.status_code == 200
        
        # Queue depth should be back to initial after request completes
        assert server.service_state.request_queue_depth == initial_depth
