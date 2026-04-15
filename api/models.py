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


class SemanticVulnerabilityResponse(BaseModel):
    """Response model for semantic vulnerability detection."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "app/database.py:42",
                "vuln_type": "SQL Injection",
                "description": "SQL query uses string formatting with user input",
                "similar_pattern_id": "001",
                "similarity_score": 0.92,
                "suggested_fix": "Use parameterized queries instead",
                "severity": "HIGH",
                "confidence": 0.9,
                "source": "semantic_scanner"
            }
        }
    )
    
    location: str = Field(description="Line number or range")
    vuln_type: str = Field(description="Type of vulnerability")
    description: str = Field(description="Human-readable description")
    similar_pattern_id: str = Field(description="ID of matching pattern")
    similarity_score: float = Field(description="Similarity score (0.0 to 1.0)")
    suggested_fix: str = Field(description="Suggested fix from pattern")
    severity: str = Field(description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)")
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    source: str = Field(default="semantic_scanner", description="Source of detection")


class HardwareViolationResponse(BaseModel):
    """Response model for hardware constraint violation."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "line 15",
                "rule": "voltage_limit",
                "actual_value": 35.0,
                "expected_value": " 30V",
                "severity": "HIGH",
                "message": "Voltage exceeds maximum limit of 30V"
            }
        }
    )
    
    location: str = Field(description="Line number")
    rule: str = Field(description="Rule violated (e.g., 'voltage_limit')")
    actual_value: Any = Field(description="Actual value found")
    expected_value: Any = Field(description="Expected value/range")
    severity: str = Field(description="Severity level (LOW, MEDIUM, HIGH)")
    message: str = Field(description="Human-readable message")


class LifecycleViolationResponse(BaseModel):
    """Response model for lifecycle ordering violation."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "line 20",
                "issue": "wrong_order",
                "begin_line": 25,
                "end_line": 20,
                "message": "RDI_END appears before RDI_BEGIN"
            }
        }
    )
    
    location: str = Field(description="Line number")
    issue: str = Field(description="Type of issue (e.g., 'missing_end', 'wrong_order')")
    begin_line: int = Field(description="Line with RDI_BEGIN")
    end_line: int = Field(description="Line with RDI_END (if present)")
    message: str = Field(description="Human-readable message")


class APITypoSuggestionResponse(BaseModel):
    """Response model for API typo suggestion."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "line 10",
                "found_api": "RDI_Begn",
                "suggested_apis": ["RDI_BEGIN", "RDI_Begin"],
                "similarity_scores": [0.95, 0.85],
                "message": "Possible typo in API name 'RDI_Begn'. Did you mean 'RDI_BEGIN'?"
            }
        }
    )
    
    location: str = Field(description="Line number")
    found_api: str = Field(description="API name found in code")
    suggested_apis: List[str] = Field(description="Suggested correct API names")
    similarity_scores: List[float] = Field(description="Similarity scores for each suggestion")
    message: str = Field(description="Human-readable message")


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
                "workflow_complete": True,
                "semantic_vulnerabilities": [],
                "hardware_violations": [],
                "lifecycle_violations": [],
                "api_typo_suggestions": []
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
    # New fields for semantic analysis (backward compatible with default_factory)
    semantic_vulnerabilities: List[SemanticVulnerabilityResponse] = Field(
        default_factory=list,
        description="Vulnerabilities detected via semantic similarity"
    )
    hardware_violations: List[HardwareViolationResponse] = Field(
        default_factory=list,
        description="Hardware constraint violations"
    )
    lifecycle_violations: List[LifecycleViolationResponse] = Field(
        default_factory=list,
        description="Lifecycle ordering violations"
    )
    api_typo_suggestions: List[APITypoSuggestionResponse] = Field(
        default_factory=list,
        description="API typo suggestions"
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


class SimilarPatternResponse(BaseModel):
    """Response model for a similar bug pattern."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern_id": "001",
                "explanation": "SQL injection vulnerability in string formatting",
                "context": "Using f-strings or % formatting with user input in SQL queries",
                "buggy_code": "query = f\"SELECT * FROM users WHERE id={user_id}\"",
                "correct_code": "query = \"SELECT * FROM users WHERE id=?\"\ncursor.execute(query, (user_id,))",
                "similarity_score": 0.92,
                "category": "sql_injection"
            }
        }
    )
    
    pattern_id: str = Field(description="Unique pattern identifier")
    explanation: str = Field(description="Description of what the bug is")
    context: str = Field(description="Additional context about when this bug occurs")
    buggy_code: str = Field(description="Example of code with the bug")
    correct_code: str = Field(description="Example of corrected code")
    similarity_score: float = Field(description="Similarity score (0.0 to 1.0)")
    category: str = Field(description="Bug category")


class SearchSimilarRequest(BaseModel):
    """Request model for semantic similarity search."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "SELECT * FROM users WHERE username='{}'",
                "top_k": 5
            }
        }
    )
    
    query: str = Field(
        ...,
        min_length=1,
        description="Search query (code snippet or description)"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of similar patterns to return"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v


class SearchSimilarResponse(BaseModel):
    """Response model for semantic similarity search."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "SELECT * FROM users WHERE username='{}'",
                "similar_patterns": [
                    {
                        "pattern_id": "001",
                        "explanation": "SQL injection vulnerability",
                        "context": "Using string formatting with user input",
                        "buggy_code": "query = f\"SELECT * FROM users WHERE id={user_id}\"",
                        "correct_code": "query = \"SELECT * FROM users WHERE id=?\"\ncursor.execute(query, (user_id,))",
                        "similarity_score": 0.92,
                        "category": "sql_injection"
                    }
                ],
                "count": 1
            }
        }
    )
    
    query: str = Field(description="Original search query")
    similar_patterns: List[SimilarPatternResponse] = Field(
        default_factory=list,
        description="List of similar bug patterns"
    )
    count: int = Field(description="Number of patterns returned")


class KnowledgeBaseStatsResponse(BaseModel):
    """Response model for knowledge base statistics."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pattern_count": 150,
                "categories": {
                    "sql_injection": 25,
                    "xss": 30,
                    "buffer_overflow": 20,
                    "general": 75
                },
                "last_updated": "2025-01-24T10:30:00.000Z"
            }
        }
    )
    
    pattern_count: int = Field(description="Total number of bug patterns in knowledge base")
    categories: Dict[str, int] = Field(description="Pattern count by category")
    last_updated: Optional[str] = Field(
        None,
        description="Last update timestamp (ISO 8601)"
    )
