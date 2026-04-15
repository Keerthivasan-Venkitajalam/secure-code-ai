"""
SecureCodeAI - Agent State Definition
Defines the state schema for the LangGraph workflow.
"""

from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Vulnerability:
    """Represents a detected vulnerability."""
    location: str  # File path and line number
    vuln_type: str  # e.g., "SQL Injection", "XSS"
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    description: str = ""
    hypothesis: str = ""  # LLM-generated vulnerability hypothesis
    confidence: float = 0.0  # 0.0 to 1.0


@dataclass
class SemanticVulnerability:
    """Represents a vulnerability detected via semantic similarity."""
    location: str  # Line number or range
    vuln_type: str  # Type of vulnerability
    description: str  # Human-readable description
    similar_pattern_id: str  # ID of matching pattern
    similarity_score: float  # Similarity score (0-1)
    suggested_fix: str  # Suggested fix from pattern
    severity: str  # high, medium, low
    confidence: float  # Confidence score (0-1)
    source: str = "semantic_scanner"  # Source of detection


@dataclass
class SimilarPattern:
    """Represents a similar bug pattern from knowledge base."""
    pattern_id: str  # Unique pattern ID
    explanation: str  # What the bug is
    context: str  # Additional context
    buggy_code: str  # Example of buggy code
    correct_code: str  # Example of correct code
    similarity_score: float  # Similarity to query (0-1)
    category: str  # Bug category


@dataclass
class HardwareViolation:
    """Represents a hardware constraint violation."""
    location: str  # Line number
    rule: str  # Rule violated (e.g., "voltage_limit")
    actual_value: Any  # Actual value found
    expected_value: Any  # Expected value/range
    severity: str  # high, medium, low
    message: str  # Human-readable message


@dataclass
class LifecycleViolation:
    """Represents a lifecycle ordering violation."""
    location: str  # Line number
    issue: str  # Type of issue (e.g., "missing_end", "wrong_order")
    begin_line: int  # Line with RDI_BEGIN
    end_line: int  # Line with RDI_END (if present)
    message: str  # Human-readable message


@dataclass
class APITypoSuggestion:
    """Represents an API typo suggestion."""
    location: str  # Line number
    found_api: str  # API name found in code
    suggested_apis: List[str]  # Suggested correct API names
    similarity_scores: List[float]  # Similarity scores for each suggestion
    message: str  # Human-readable message


@dataclass
class Contract:
    """Formal specification for symbolic execution."""
    code: str  # icontract decorator code
    vuln_type: str
    target_function: str


@dataclass
class VerificationResult:
    """Result from symbolic execution."""
    verified: bool  # True = no vulnerability found
    counterexample: Optional[str] = None  # Exploit PoC if vulnerable
    error_message: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class Patch:
    """Generated security patch."""
    code: str  # Patched function code
    diff: str  # Unified diff format
    verified: bool = False  # Has the patch been verified by SymBot?
    verification_result: Optional[VerificationResult] = None


class AgentState(TypedDict, total=False):
    """
    State object passed between LangGraph nodes.
    This maintains all context throughout the workflow.
    """
    # Input
    code: str  # Full source code to analyze
    file_path: str  # Path to the file being analyzed
    binary_path: Optional[str]  # Path to the compiled binary (if applicable)
    
    # Scanner Agent output
    vulnerabilities: List[Vulnerability]  # Detected vulnerability hotspots
    code_slice: Optional[str]  # Extracted vulnerable code slice
    
    # Speculator Agent output
    contracts: List[Contract]  # Generated formal specifications
    
    # SymBot Agent output
    verification_results: List[VerificationResult]
    current_vulnerability: Optional[Vulnerability]  # Currently processing
    
    # Patcher Agent output
    patches: List[Patch]
    current_patch: Optional[Patch]
    
    # Semantic Scanner output (new)
    semantic_vulnerabilities: List[SemanticVulnerability]  # Semantic analysis results
    similar_patterns: List[SimilarPattern]  # Similar patterns from knowledge base
    
    # Validator Suite output (new)
    hardware_violations: List[HardwareViolation]  # Hardware constraint violations
    lifecycle_violations: List[LifecycleViolation]  # Lifecycle ordering violations
    api_typo_suggestions: List[APITypoSuggestion]  # API typo suggestions
    
    # Control flow
    iteration_count: int  # Number of patch attempts
    max_iterations: int  # Maximum refinement loops (default: 3)
    workflow_complete: bool
    
    # Metadata
    errors: List[str]  # Error messages during execution
    logs: List[str]  # Execution logs for debugging
    total_execution_time: float
