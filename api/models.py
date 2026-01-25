"""
SecureCodeAI - API Data Models
Pydantic models for request/response validation and serialization.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class AnalyzeRequest(BaseModel):
    """Request model for code analysis."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "query = f\"SELECT * FROM users WHERE username='{username}'\"",
                "file_path": "app/database.py",
                "max_iterations": 3
            }
        }
    )
    
    code: str = Field(
        ..., 
        min_length=1, 
        description="Source code to analyze for vulnerabilities"
    )
    file_path: str = Field(
        default="unknown", 
        description="File path for context (optional)"
    )
    max_iterations: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Maximum patch refinement loops"
    )
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate code is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Code cannot be empty or whitespace only")
        return v


class VulnerabilityResponse(BaseModel):
    """Response model for detected vulnerability."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "app/database.py:42",
                "vuln_type": "SQL Injection",
                "severity": "HIGH",
                "description": "SQL query uses f-string formatting",
                "confidence": 0.9,
                "cwe_id": "CWE-89",
                "hypothesis": "User input is directly interpolated into SQL query without sanitization"
            }
        }
    )
    
    location: str = Field(description="File path and line number")
    vuln_type: str = Field(description="Vulnerability type (e.g., SQL Injection)")
    severity: str = Field(description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)")
    description: str = Field(description="Vulnerability description")
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    cwe_id: Optional[str] = Field(None, description="Common Weakness Enumeration ID")
    hypothesis: Optional[str] = Field(None, description="LLM-generated vulnerability hypothesis")


class PatchResponse(BaseModel):
    """Response model for generated security patch."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "query = \"SELECT * FROM users WHERE username=?\"\ncursor.execute(query, (username,))",
                "diff": "- query = f\"SELECT * FROM users WHERE username='{username}'\"\n+ query = \"SELECT * FROM users WHERE username=?\"\n+ cursor.execute(query, (username,))",
                "verified": True,
                "verification_result": {
                    "verified": True,
                    "execution_time": 2.5
                }
            }
        }
    )
    
    code: str = Field(description="Patched code")
    diff: str = Field(description="Unified diff format")
    verified: bool = Field(description="Whether patch passed symbolic verification")
    verification_result: Optional[Dict[str, Any]] = Field(
        None, 
        description="Verification result details"
    )


class AnalyzeResponse(BaseModel):
    """Response model for code analysis."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "vulnerabilities": [
                    {
                        "location": "app/database.py:42",
                        "vuln_type": "SQL Injection",
                        "severity": "HIGH",
                        "description": "SQL query uses f-string formatting",
                        "confidence": 0.9
                    }
                ],
                "patches": [
                    {
                        "code": "query = \"SELECT * FROM users WHERE username=?\"\ncursor.execute(query, (username,))",
                        "diff": "- query = f\"SELECT * FROM users WHERE username='{username}'\"\n+ query = \"SELECT * FROM users WHERE username=?\"",
                        "verified": True
                    }
                ],
                "execution_time": 15.3,
                "errors": [],
                "logs": ["Scanner Agent: Found 1 potential vulnerabilities"],
                "workflow_complete": True
            }
        }
    )
    
    analysis_id: str = Field(description="Unique analysis identifier")
    vulnerabilities: List[VulnerabilityResponse] = Field(
        default_factory=list,
        description="Detected vulnerabilities"
    )
    patches: List[PatchResponse] = Field(
        default_factory=list,
        description="Generated security patches"
    )
    execution_time: float = Field(description="Total execution time in seconds")
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages during execution"
    )
    logs: List[str] = Field(
        default_factory=list,
        description="Execution logs for debugging"
    )
    workflow_complete: bool = Field(
        default=False,
        description="Whether workflow completed successfully"
    )
    queue_depth: Optional[int] = Field(
        None,
        description="Current request queue depth (included when under load)"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "vllm_loaded": True,
                "workflow_ready": True,
                "uptime_seconds": 3600.5,
                "request_queue_depth": 0
            }
        }
    )
    
    status: Literal["healthy", "unhealthy"] = Field(description="Service health status")
    vllm_loaded: bool = Field(description="Whether vLLM engine is loaded")
    workflow_ready: bool = Field(description="Whether agent workflow is ready")
    uptime_seconds: float = Field(description="Service uptime in seconds")
    request_queue_depth: int = Field(
        default=0,
        description="Current request queue depth"
    )


class ReadinessResponse(BaseModel):
    """Response model for readiness check."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ready": True,
                "components": {
                    "api_server": True,
                    "vllm_engine": True,
                    "agent_workflow": True
                }
            }
        }
    )
    
    ready: bool = Field(description="Whether service is ready to accept requests")
    components: Dict[str, bool] = Field(
        description="Component readiness status"
    )


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "detail": "Code cannot be empty or whitespace only",
                "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "timestamp": "2025-01-24T12:34:56.789Z"
            }
        }
    )
    
    error: str = Field(description="Error type")
    detail: str = Field(description="Error details")
    request_id: str = Field(description="Request identifier for tracking")
    timestamp: str = Field(description="Error timestamp (ISO 8601)")
