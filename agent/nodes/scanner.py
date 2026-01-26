"""
SecureCodeAI - Scanner Agent
Identifies potential vulnerability hotspots using AST analysis and LLM-powered reasoning.
"""

import ast
import re
import logging
from typing import List, Dict, Optional, Tuple
import time

from ..state import AgentState, Vulnerability
from ..llm_client import LLMClient
from ..prompts import HYPOTHESIS_PROMPT, SLICING_PROMPT


logger = logging.getLogger(__name__)


class ScannerAgent:
    """
    Scanner Agent: Identifies vulnerability hotspots in code.
    
    Uses:
    1. AST parsing (Python's ast module)
    2. Pattern matching for dangerous functions
    3. LLM-powered hypothesis generation (NEW)
    4. Contextual false positive reduction (NEW)
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize Scanner Agent.
        
        Args:
            llm_client: LLM client for hypothesis generation (optional)
        """
        self.llm_client = llm_client
        self.dangerous_patterns = {
            "SQL Injection": [
                r"execute\s*\(\s*f['\"].*?\{.*?\}",  # f-string in execute()
                r"execute\s*\(\s*['\"].*?\%",  # % formatting in execute()
                r"execute\s*\(\s*.*?\+",  # String concatenation in execute()
                r"f['\"].*?SELECT.*?FROM.*?\{.*?\}",  # Generic SQL f-string
            ],
            "Command Injection": [
                r"subprocess\.run\s*\(.*?shell\s*=\s*True",
                r"os\.system\s*\(",
                r"subprocess\.call\s*\(.*?shell\s*=\s*True",
            ],
            "Path Traversal": [
                r"open\s*\(.*?\+",  # String concatenation with open()
                r"open\s*\(\s*f['\"].*?\{",  # f-string with open()
            ],
            "Code Injection": [
                r"\beval\s*\(",
                r"\bexec\s*\(",
            ]
        }
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute Scanner Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with detected vulnerabilities
        """
        start_time = time.time()
        state["logs"].append("Scanner Agent: Starting scan...")
        
        # Initialize timing metrics (Requirement 10.4)
        ast_analysis_time = 0.0
        hypothesis_generation_time = 0.0
        slicing_time = 0.0
        
        code = state.get("code", "")
        vulnerabilities = []
        
        try:
            # Pattern-based scanning with timing
            ast_start = time.time()
            
            for vuln_type, patterns in self.dangerous_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, code, re.MULTILINE)
                    for match in matches:
                        # Find line number
                        line_num = code[:match.start()].count('\n') + 1
                        
                        vulnerabilities.append(Vulnerability(
                            location=f"{state.get('file_path', 'unknown')}:{line_num}",
                            vuln_type=vuln_type,
                            severity="HIGH",
                            description=f"Detected dangerous pattern: {pattern}",
                            confidence=0.7
                        ))
            
            # AST-based scanning (more precise)
            try:
                tree = ast.parse(code)
                ast_vulns = self._scan_ast(tree, state.get("file_path", "unknown"))
                vulnerabilities.extend(ast_vulns)
            except SyntaxError as e:
                state["errors"].append(f"Scanner Agent: AST parse error - {str(e)}")
            
            ast_analysis_time = time.time() - ast_start
        
        except Exception as e:
            state["errors"].append(f"Scanner Agent: Error - {str(e)}")
        
        # Deduplicate vulnerabilities by location
        unique_vulns = []
        seen_locations = set()
        for vuln in vulnerabilities:
            if vuln.location not in seen_locations:
                unique_vulns.append(vuln)
                seen_locations.add(vuln.location)
        
        # LLM-powered enhancements (Requirements 1.1, 1.2, 1.3)
        if self.llm_client:
            hypothesis_start = time.time()
            state["logs"].append("Scanner Agent: Generating LLM-powered hypotheses...")
            for vuln in unique_vulns:
                try:
                    # Generate hypothesis for each vulnerability
                    hypothesis = self._generate_hypothesis(vuln, code)
                    vuln.hypothesis = hypothesis
                    
                    # Assess context to reduce false positives
                    adjusted_confidence = self._assess_context(vuln, code)
                    vuln.confidence = adjusted_confidence
                    
                    # Validate hypothesis (Requirement 5.4, 5.5)
                    is_valid, error = self.validate_hypothesis(vuln)
                    if not is_valid:
                        logger.warning(f"Invalid hypothesis for {vuln.location}: {error}")
                        state["errors"].append(f"Scanner Agent: Invalid hypothesis - {error}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate hypothesis for {vuln.location}: {e}")
                    vuln.hypothesis = f"Pattern-based detection: {vuln.description}"
            
            hypothesis_generation_time = time.time() - hypothesis_start
            
            # Extract code slice for the first vulnerability (Requirements 4.1, 4.2, 4.3, 4.4)
            if unique_vulns:
                slicing_start = time.time()
                state["logs"].append("Scanner Agent: Extracting code slice for symbolic execution...")
                try:
                    code_slice = self._extract_code_slice(code, unique_vulns[0])
                    if code_slice:
                        # Validate code slice (Requirement 5.4, 5.5)
                        is_valid, error = self.validate_code_slice(code_slice)
                        if is_valid:
                            state["code_slice"] = code_slice
                            state["logs"].append("Scanner Agent: Code slice extracted successfully")
                        else:
                            logger.error(f"Invalid code slice: {error}")
                            state["errors"].append(f"Scanner Agent: Invalid code slice - {error}")
                    else:
                        state["logs"].append("Scanner Agent: Failed to extract code slice")
                except Exception as e:
                    logger.error(f"Code slice extraction error: {e}")
                    state["errors"].append(f"Scanner Agent: Slice extraction failed - {str(e)}")
                
                slicing_time = time.time() - slicing_start
        
        state["vulnerabilities"] = unique_vulns
        state["logs"].append(f"Scanner Agent: Found {len(unique_vulns)} potential vulnerabilities")
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        # Log detailed timing metrics (Requirement 10.4)
        logger.info(f"Scanner timing - AST: {ast_analysis_time:.2f}s, "
                   f"Hypothesis: {hypothesis_generation_time:.2f}s, "
                   f"Slicing: {slicing_time:.2f}s, "
                   f"Total: {execution_time:.2f}s")
        
        # Performance assertion for files under 1000 lines (Requirement 10.4)
        line_count = len(code.split('\n'))
        if line_count < 1000 and execution_time > 10.0:
            logger.warning(f"Scanner performance degraded: {execution_time:.2f}s for {line_count} lines "
                          f"(expected < 10s)")
            state["logs"].append(f"Scanner Agent: Performance warning - {execution_time:.2f}s for {line_count} lines")
        
        return state
    
    def _generate_hypothesis(self, vuln: Vulnerability, code: str) -> str:
        """
        Generate LLM-powered vulnerability hypothesis.
        
        Args:
            vuln: Detected vulnerability
            code: Full source code
            
        Returns:
            Natural language hypothesis explaining the vulnerability
            
        Validates: Requirements 1.1, 1.3
        """
        if not self.llm_client:
            return vuln.description
        
        try:
            # Extract function containing the vulnerability
            function_name, function_code = self._extract_function_at_line(
                code, 
                self._get_line_number(vuln.location)
            )
            
            # Build prompt for hypothesis generation
            prompt = HYPOTHESIS_PROMPT.format(
                code=function_code or code[:500],  # Limit context if function not found
                vuln_type=vuln.vuln_type,
                line_num=self._get_line_number(vuln.location),
                function_name=function_name or "unknown"
            )
            
            # Generate hypothesis using LLM
            params = HYPOTHESIS_PROMPT.get_generation_params()
            hypothesis = self.llm_client.generate(
                prompt,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"]
            )
            
            return hypothesis.strip()
            
        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            return vuln.description
    
    def _assess_context(self, vuln: Vulnerability, code: str) -> float:
        """
        Assess vulnerability context to reduce false positives.
        
        Uses LLM to analyze if dangerous function usage is actually vulnerable
        based on context (e.g., eval() with hardcoded string is safe).
        
        Args:
            vuln: Detected vulnerability
            code: Full source code
            
        Returns:
            Adjusted confidence score (0.0-1.0)
            
        Validates: Requirement 1.2
        """
        if not self.llm_client:
            return vuln.confidence
        
        try:
            # Extract context around vulnerability
            line_num = self._get_line_number(vuln.location)
            context = self._extract_context(code, line_num, context_lines=5)
            
            # Build assessment prompt
            assessment_prompt = f"""Analyze if this is a true vulnerability or false positive.

Code Context:
```python
{context}
```

Vulnerability: {vuln.vuln_type} at line {line_num}

Is this exploitable by an attacker? Consider:
1. Is user input involved?
2. Are there any sanitization/validation checks?
3. Is the dangerous function used with hardcoded/safe values?

Answer with ONLY: "TRUE_POSITIVE" or "FALSE_POSITIVE" followed by confidence (0.0-1.0)
Format: VERDICT: confidence
Example: TRUE_POSITIVE: 0.9
"""
            
            # Get LLM assessment
            response = self.llm_client.generate(assessment_prompt, max_tokens=50, temperature=0.1)
            
            # Parse response
            if "FALSE_POSITIVE" in response.upper():
                # Reduce confidence for likely false positives
                return min(vuln.confidence * 0.5, 0.4)
            elif "TRUE_POSITIVE" in response.upper():
                # Extract confidence if provided
                try:
                    confidence_match = re.search(r'(\d+\.?\d*)', response)
                    if confidence_match:
                        llm_confidence = float(confidence_match.group(1))
                        # Blend LLM confidence with pattern confidence
                        return (vuln.confidence + llm_confidence) / 2
                except:
                    pass
            
            # Default: keep original confidence
            return vuln.confidence
            
        except Exception as e:
            logger.warning(f"Context assessment failed: {e}")
            return vuln.confidence
    
    def _extract_function_at_line(self, code: str, line_num: int) -> tuple[str, str]:
        """
        Extract function containing the specified line.
        
        Args:
            code: Full source code
            line_num: Line number to find
            
        Returns:
            Tuple of (function_name, function_code)
        """
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if line_num is within this function
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        if node.lineno <= line_num <= node.end_lineno:
                            # Extract function code
                            lines = code.split('\n')
                            func_lines = lines[node.lineno-1:node.end_lineno]
                            return node.name, '\n'.join(func_lines)
            
            return "unknown", ""
            
        except Exception as e:
            logger.debug(f"Function extraction failed: {e}")
            return "unknown", ""
    
    def _extract_context(self, code: str, line_num: int, context_lines: int = 5) -> str:
        """
        Extract code context around a line.
        
        Args:
            code: Full source code
            line_num: Target line number
            context_lines: Number of lines before/after to include
            
        Returns:
            Code context as string
        """
        lines = code.split('\n')
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        
        context_with_numbers = []
        for i in range(start, end):
            marker = ">>>" if i == line_num - 1 else "   "
            context_with_numbers.append(f"{marker} {i+1:4d} | {lines[i]}")
        
        return '\n'.join(context_with_numbers)
    
    def _get_line_number(self, location: str) -> int:
        """Extract line number from location string (file:line format)."""
        try:
            return int(location.split(':')[-1])
        except:
            return 1
    
    def _scan_ast(self, tree: ast.AST, file_path: str) -> List[Vulnerability]:
        """Scan AST for vulnerable patterns with basic data flow analysis."""
        vulnerabilities = []
        
        for node in ast.walk(tree):
            # Track variables that hold potentially dangerous strings within function scopes
            if isinstance(node, ast.FunctionDef):
                tainted_vars = set()
                
                for child in ast.walk(node):
                    # Track assignments of f-strings or string concatenation
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                # Check value being assigned
                                if isinstance(child.value, ast.JoinedStr):  # f-string
                                    tainted_vars.add(target.id)
                                elif isinstance(child.value, ast.BinOp) and isinstance(child.value.op, ast.Add):  # Concatenation
                                    tainted_vars.add(target.id)
                    
                    # Check for dangerous function calls
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            func_name = child.func.id
                            
                            # eval/exec detection
                            if func_name in ['eval', 'exec']:
                                vulnerabilities.append(Vulnerability(
                                    location=f"{file_path}:{child.lineno}",
                                    vuln_type="Code Injection",
                                    severity="CRITICAL",
                                    description=f"Use of dangerous function: {func_name}()",
                                    confidence=0.9
                                ))
                        
                        # Check for subprocess/os.system with shell=True
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr in ['system', 'popen']:
                                vulnerabilities.append(Vulnerability(
                                    location=f"{file_path}:{child.lineno}",
                                    vuln_type="Command Injection",
                                    severity="HIGH",
                                    description=f"Dangerous system call: {child.func.attr}",
                                    confidence=0.85
                                ))
                        
                        # Check for SQL usage
                        if isinstance(child.func, ast.Attribute) and child.func.attr == 'execute':
                            if child.args:
                                arg = child.args[0]
                                
                                # Direct usage: execute(f"...") or execute("..." + ...)
                                if isinstance(arg, ast.JoinedStr):
                                    vulnerabilities.append(Vulnerability(
                                        location=f"{file_path}:{child.lineno}",
                                        vuln_type="SQL Injection",
                                        severity="HIGH",
                                        description="SQL query uses f-string formatting",
                                        confidence=0.9
                                    ))
                                elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                                    vulnerabilities.append(Vulnerability(
                                        location=f"{file_path}:{child.lineno}",
                                        vuln_type="SQL Injection",
                                        severity="HIGH",
                                        description="SQL query uses string concatenation",
                                        confidence=0.85
                                    ))
                                
                                # Indirect usage: execute(query) where query is tainted
                                elif isinstance(arg, ast.Name) and arg.id in tainted_vars:
                                    vulnerabilities.append(Vulnerability(
                                        location=f"{file_path}:{child.lineno}",
                                        vuln_type="SQL Injection",
                                        severity="HIGH",
                                        description=f"SQL query variable '{arg.id}' constructed via string formatting",
                                        confidence=0.85
                                    ))
        
        return vulnerabilities
    
    def _extract_code_slice(self, code: str, vuln: Vulnerability) -> Optional[str]:
        """
        Extract minimal code slice using LLM-guided neuro-slicing.
        
        This implements the neuro-slicing algorithm:
        1. Parse AST to identify vulnerable function
        2. Use LLM to identify tainted variables (user inputs)
        3. Perform backward slicing from vulnerable line
        4. Use LLM to generate mocks for external dependencies
        5. Combine into executable slice
        
        Uses self-correction loop for robust slice generation.
        
        Args:
            code: Full source code
            vuln: Detected vulnerability
            
        Returns:
            Executable code slice or None if extraction fails
            
        Validates: Requirements 4.1, 4.2, 4.3, 4.4, 7.1, 7.2, 7.3
        """
        if not self.llm_client:
            logger.warning("Cannot extract code slice without LLM client")
            return None
        
        try:
            # Step 1: Parse AST to identify vulnerable function
            line_num = self._get_line_number(vuln.location)
            func_name, func_code = self._extract_function_at_line(code, line_num)
            
            # Step 2-5: Use LLM to generate complete slice with mocks
            # Build context for better slicing (use full code if function not found)
            if func_code:
                context = self._build_context(code, line_num)
            else:
                # Fallback: use full code if we can't extract function
                logger.debug(f"Using full code as context for line {line_num}")
                context = code
            
            # Use self-correction loop for robust slice generation (Requirements 7.1, 7.2, 7.3)
            def prompt_builder(error_feedback: Optional[str]) -> str:
                prompt = SLICING_PROMPT.format(
                    code=context,
                    vuln_type=vuln.vuln_type,
                    line_num=line_num,
                    hypothesis=vuln.hypothesis or vuln.description
                )
                
                if error_feedback:
                    prompt += f"\n\nPrevious attempt had syntax error:\n{error_feedback}\n\nGenerate corrected slice:\n```python"
                
                return prompt
            
            def validator(output: str) -> tuple:
                # Clean and validate slice
                cleaned = self._clean_code_response(output)
                is_valid, error = self.llm_client.validate_python_syntax(cleaned)
                return (is_valid, error)
            
            # Generate slice with self-correction
            params = SLICING_PROMPT.get_generation_params()
            slice_code = self.llm_client.generate_with_self_correction(
                prompt_builder,
                validator,
                max_retries=3,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"]
            )
            
            if slice_code:
                # Clean the final output
                slice_code = self._clean_code_response(slice_code)
                logger.info(f"Successfully extracted code slice for {vuln.location}")
                return slice_code
            else:
                logger.error(f"Failed to extract valid code slice after retries")
                return None
            
        except Exception as e:
            logger.error(f"Code slice extraction failed: {e}")
            return None
    
    def _build_context(self, code: str, line_num: int) -> str:
        """
        Build enriched context for LLM slicing.
        
        Extracts:
        - Imports
        - Type hints
        - Function signatures
        - Docstrings
        - Security-relevant comments
        
        Handles context window limits (128k tokens) by prioritizing relevant sections.
        
        Args:
            code: Full source code
            line_num: Line number of vulnerability
            
        Returns:
            Enriched context string
            
        Validates: Requirements 6.1, 6.2, 6.4, 6.5
        """
        try:
            tree = ast.parse(code)
            context_parts = []
            
            # Extract imports (always include)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))
            
            if imports:
                context_parts.append("# Imports\n" + "\n".join(imports))
            
            # Find the vulnerable function and related functions
            vulnerable_func = None
            related_funcs = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if this is the vulnerable function
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        if node.lineno <= line_num <= node.end_lineno:
                            vulnerable_func = node
                        else:
                            # Include other functions that might be called
                            related_funcs.append(node)
            
            # Add vulnerable function with full details
            if vulnerable_func:
                func_parts = []
                
                # Add docstring if present
                docstring = ast.get_docstring(vulnerable_func)
                if docstring:
                    func_parts.append(f'"""{docstring}"""')
                
                # Add function signature with type hints
                func_code = ast.unparse(vulnerable_func)
                func_parts.append(func_code)
                
                context_parts.append("\n# Vulnerable Function\n" + "\n".join(func_parts))
            
            # Add signatures of related functions (not full implementations to save tokens)
            if related_funcs:
                signatures = []
                for func in related_funcs[:5]:  # Limit to 5 most relevant
                    # Extract just the signature
                    sig_parts = [f"def {func.name}("]
                    
                    # Add parameters
                    args = []
                    if func.args.args:
                        for arg in func.args.args:
                            arg_str = arg.arg
                            if arg.annotation:
                                arg_str += f": {ast.unparse(arg.annotation)}"
                            args.append(arg_str)
                    sig_parts.append(", ".join(args))
                    sig_parts.append(")")
                    
                    # Add return type if present
                    if func.returns:
                        sig_parts.append(f" -> {ast.unparse(func.returns)}")
                    
                    sig_parts.append(": ...")
                    
                    signatures.append("".join(sig_parts))
                
                if signatures:
                    context_parts.append("\n# Related Function Signatures\n" + "\n".join(signatures))
            
            # Combine all parts
            full_context = "\n\n".join(context_parts)
            
            # Check token limit (rough estimate: 1 token ≈ 4 characters)
            # Limit to ~8k tokens (32k characters) to leave room for prompt
            max_chars = 32000
            if len(full_context) > max_chars:
                # Prioritize: imports + vulnerable function
                priority_parts = []
                if imports:
                    priority_parts.append("# Imports\n" + "\n".join(imports))
                if vulnerable_func:
                    priority_parts.append("\n# Vulnerable Function\n" + ast.unparse(vulnerable_func))
                
                full_context = "\n\n".join(priority_parts)
            
            return full_context
            
        except Exception as e:
            logger.warning(f"Context building failed: {e}, using raw code")
            # Fallback: return function containing the vulnerability
            func_name, func_code = self._extract_function_at_line(code, line_num)
            return func_code or code[:10000]  # Limit to 10k chars
    
    def _clean_code_response(self, response: str) -> str:
        """
        Clean LLM response to extract pure Python code.
        
        Removes markdown code blocks, explanations, etc.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned Python code
        """
        # Remove markdown code blocks
        if "```python" in response:
            # Extract code between ```python and ```
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            if end != -1:
                response = response[start:end]
        elif "```" in response:
            # Generic code block
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end]
        
        # Strip whitespace
        response = response.strip()
        
        return response
    
    def validate_hypothesis(self, vuln: Vulnerability) -> Tuple[bool, Optional[str]]:
        """
        Validate that a vulnerability hypothesis contains required fields.
        
        Checks:
        - location is non-empty
        - vuln_type is non-empty
        - confidence is between 0.0 and 1.0
        - hypothesis is non-empty (if LLM was used)
        
        Args:
            vuln: Vulnerability object to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Validates: Requirements 5.4, 5.5
        """
        errors = []
        
        # Check required fields
        if not vuln.location:
            errors.append("location is empty")
        
        if not vuln.vuln_type:
            errors.append("vuln_type is empty")
        
        # Check confidence range
        if not (0.0 <= vuln.confidence <= 1.0):
            errors.append(f"confidence {vuln.confidence} not in range [0.0, 1.0]")
        
        # Check hypothesis if LLM was used
        if self.llm_client and not vuln.hypothesis:
            errors.append("hypothesis is empty (LLM client available)")
        
        if errors:
            return (False, "; ".join(errors))
        
        return (True, None)
    
    def validate_code_slice(self, code_slice: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a code slice is valid Python.
        
        Args:
            code_slice: Code slice to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Validates: Requirements 5.4, 5.5
        """
        if not code_slice:
            return (False, "code slice is empty")
        
        # Validate Python syntax
        if self.llm_client:
            return self.llm_client.validate_python_syntax(code_slice)
        else:
            # Fallback validation without LLM client
            try:
                ast.parse(code_slice)
                return (True, None)
            except SyntaxError as e:
                return (False, f"Syntax error: {e.msg}")
            except Exception as e:
                return (False, f"Parse error: {str(e)}")
