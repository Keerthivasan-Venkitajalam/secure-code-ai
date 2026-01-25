"""
Unit tests for API data models.
Tests request/response validation and serialization.
"""

import pytest
from pydantic import ValidationError

from api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    VulnerabilityResponse,
    PatchResponse,
    HealthResponse,
    ReadinessResponse,
    ErrorResponse
)


class TestAnalyzeRequest:
    """Test AnalyzeRequest validation."""
    
    def test_valid_request(self):
        """Test valid analyze request."""
        request = AnalyzeRequest(
            code="print('hello')",
            file_path="test.py",
            max_iterations=3
        )
        assert request.code == "print('hello')"
        assert request.file_path == "test.py"
        assert request.max_iterations == 3
    
    def test_default_values(self):
        """Test default values are applied."""
        request = AnalyzeRequest(code="print('hello')")
        assert request.file_path == "unknown"
        assert request.max_iterations == 3
    
    def test_empty_code_rejected(self):
        """Test empty code is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(code="")
        
        errors = exc_info.value.errors()
        # Check for either min_length validation or custom validator message
        assert any("String should have at least 1 character" in str(e) or "Code cannot be empty" in str(e) for e in errors)
    
    def test_whitespace_only_code_rejected(self):
        """Test whitespace-only code is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AnalyzeRequest(code="   \n\t  ")
        
        errors = exc_info.value.errors()
        assert any("Code cannot be empty" in str(e) for e in errors)
    
    def test_max_iterations_bounds(self):
        """Test max_iterations must be between 1 and 10."""
        # Valid bounds
        AnalyzeRequest(code="print('hello')", max_iterations=1)
        AnalyzeRequest(code="print('hello')", max_iterations=10)
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            AnalyzeRequest(code="print('hello')", max_iterations=0)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            AnalyzeRequest(code="print('hello')", max_iterations=11)
    
    def test_invalid_type_rejected(self):
        """Test invalid types are rejected."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(code=123)  # code must be string
        
        with pytest.raises(ValidationError):
            AnalyzeRequest(code="print('hello')", max_iterations="three")  # must be int


class TestVulnerabilityResponse:
    """Test VulnerabilityResponse serialization."""
    
    def test_valid_vulnerability(self):
        """Test valid vulnerability response."""
        vuln = VulnerabilityResponse(
            location="test.py:42",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Dangerous SQL query",
            confidence=0.9,
            cwe_id="CWE-89",
            hypothesis="User input not sanitized"
        )
        
        assert vuln.location == "test.py:42"
        assert vuln.vuln_type == "SQL Injection"
        assert vuln.severity == "HIGH"
        assert vuln.confidence == 0.9
    
    def test_optional_fields(self):
        """Test optional fields can be None."""
        vuln = VulnerabilityResponse(
            location="test.py:42",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Dangerous SQL query",
            confidence=0.9
        )
        
        assert vuln.cwe_id is None
        assert vuln.hypothesis is None
    
    def test_serialization(self):
        """Test vulnerability can be serialized to dict."""
        vuln = VulnerabilityResponse(
            location="test.py:42",
            vuln_type="SQL Injection",
            severity="HIGH",
            description="Dangerous SQL query",
            confidence=0.9
        )
        
        data = vuln.model_dump()
        assert isinstance(data, dict)
        assert data["location"] == "test.py:42"
        assert data["vuln_type"] == "SQL Injection"


class TestPatchResponse:
    """Test PatchResponse serialization."""
    
    def test_valid_patch(self):
        """Test valid patch response."""
        patch = PatchResponse(
            code="fixed_code = sanitize(user_input)",
            diff="- bad_code\n+ fixed_code",
            verified=True,
            verification_result={"verified": True, "time": 2.5}
        )
        
        assert patch.code == "fixed_code = sanitize(user_input)"
        assert patch.verified is True
        assert patch.verification_result["verified"] is True
    
    def test_unverified_patch(self):
        """Test unverified patch."""
        patch = PatchResponse(
            code="fixed_code",
            diff="- bad\n+ fixed",
            verified=False
        )
        
        assert patch.verified is False
        assert patch.verification_result is None


class TestAnalyzeResponse:
    """Test AnalyzeResponse serialization."""
    
    def test_valid_response(self):
        """Test valid analyze response."""
        response = AnalyzeResponse(
            analysis_id="test-123",
            vulnerabilities=[
                VulnerabilityResponse(
                    location="test.py:42",
                    vuln_type="SQL Injection",
                    severity="HIGH",
                    description="Dangerous SQL query",
                    confidence=0.9
                )
            ],
            patches=[
                PatchResponse(
                    code="fixed_code",
                    diff="- bad\n+ fixed",
                    verified=True
                )
            ],
            execution_time=15.3,
            errors=[],
            logs=["Scanner: Found 1 vulnerability"],
            workflow_complete=True
        )
        
        assert response.analysis_id == "test-123"
        assert len(response.vulnerabilities) == 1
        assert len(response.patches) == 1
        assert response.execution_time == 15.3
        assert response.workflow_complete is True
    
    def test_empty_results(self):
        """Test response with no vulnerabilities or patches."""
        response = AnalyzeResponse(
            analysis_id="test-123",
            execution_time=5.0
        )
        
        assert response.vulnerabilities == []
        assert response.patches == []
        assert response.errors == []
        assert response.logs == []
        assert response.workflow_complete is False
    
    def test_with_errors(self):
        """Test response with errors."""
        response = AnalyzeResponse(
            analysis_id="test-123",
            execution_time=2.0,
            errors=["Scanner failed", "Workflow aborted"],
            workflow_complete=False
        )
        
        assert len(response.errors) == 2
        assert "Scanner failed" in response.errors


class TestHealthResponse:
    """Test HealthResponse serialization."""
    
    def test_healthy_status(self):
        """Test healthy status response."""
        health = HealthResponse(
            status="healthy",
            vllm_loaded=True,
            workflow_ready=True,
            uptime_seconds=3600.5,
            request_queue_depth=0
        )
        
        assert health.status == "healthy"
        assert health.vllm_loaded is True
        assert health.workflow_ready is True
    
    def test_unhealthy_status(self):
        """Test unhealthy status response."""
        health = HealthResponse(
            status="unhealthy",
            vllm_loaded=False,
            workflow_ready=False,
            uptime_seconds=10.0
        )
        
        assert health.status == "unhealthy"
        assert health.vllm_loaded is False
    
    def test_queue_depth(self):
        """Test queue depth reporting."""
        health = HealthResponse(
            status="healthy",
            vllm_loaded=True,
            workflow_ready=True,
            uptime_seconds=100.0,
            request_queue_depth=5
        )
        
        assert health.request_queue_depth == 5


class TestReadinessResponse:
    """Test ReadinessResponse serialization."""
    
    def test_ready_status(self):
        """Test ready status response."""
        readiness = ReadinessResponse(
            ready=True,
            components={
                "api_server": True,
                "vllm_engine": True,
                "agent_workflow": True
            }
        )
        
        assert readiness.ready is True
        assert all(readiness.components.values())
    
    def test_not_ready_status(self):
        """Test not ready status response."""
        readiness = ReadinessResponse(
            ready=False,
            components={
                "api_server": True,
                "vllm_engine": False,
                "agent_workflow": False
            }
        )
        
        assert readiness.ready is False
        assert readiness.components["api_server"] is True
        assert readiness.components["vllm_engine"] is False


class TestErrorResponse:
    """Test ErrorResponse serialization."""
    
    def test_error_response(self):
        """Test error response."""
        error = ErrorResponse(
            error="ValidationError",
            detail="Invalid input",
            request_id="test-123",
            timestamp="2025-01-24T12:34:56.789Z"
        )
        
        assert error.error == "ValidationError"
        assert error.detail == "Invalid input"
        assert error.request_id == "test-123"
        assert "2025-01-24" in error.timestamp



# Property-Based Tests
from hypothesis import given, strategies as st


@given(
    code=st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=0, max_size=100).filter(lambda x: x.strip() == ""),  # Whitespace only
    )
)
def test_property_invalid_input_rejection(code):
    """
    Property 3: Invalid Input Rejection
    
    Feature: backend-api-deployment, Property 3: Invalid Input Rejection
    Validates: Requirements 1.2, 1.3
    
    For any invalid code input (empty or whitespace-only),
    the AnalyzeRequest model SHALL reject it with a ValidationError.
    """
    with pytest.raises(ValidationError):
        AnalyzeRequest(code=code)


@given(
    max_iterations=st.one_of(
        st.integers(max_value=0),  # Too low
        st.integers(min_value=11),  # Too high
    )
)
def test_property_max_iterations_bounds(max_iterations):
    """
    Property 3: Invalid Input Rejection (max_iterations bounds)
    
    Feature: backend-api-deployment, Property 3: Invalid Input Rejection
    Validates: Requirements 1.2, 1.3
    
    For any max_iterations value outside the valid range [1, 10],
    the AnalyzeRequest model SHALL reject it with a ValidationError.
    """
    with pytest.raises(ValidationError):
        AnalyzeRequest(code="print('hello')", max_iterations=max_iterations)
