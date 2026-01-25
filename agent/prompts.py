"""
SecureCodeAI - Prompt Template System
SOTA prompt engineering for LLM-powered security analysis.

This module implements structured prompt templates with:
- Few-shot learning examples
- Anti-hallucination instructions
- Configurable generation parameters
- Type-safe template formatting
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class VulnerabilityType(Enum):
    """Enumeration of supported vulnerability types."""
    SQL_INJECTION = "SQL Injection"
    COMMAND_INJECTION = "Command Injection"
    PATH_TRAVERSAL = "Path Traversal"
    XSS = "Cross-Site Scripting"
    SSRF = "Server-Side Request Forgery"
    DESERIALIZATION = "Insecure Deserialization"
    XXE = "XML External Entity"


@dataclass
class PromptTemplate:
    """
    Structured prompt template for LLM generation.
    
    Implements SOTA prompt engineering practices:
    - Clear role definition
    - Structured output format
    - Few-shot examples
    - Anti-hallucination constraints
    - Configurable parameters
    
    Attributes:
        name: Unique identifier for the template
        template: Base prompt template with {placeholders}
        few_shot_examples: Dict mapping vulnerability types to examples
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: Optional system-level instructions
        output_format: Expected output format description
        constraints: List of constraints to prevent hallucination
    """
    
    name: str
    template: str
    few_shot_examples: Dict[str, str] = field(default_factory=dict)
    max_tokens: int = 2048
    temperature: float = 0.2
    system_prompt: Optional[str] = None
    output_format: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    
    def format(self, **kwargs) -> str:
        """
        Format template with provided variables.
        
        Args:
            **kwargs: Template variables to substitute
            
        Returns:
            Formatted prompt string
            
        Raises:
            KeyError: If required template variable is missing
        """
        # Build full prompt
        prompt_parts = []
        
        # Add system prompt if present
        if self.system_prompt:
            prompt_parts.append(f"# System Instructions\n{self.system_prompt}\n")
        
        # Add output format if present
        if self.output_format:
            prompt_parts.append(f"# Output Format\n{self.output_format}\n")
        
        # Add constraints if present
        if self.constraints:
            constraints_text = "\n".join(f"- {c}" for c in self.constraints)
            prompt_parts.append(f"# Constraints\n{constraints_text}\n")
        
        # Add few-shot examples if relevant
        vuln_type = kwargs.get('vuln_type', '')
        if vuln_type and vuln_type in self.few_shot_examples:
            prompt_parts.append(f"# Example\n{self.few_shot_examples[vuln_type]}\n")
        
        # Add main template
        prompt_parts.append(self.template.format(**kwargs))
        
        return "\n".join(prompt_parts)
    
    def get_generation_params(self) -> Dict[str, any]:
        """
        Get generation parameters for this template.
        
        Returns:
            Dictionary with max_tokens and temperature
        """
        return {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }


# ============================================================================
# HYPOTHESIS GENERATION PROMPT
# ============================================================================

HYPOTHESIS_PROMPT = PromptTemplate(
    name="hypothesis_generation",
    system_prompt="""You are a security expert analyzing Python code for vulnerabilities.
Your task is to generate detailed vulnerability hypotheses based on detected patterns.""",
    
    template="""# Code Analysis

```python
{code}
```

**Detected Pattern:** {vuln_type} at line {line_num}
**Function:** {function_name}

# Task

Generate a detailed vulnerability hypothesis that explains:

1. **Security Property Violated**: What security principle is broken?
2. **Attack Vector**: How could an attacker exploit this?
3. **Data Flow**: What user-controlled data reaches the vulnerable operation?
4. **Impact**: What damage could result from exploitation?

# Hypothesis

""",
    
    output_format="""Provide a structured analysis in the following format:

**Security Property:** [e.g., Input validation, Output encoding]
**Attack Vector:** [Specific exploitation technique]
**Data Flow:** [Source → Sink path]
**Impact:** [Confidentiality/Integrity/Availability impact]""",
    
    constraints=[
        "Only analyze the provided code",
        "Base hypothesis on actual code patterns, not speculation",
        "Focus on exploitable vulnerabilities, not code quality issues",
        "Be specific about the data flow path"
    ],
    
    few_shot_examples={
        "SQL Injection": """**Example for SQL Injection:**

**Security Property:** Input sanitization - User input is directly concatenated into SQL query without parameterization
**Attack Vector:** Attacker can inject SQL metacharacters (', --, ;) to manipulate query logic
**Data Flow:** user_input parameter → string concatenation → execute() call
**Impact:** Unauthorized data access, data modification, or database compromise""",
        
        "Command Injection": """**Example for Command Injection:**

**Security Property:** Command sanitization - User input is passed to shell without validation
**Attack Vector:** Attacker can inject shell metacharacters (|, ;, &, `) to execute arbitrary commands
**Data Flow:** filename parameter → f-string formatting → subprocess.call() with shell=True
**Impact:** Remote code execution, system compromise, data exfiltration""",
        
        "Path Traversal": """**Example for Path Traversal:**

**Security Property:** Path validation - User input is used in file path without canonicalization
**Attack Vector:** Attacker can use directory traversal sequences (.., /) to access files outside intended directory
**Data Flow:** user_path parameter → os.path.join() → open() call
**Impact:** Unauthorized file access, information disclosure, potential code execution"""
    },
    
    max_tokens=512,
    temperature=0.2
)


# ============================================================================
# CODE SLICING PROMPT
# ============================================================================

SLICING_PROMPT = PromptTemplate(
    name="code_slicing",
    system_prompt="""You are a program analysis expert specializing in data flow analysis.
Your task is to extract minimal, executable code slices for symbolic execution.""",
    
    template="""# Full Code

```python
{code}
```

# Vulnerability Details

**Type:** {vuln_type}
**Location:** Line {line_num}
**Hypothesis:** {hypothesis}

# Task

Extract a minimal code slice that:
1. Includes the vulnerable function
2. Includes all functions it calls that affect vulnerable data
3. Includes all tainted (user-controlled) variables
4. Generates mock objects for external dependencies (database, network, file I/O)
5. Is syntactically valid and executable

# Code Slice

```python
""",
    
    output_format="""Output ONLY valid Python code. The slice must:
- Be executable independently
- Include necessary imports
- Mock external dependencies
- Preserve the vulnerability for testing""",
    
    constraints=[
        "Output ONLY Python code, no explanations",
        "Include all necessary imports",
        "Mock external dependencies (db, network, files)",
        "Preserve original function signatures",
        "Ensure code is syntactically valid"
    ],
    
    few_shot_examples={
        "SQL Injection": """# Example slice for SQL injection:

import sqlite3
from unittest.mock import Mock

# Mock database connection
def get_db_connection():
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn

# Vulnerable function (preserved)
def search_users(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
""",
        
        "Command Injection": """# Example slice for command injection:

import subprocess
from unittest.mock import Mock, patch

# Vulnerable function (preserved)
def process_file(filename):
    # User-controlled filename passed to shell
    result = subprocess.call(f"cat {filename}", shell=True)
    return result
"""
    },
    
    max_tokens=2048,
    temperature=0.1  # Lower temperature for precise code generation
)


# ============================================================================
# CONTRACT GENERATION PROMPT
# ============================================================================

CONTRACT_PROMPT = PromptTemplate(
    name="contract_generation",
    system_prompt="""You are a formal methods engineer specializing in security contracts.
Your task is to generate icontract decorators that encode security properties.""",
    
    template="""# Vulnerability Analysis

**Type:** {vuln_type}
**Hypothesis:** {hypothesis}
**Target Function:** {function_name}

# Task

Generate icontract decorators that formally specify security properties:
- Use @icontract.require() for preconditions (input validation)
- Use @icontract.ensure() for postconditions (output validation)
- Check for dangerous characters and patterns specific to {vuln_type}

# Contract

```python
""",
    
    output_format="""Output ONLY icontract decorators, no function definition.
Format:
@icontract.require(lambda param: condition, "Error message")
@icontract.ensure(lambda result: condition, "Error message")""",
    
    constraints=[
        "Output ONLY icontract decorators",
        "No function definitions or implementations",
        "Use lambda expressions for conditions",
        "Include descriptive error messages",
        "Check for vulnerability-specific patterns"
    ],
    
    few_shot_examples={
        "SQL Injection": """@icontract.require(lambda query: "'" not in str(query), "Query contains SQL quote")
@icontract.require(lambda query: "--" not in str(query), "Query contains SQL comment")
@icontract.require(lambda query: " OR " not in str(query).upper(), "Query contains OR keyword")
@icontract.require(lambda query: " UNION " not in str(query).upper(), "Query contains UNION keyword")
@icontract.ensure(lambda result: "'" not in str(result), "Result contains SQL quote")
@icontract.ensure(lambda result: "--" not in str(result), "Result contains SQL comment")""",
        
        "Command Injection": """@icontract.require(lambda cmd: "|" not in cmd, "Command contains pipe")
@icontract.require(lambda cmd: ";" not in cmd, "Command contains semicolon")
@icontract.require(lambda cmd: "&" not in cmd, "Command contains ampersand")
@icontract.require(lambda cmd: "`" not in cmd, "Command contains backtick")
@icontract.require(lambda cmd: "$(" not in cmd, "Command contains command substitution")
@icontract.require(lambda cmd: ">" not in cmd, "Command contains redirect")""",
        
        "Path Traversal": """@icontract.require(lambda path: ".." not in path, "Path contains directory traversal")
@icontract.require(lambda path: not path.startswith("/"), "Path is absolute")
@icontract.require(lambda path: not path.startswith("~"), "Path uses home directory")
@icontract.ensure(lambda result: ".." not in str(result), "Result contains directory traversal")"""
    },
    
    max_tokens=512,
    temperature=0.1
)


# ============================================================================
# PATCH GENERATION PROMPT
# ============================================================================

PATCH_PROMPT = PromptTemplate(
    name="patch_generation",
    system_prompt="""You are a security engineer specializing in vulnerability remediation.
Your task is to generate secure patches that fix vulnerabilities while preserving functionality.""",
    
    template="""# Original Code

```python
{code}
```

# Vulnerability Details

**Type:** {vuln_type}
**Hypothesis:** {hypothesis}

# Counterexample (Exploit that works)

```
{counterexample}
```

{previous_attempts}

# Task

Generate a COMPLETE patched version that:
1. Fixes the vulnerability by handling the counterexample
2. Preserves the original function signature and behavior
3. Uses secure coding practices (parameterized queries, input validation, etc.)
4. Maintains the original code style and formatting
5. Adds a comment explaining the security fix

# Secure Patterns for {vuln_type}

{secure_patterns}

# Patched Code

```python
""",
    
    output_format="""Output the COMPLETE patched function with:
- Original function signature preserved
- Security fix implemented
- Comment explaining the fix
- Same code style as original""",
    
    constraints=[
        "Output ONLY Python code, no explanations outside code",
        "Preserve function signature exactly",
        "Add security comment above fix",
        "Use secure coding patterns",
        "Maintain original code style",
        "Ensure patch is syntactically valid"
    ],
    
    few_shot_examples={
        "SQL Injection": """# Secure pattern: Use parameterized queries

def search_users(username):
    # SECURITY FIX: Use parameterized query to prevent SQL injection
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()""",
        
        "Command Injection": """# Secure pattern: Use list arguments with shell=False

def process_file(filename):
    # SECURITY FIX: Use list arguments and shell=False to prevent command injection
    # Validate filename to ensure it doesn't contain path traversal
    if ".." in filename or filename.startswith("/"):
        raise ValueError("Invalid filename")
    
    result = subprocess.call(["cat", filename], shell=False)
    return result""",
        
        "Path Traversal": """# Secure pattern: Canonicalize and validate paths

import os

def read_file(user_path):
    # SECURITY FIX: Canonicalize path and validate it's within allowed directory
    base_dir = os.path.abspath("/var/app/data")
    requested_path = os.path.abspath(os.path.join(base_dir, user_path))
    
    # Ensure path is within base directory
    if not requested_path.startswith(base_dir):
        raise ValueError("Path traversal detected")
    
    with open(requested_path, 'r') as f:
        return f.read()"""
    },
    
    max_tokens=4096,  # Larger for complete function generation
    temperature=0.2
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_secure_patterns(vuln_type: str) -> str:
    """
    Get secure coding patterns for a specific vulnerability type.
    
    Args:
        vuln_type: Type of vulnerability
        
    Returns:
        Formatted string with secure patterns
    """
    patterns = {
        "SQL Injection": """- Use parameterized queries with placeholders (?, %s)
- Use ORM methods (e.g., SQLAlchemy query builder)
- Never concatenate user input into SQL strings
- Validate and sanitize all user inputs""",
        
        "Command Injection": """- Use subprocess with list arguments and shell=False
- Avoid shell=True entirely
- Validate and whitelist allowed commands
- Use shlex.quote() for shell escaping if absolutely necessary""",
        
        "Path Traversal": """- Use os.path.abspath() to canonicalize paths
- Validate paths are within allowed directory
- Use os.path.normpath() to remove .. sequences
- Reject absolute paths and home directory paths""",
        
        "XSS": """- Use HTML escaping for all user input in HTML context
- Use JavaScript escaping for user input in JS context
- Use Content Security Policy headers
- Validate and sanitize all user inputs""",
        
        "SSRF": """- Validate and whitelist allowed URLs/domains
- Use URL parsing to extract and validate components
- Block private IP ranges (127.0.0.1, 10.0.0.0/8, etc.)
- Implement request timeouts"""
    }
    
    return patterns.get(vuln_type, "- Follow secure coding best practices\n- Validate all user inputs\n- Use security libraries")


def format_previous_attempts(attempts: List[str]) -> str:
    """
    Format previous failed patch attempts for feedback.
    
    Args:
        attempts: List of previous patch attempts
        
    Returns:
        Formatted string with previous attempts
    """
    if not attempts:
        return ""
    
    formatted = "# Previous Failed Attempts\n\n"
    for i, attempt in enumerate(attempts, 1):
        formatted += f"## Attempt {i}\n```python\n{attempt}\n```\n\n"
    
    formatted += "**Note:** Generate a different approach that addresses the issues in previous attempts.\n"
    
    return formatted


# Export all templates
__all__ = [
    'PromptTemplate',
    'VulnerabilityType',
    'HYPOTHESIS_PROMPT',
    'SLICING_PROMPT',
    'CONTRACT_PROMPT',
    'PATCH_PROMPT',
    'get_secure_patterns',
    'format_previous_attempts'
]
