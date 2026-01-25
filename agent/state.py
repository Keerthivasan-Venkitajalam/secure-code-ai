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
    
    # Control flow
    iteration_count: int  # Number of patch attempts
    max_iterations: int  # Maximum refinement loops (default: 3)
    workflow_complete: bool
    
    # Metadata
    errors: List[str]  # Error messages during execution
    logs: List[str]  # Execution logs for debugging
    total_execution_time: float
