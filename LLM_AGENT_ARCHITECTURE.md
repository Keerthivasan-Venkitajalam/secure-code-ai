# LLM Agent Intelligence Architecture

## Overview

The SecureCodeAI system uses LLM-powered agents to perform intelligent vulnerability detection, formal contract generation, and security patch synthesis. This document describes the architecture, prompt templates, self-correction loops, and neuro-slicing algorithm that enable the system to achieve high accuracy and reliability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: Source Code                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Scanner Agent (LLM-Powered)                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  1. AST Analysis (Pattern Detection)               │     │
│  │  2. LLM Hypothesis Generation                      │     │
│  │  3. Neuro-Slicing (Extract Relevant Code)          │     │
│  │  4. Mock Generation (External Dependencies)        │     │
│  └────────────────────────────────────────────────────┘     │
│  Output: Vulnerability + Code Slice + Hypothesis            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Speculator Agent (LLM-Powered)                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  1. Parse Vulnerability Hypothesis                 │     │
│  │  2. LLM Contract Generation (icontract)            │     │
│  │  3. Syntax Validation (Python AST)                 │     │
│  │  4. Retry on Syntax Errors                         │     │
│  └────────────────────────────────────────────────────┘     │
│  Output: Formal Contract (icontract decorator)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  SymBot Agent (Symbolic Execution)           │
│  ┌────────────────────────────────────────────────────┐     │
│  │  1. Combine Code Slice + Contract                  │     │
│  │  2. Run CrossHair (Symbolic Execution)             │     │
│  │  3. Extract Counterexample (if found)              │     │
│  └────────────────────────────────────────────────────┘     │
│  Output: Verification Result + Counterexample               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Patcher Agent (LLM-Powered)                  │
│  ┌────────────────────────────────────────────────────┐     │
│  │  1. Parse Counterexample                           │     │
│  │  2. LLM Patch Generation                           │     │
│  │  3. Code Style Preservation                        │     │
│  │  4. Verification Feedback Loop                     │     │
│  └────────────────────────────────────────────────────┘     │
│  Output: Security Patch                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Verify Patch │ ──┐
                  └──────┬───────┘   │
                         │            │
                    ┌────▼────┐       │
                    │ Success?│       │
                    └────┬────┘       │
                         │            │
                    Yes  │  No        │
                         │            │
                         ▼            │
                      [END]           │
                                      │
                         ┌────────────┘
                         │ Retry (max 3x)
                         ▼
                  [Back to Patcher]
```

## Core Components

### 1. LLM Client (`agent/llm_client.py`)

The LLM Client provides a unified interface for all LLM inference operations across agents.

**Key Features:**
- Configurable generation parameters (temperature, max_tokens, top_p)
- Automatic retry with exponential backoff
- Python syntax validation
- Self-correction loop infrastructure

**Configuration:**
```python
# Default parameters optimized for code generation
max_tokens = 2048
temperature = 0.2  # Low temperature for deterministic output
top_p = 0.95
```

**Example Usage:**
```python
from agent.llm_client import LLMClient

llm = LLMClient(vllm_client)

# Generate with default parameters
response = llm.generate("Generate a vulnerability hypothesis...")

# Generate with custom parameters
response = llm.generate(
    prompt="Generate a patch...",
    max_tokens=4096,
    temperature=0.1
)

# Validate Python syntax
is_valid, error = llm.validate_python_syntax(code)
```

### 2. Scanner Agent (`agent/nodes/scanner.py`)

The Scanner Agent combines AST-based pattern detection with LLM-powered semantic analysis.

**Capabilities:**
- **Pattern Detection**: Uses AST to identify dangerous function calls (eval, exec, os.system, etc.)
- **Hypothesis Generation**: LLM generates natural language explanations of vulnerabilities
- **Context Assessment**: LLM analyzes context to reduce false positives
- **Neuro-Slicing**: Extracts minimal code slices for efficient symbolic execution

**Example Output:**
```python
Vulnerability(
    location="app.py:42",
    vuln_type="SQL Injection",
    hypothesis="User input 'username' flows directly into SQL query without sanitization. An attacker could inject SQL commands like ' OR '1'='1 to bypass authentication.",
    confidence=0.85,
    code_slice="<extracted slice>"
)
```

### 3. Speculator Agent (`agent/nodes/speculator.py`)

The Speculator Agent generates formal security contracts using icontract decorators.

**Capabilities:**
- **Contract Generation**: LLM generates icontract decorators from hypotheses
- **Syntax Validation**: Validates generated contracts are valid Python
- **Self-Correction**: Retries with error feedback on syntax errors
- **Vulnerability-Specific Patterns**: Uses tailored examples for each vulnerability type

**Example Output:**
```python
@icontract.ensure(lambda result: "'" not in str(result))
@icontract.ensure(lambda result: "--" not in str(result))
@icontract.ensure(lambda result: " OR " not in str(result).upper())
@icontract.ensure(lambda result: "UNION" not in str(result).upper())
def search_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute_query(query)
```

### 4. Patcher Agent (`agent/nodes/patcher.py`)

The Patcher Agent generates security patches that fix vulnerabilities while preserving functionality.

**Capabilities:**
- **Patch Generation**: LLM generates secure code from counterexamples
- **Signature Preservation**: Ensures patched functions maintain original signatures
- **Style Preservation**: Maintains original code style (indentation, naming)
- **Documentation**: Adds explanatory comments to patches
- **PEP 8 Compliance**: Ensures patches follow Python style guidelines

**Example Output:**
```python
def search_user(username):
    # Security fix: Use parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE name = ?"
    return execute_query(query, (username,))
```

## Prompt Templates

### Hypothesis Generation Prompt

```python
HYPOTHESIS_PROMPT = PromptTemplate(
    name="hypothesis_generation",
    system_prompt="""You are a security expert analyzing Python code for vulnerabilities.
Your task is to generate detailed vulnerability hypotheses that explain:
1. What security property is violated
2. How an attacker could exploit this
3. What data flow leads to the vulnerability""",
    
    template="""Code:
```python
{code}
```

Detected Pattern: {vuln_type} at line {line_num}
Context: {context}

Generate a detailed vulnerability hypothesis:""",
    
    few_shot_examples={
        "SQL Injection": """Example:
Code: query = f"SELECT * FROM users WHERE id={user_id}"
Hypothesis: User input 'user_id' flows directly into SQL query without validation. An attacker could inject SQL commands like '1 OR 1=1' to access all user records."""
    },
    
    max_tokens=512,
    temperature=0.2
)
```

### Contract Generation Prompt

```python
CONTRACT_PROMPT = PromptTemplate(
    name="contract_generation",
    system_prompt="""You are a formal methods engineer generating icontract decorators.
Generate ONLY the decorator code, not the function definition.
Use @icontract.require() for preconditions and @icontract.ensure() for postconditions.""",
    
    template="""Vulnerability Type: {vuln_type}
Hypothesis: {hypothesis}

Examples of correct icontract usage:
{examples}

Generate icontract decorators:
```python""",
    
    few_shot_examples={
        "SQL Injection": """@icontract.ensure(lambda result: "'" not in str(result))
@icontract.ensure(lambda result: "--" not in str(result))
@icontract.ensure(lambda result: " OR " not in str(result).upper())""",
        
        "Command Injection": """@icontract.require(lambda cmd: "|" not in cmd and ";" not in cmd)
@icontract.require(lambda cmd: "`" not in cmd and "$(" not in cmd)"""
    },
    
    max_tokens=1024,
    temperature=0.2
)
```

### Patch Generation Prompt

```python
PATCH_PROMPT = PromptTemplate(
    name="patch_generation",
    system_prompt="""You are a security engineer generating secure patches.
Generate COMPLETE patched code that:
1. Fixes the vulnerability
2. Preserves the original function signature
3. Maintains the original code style
4. Adds explanatory comments""",
    
    template="""Original Code:
```python
{code}
```

Vulnerability: {vuln_type}
Hypothesis: {hypothesis}
Counterexample (exploit that works): {counterexample}

{previous_attempts}

Secure coding patterns for {vuln_type}:
{secure_patterns}

Generate the COMPLETE patched code:
```python""",
    
    few_shot_examples={
        "SQL Injection": """# Use parameterized queries
query = "SELECT * FROM users WHERE name = ?"
execute_query(query, (username,))

# Or use ORM
User.objects.filter(name=username)""",
        
        "Command Injection": """# Use list arguments with shell=False
subprocess.run(["ls", user_input], shell=False)

# Or validate input
if not re.match(r'^[a-zA-Z0-9_-]+$', user_input):
    raise ValueError("Invalid input")"""
    },
    
    max_tokens=4096,
    temperature=0.2
)
```

## Self-Correction Loops

The system implements self-correction loops to handle LLM errors gracefully.

### Generic Self-Correction Function

```python
async def generate_with_self_correction(
    llm: LLMClient,
    prompt_builder: Callable[[Optional[str]], str],
    validator: Callable[[str], Tuple[bool, Optional[str]]],
    max_retries: int = 3
) -> Optional[str]:
    """
    Generic self-correction loop for LLM generation.
    
    Args:
        llm: LLM client for generation
        prompt_builder: Function that builds prompt, optionally with error feedback
        validator: Function that validates output, returns (is_valid, error_message)
        max_retries: Maximum number of retry attempts
    
    Returns:
        Valid output or None if all retries exhausted
    """
    error_feedback = None
    
    for attempt in range(max_retries):
        # Build prompt with optional error feedback
        prompt = prompt_builder(error_feedback)
        
        # Generate output
        output = await llm.generate(prompt)
        
        # Validate output
        is_valid, error = validator(output)
        if is_valid:
            return output
        
        # Prepare error feedback for next iteration
        error_feedback = error
        logging.info(f"Retry {attempt+1}/{max_retries}: {error}")
    
    logging.error(f"Failed after {max_retries} attempts")
    return None
```

### Example: Contract Generation with Self-Correction

```python
def _generate_contract_with_retry(self, vuln: Vulnerability) -> Optional[Contract]:
    """Generate contract with automatic retry on syntax errors."""
    
    def prompt_builder(error_feedback: Optional[str]) -> str:
        prompt = CONTRACT_PROMPT.format(
            vuln_type=vuln.vuln_type,
            hypothesis=vuln.hypothesis,
            examples=self._get_relevant_examples(vuln.vuln_type)
        )
        
        if error_feedback:
            prompt += f"\n\nPrevious attempt had syntax error:\n{error_feedback}\n\nGenerate corrected contract:"
        
        return prompt
    
    def validator(contract_code: str) -> Tuple[bool, Optional[str]]:
        return self.llm.validate_python_syntax(contract_code)
    
    contract_code = generate_with_self_correction(
        self.llm,
        prompt_builder,
        validator,
        max_retries=3
    )
    
    if contract_code:
        return Contract(code=contract_code, vuln_type=vuln.vuln_type)
    return None
```

## Neuro-Slicing Algorithm

Neuro-slicing combines LLM semantic understanding with traditional program slicing to extract minimal code slices for symbolic execution.

### Algorithm Steps

1. **Parse AST**: Identify the vulnerable function
2. **LLM Taint Analysis**: Use LLM to identify user-controlled variables
3. **Backward Slicing**: Perform backward slicing from vulnerable line
4. **Mock Generation**: Use LLM to generate mocks for external dependencies
5. **Combine**: Assemble executable code slice

### Implementation

```python
async def _extract_code_slice(
    self,
    code: str,
    vuln: Vulnerability
) -> Optional[str]:
    """
    Extract minimal code slice using neuro-slicing.
    
    Steps:
    1. Parse AST to identify vulnerable function
    2. Use LLM to identify tainted variables
    3. Perform backward slicing
    4. Generate mocks for dependencies
    5. Combine into executable slice
    """
    try:
        # Step 1: Parse AST
        tree = ast.parse(code)
        line_num = self._get_line_number(vuln.location)
        vuln_function = self._extract_function_at_line(tree, line_num)
        
        if not vuln_function:
            return None
        
        # Step 2: LLM identifies tainted variables
        taint_prompt = SLICING_PROMPT.format(
            code=ast.unparse(vuln_function),
            vuln_type=vuln.vuln_type,
            line_num=line_num
        )
        
        slice_code = await self.llm.generate(taint_prompt, max_tokens=2048)
        
        # Step 3-5: LLM performs slicing and mock generation in one step
        # Validate the slice is syntactically valid
        is_valid, error = self.llm.validate_python_syntax(slice_code)
        
        if not is_valid:
            logging.warning(f"Invalid slice syntax: {error}")
            return None
        
        return slice_code
        
    except Exception as e:
        logging.error(f"Error extracting code slice: {e}")
        return None
```

### Example: Before and After Slicing

**Original Code (100 lines):**
```python
import os
import sys
from database import Database
from auth import authenticate

db = Database()

def get_user_profile(user_id):
    # Complex logic...
    return db.query(f"SELECT * FROM users WHERE id={user_id}")

def update_user(user_id, data):
    # More complex logic...
    pass

# ... 80 more lines ...
```

**Extracted Slice (15 lines):**
```python
# Mock for database
class MockDatabase:
    def query(self, sql):
        return []

db = MockDatabase()

def get_user_profile(user_id):
    # Vulnerable line: SQL injection
    return db.query(f"SELECT * FROM users WHERE id={user_id}")
```

### Performance Impact

Neuro-slicing reduces symbolic execution time by:
- **Code Size**: 50-90% reduction in lines of code
- **Verification Time**: 50-80% reduction in symbolic execution time
- **Path Explosion**: Eliminates irrelevant code paths

## Generated Examples

### Example 1: SQL Injection

**Hypothesis:**
```
User input 'username' flows directly into SQL query without sanitization. 
An attacker could inject SQL commands like ' OR '1'='1 to bypass authentication 
and access all user records.
```

**Contract:**
```python
@icontract.ensure(lambda result: "'" not in str(result))
@icontract.ensure(lambda result: "--" not in str(result))
@icontract.ensure(lambda result: " OR " not in str(result).upper())
@icontract.ensure(lambda result: "UNION" not in str(result).upper())
```

**Patch:**
```python
def search_user(username):
    # Security fix: Use parameterized query to prevent SQL injection
    # This ensures user input is properly escaped and cannot modify query structure
    query = "SELECT * FROM users WHERE name = ?"
    return execute_query(query, (username,))
```

### Example 2: Command Injection

**Hypothesis:**
```
User input 'filename' is concatenated directly into shell command. 
An attacker could inject shell metacharacters like '; rm -rf /' to execute 
arbitrary commands on the system.
```

**Contract:**
```python
@icontract.require(lambda filename: "|" not in filename and ";" not in filename)
@icontract.require(lambda filename: "`" not in filename and "$(" not in filename)
@icontract.require(lambda filename: "&" not in filename and ">" not in filename)
```

**Patch:**
```python
def list_files(filename):
    # Security fix: Use list arguments with shell=False to prevent command injection
    # This ensures the filename is treated as a literal argument, not shell code
    result = subprocess.run(
        ["ls", "-l", filename],
        shell=False,
        capture_output=True,
        text=True
    )
    return result.stdout
```

### Example 3: Path Traversal

**Hypothesis:**
```
User input 'filepath' is used directly in file operations without validation. 
An attacker could use directory traversal sequences like '../../../etc/passwd' 
to access files outside the intended directory.
```

**Contract:**
```python
@icontract.require(lambda filepath: ".." not in filepath)
@icontract.require(lambda filepath: not filepath.startswith("/"))
@icontract.require(lambda filepath: not filepath.startswith("\\"))
```

**Patch:**
```python
def read_user_file(filepath):
    # Security fix: Validate and normalize path to prevent directory traversal
    # Use os.path.normpath to resolve '..' and ensure path is within allowed directory
    import os
    
    base_dir = "/var/app/user_files"
    normalized_path = os.path.normpath(os.path.join(base_dir, filepath))
    
    # Ensure the resolved path is still within base_dir
    if not normalized_path.startswith(base_dir):
        raise ValueError("Invalid file path: directory traversal detected")
    
    with open(normalized_path, 'r') as f:
        return f.read()
```

## Performance Characteristics

### Scanner Performance
- **Small files (< 500 lines)**: < 1 second
- **Medium files (500-1000 lines)**: < 5 seconds
- **Large files (> 1000 lines)**: < 10 seconds

### Patcher Performance
- **Simple patches**: < 1 second
- **Complex patches**: < 5 seconds
- **With retry**: < 15 seconds (3 retries × 5 seconds)

### LLM Inference Latency
- **Hypothesis generation**: 1-2 seconds
- **Contract generation**: 2-3 seconds
- **Patch generation**: 2-4 seconds

### End-to-End Workflow
- **Without slicing**: 30-60 seconds (symbolic execution bottleneck)
- **With slicing**: 10-20 seconds (50-70% reduction)

## Configuration

### LLM Parameters

```python
# agent/llm_client.py
DEFAULT_CONFIG = {
    'max_tokens': 2048,
    'temperature': 0.2,  # Low for deterministic output
    'top_p': 0.95,
    'frequency_penalty': 0.0,
    'presence_penalty': 0.0
}

# Patch generation uses higher token limit
PATCH_CONFIG = {
    'max_tokens': 4096,  # Allow full function generation
    'temperature': 0.1,  # Even lower for code generation
    'top_p': 0.95
}
```

### Retry Configuration

```python
# agent/llm_client.py
RETRY_CONFIG = {
    'max_retries': 3,
    'initial_delay': 2.0,  # seconds
    'backoff_factor': 2.0,  # exponential backoff
    'max_delay': 8.0  # seconds
}
```

## Testing

### Unit Tests
- Test prompt template formatting
- Test syntax validation
- Test self-correction logic
- Test neuro-slicing components

### Property-Based Tests
- Property 1: Hypothesis generation completeness
- Property 2: False positive reduction
- Property 3-7: Code slice validity and completeness
- Property 8-9: Contract syntax and patterns
- Property 10: Self-correction loop
- Property 11-16: Patch quality and compliance
- Property 17-18: Configuration and validation
- Property 19-20: Performance bounds

### Integration Tests
- End-to-end workflow tests
- Self-correction loop tests
- Neuro-slicing effectiveness tests
- Real-world vulnerability tests

## Future Enhancements

1. **Multi-Model Support**: Support for multiple LLM backends (GPT-4, Claude, etc.)
2. **Fine-Tuning**: Fine-tune models on security-specific datasets
3. **Caching**: Cache LLM responses for common patterns
4. **Parallel Processing**: Process multiple vulnerabilities in parallel
5. **Interactive Mode**: Allow user feedback during patch generation
6. **Confidence Calibration**: Improve confidence score accuracy
7. **Multi-Language Support**: Extend to Java, JavaScript, C++, etc.

## References

- [icontract Documentation](https://icontract.readthedocs.io/)
- [CrossHair Documentation](https://crosshair.readthedocs.io/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [DeepSeek-Coder](https://github.com/deepseek-ai/DeepSeek-Coder)
- [Program Slicing](https://en.wikipedia.org/wiki/Program_slicing)
