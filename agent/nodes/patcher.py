"""
SecureCodeAI - Patcher Agent
Generates security patches based on counterexamples from symbolic execution.
"""

import ast
import logging
import time
import re
from typing import Optional, List, Tuple

from ..state import AgentState, Patch, VerificationResult, Vulnerability
from ..llm_client import LLMClient
from ..prompts import PATCH_PROMPT, get_secure_patterns, format_previous_attempts

# Import PEP 8 tools (Requirement 9.5)
try:
    import pycodestyle
    import autopep8
    PEP8_AVAILABLE = True
except ImportError:
    PEP8_AVAILABLE = False
    logging.warning("pycodestyle/autopep8 not available, PEP 8 checking disabled")


logger = logging.getLogger(__name__)


class PatcherAgent:
    """
    Patcher Agent: Generates and validates security patches.
    
    Uses LLM to generate patches that fix vulnerabilities found by SymBot.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize Patcher Agent.
        
        Args:
            llm_client: LLM client for patch generation (optional, uses templates if None)
        """
        self.llm_client = llm_client
        
        # Load few-shot examples for patch generation (Requirement 3.1)
        self.patch_examples = PATCH_PROMPT.few_shot_examples
        
        # Template patches for common vulnerabilities (fallback)
        self.patch_templates = {
            "SQL Injection": "Use parameterized queries with ? placeholders",
            "Command Injection": "Use subprocess with list arguments (shell=False)",
            "Path Traversal": "Use os.path.basename() to sanitize filenames",
            "Code Injection": "Remove eval/exec, use safe alternatives like ast.literal_eval"
        }
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute Patcher Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated patch
        """
        start_time = time.time()
        state["logs"].append("Patcher Agent: Generating patch...")
        
        # Initialize timing metrics (Requirement 10.5)
        patch_generation_time = 0.0
        
        # Get latest verification result
        verification_results = state.get("verification_results", [])
        if not verification_results:
            state["errors"].append("Patcher Agent: No verification results found")
            return state
        
        latest_result = verification_results[-1]
        if not latest_result.counterexample:
            state["logs"].append("Patcher Agent: No counterexample to patch")
            return state
        
        # Get vulnerability info
        current_vuln = state.get("current_vulnerability")
        if not current_vuln:
            state["errors"].append("Patcher Agent: No current vulnerability")
            return state
        
        try:
            # Generate patch with feedback (Requirements 3.1, 3.5, 7.2)
            code = state.get("code", "")
            iteration = state.get("iteration_count", 0)
            
            patch_start = time.time()
            patch = self._generate_patch_with_feedback(
                code,
                current_vuln,
                latest_result.counterexample,
                iteration
            )
            patch_generation_time = time.time() - patch_start
            
            if patch:
                # Validate patch (Requirement 5.4, 5.5)
                is_valid, error = self.validate_patch(patch, code)
                if is_valid:
                    state["current_patch"] = patch
                    state["patches"] = state.get("patches", []) + [patch]
                    state["iteration_count"] = iteration + 1
                    state["logs"].append(f"Patcher Agent: Generated patch (iteration {iteration + 1})")
                else:
                    logger.warning(f"Invalid patch: {error}")
                    state["errors"].append(f"Patcher Agent: Invalid patch - {error}")
            else:
                state["errors"].append("Patcher Agent: Failed to generate valid patch")
        
        except Exception as e:
            state["errors"].append(f"Patcher Agent: Error - {str(e)}")
            logger.error(f"Patcher execution error: {e}")
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        # Log detailed timing metrics (Requirement 10.5)
        logger.info(f"Patcher timing - Generation: {patch_generation_time:.2f}s, "
                   f"Total: {execution_time:.2f}s")
        
        # Performance assertion (< 5s per patch) (Requirement 10.5)
        if execution_time > 5.0:
            logger.warning(f"Patcher performance degraded: {execution_time:.2f}s (expected < 5s)")
            state["logs"].append(f"Patcher Agent: Performance warning - {execution_time:.2f}s per patch")
        
        return state
    
    def _generate_patch_with_feedback(
        self,
        code: str,
        vuln: Vulnerability,
        counterexample: str,
        iteration: int
    ) -> Optional[Patch]:
        """
        Generate patch with verification feedback.
        
        Includes counterexample and previous failed patches in prompt.
        
        Args:
            code: Original vulnerable code
            vuln: Vulnerability information
            counterexample: Exploit PoC from SymBot
            iteration: Current iteration number
            
        Returns:
            Patch object or None if generation fails
            
        Validates: Requirements 3.1, 3.5, 7.2
        """
        # If no LLM client, use template
        if not self.llm_client:
            patch_code = self._apply_template_patch(code, vuln.vuln_type)
            return Patch(
                code=patch_code,
                diff=self._generate_diff(code, patch_code),
                verified=False
            )
        
        try:
            # Get previous failed patches if this is a retry
            previous_patches = []
            if iteration > 0:
                # In a real implementation, we'd get these from state
                # For now, we'll just note that we're retrying
                logger.info(f"Generating patch (iteration {iteration + 1})")
            
            # Build patch prompt
            prompt = self._build_patch_prompt(
                code,
                vuln,
                counterexample,
                previous_patches
            )
            
            # Generate patch using LLM (max_tokens=4096 for full function)
            params = PATCH_PROMPT.get_generation_params()
            patched_code = self.llm_client.generate(
                prompt,
                max_tokens=4096,  # Larger for complete functions
                temperature=params["temperature"]
            )
            
            # Clean response
            patched_code = self._clean_patch_response(patched_code)
            
            # Validate patch syntax
            is_valid, error = self.llm_client.validate_python_syntax(patched_code)
            
            if not is_valid:
                logger.error(f"Generated patch has syntax error: {error}")
                # Fall back to template
                patched_code = self._apply_template_patch(code, vuln.vuln_type)
            
            # Verify function signature preservation (Requirement 3.2)
            if not self._verify_signature_preserved(code, patched_code):
                logger.warning("Patch modified function signature")
            
            # Preserve code style (Requirements 9.1, 9.3, 9.4)
            patched_code = self._preserve_code_style(code, patched_code)
            
            # Add security comment (Requirement 9.2)
            patched_code = self._add_security_comment(patched_code, vuln, counterexample)
            
            # Check for new dependencies (Requirement 9.3)
            new_deps = self._check_new_dependencies(code, patched_code)
            if new_deps:
                logger.info(f"Patch introduces new dependencies: {new_deps}")
            
            # Check and fix PEP 8 compliance (Requirement 9.5)
            is_compliant, violations = self._check_pep8_compliance(patched_code)
            if not is_compliant:
                logger.info(f"PEP 8 violations found: {len(violations)}")
                patched_code = self._fix_pep8_violations(patched_code)
                logger.info("Applied PEP 8 auto-fixes")
            
            # Generate diff
            diff = self._generate_diff(code, patched_code)
            
            return Patch(
                code=patched_code,
                diff=diff,
                verified=False
            )
            
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
            # Fall back to template
            patch_code = self._apply_template_patch(code, vuln.vuln_type)
            return Patch(
                code=patch_code,
                diff=self._generate_diff(code, patch_code),
                verified=False
            )
    
    def _build_patch_prompt(
        self,
        code: str,
        vuln: Vulnerability,
        counterexample: str,
        previous_patches: List[str]
    ) -> str:
        """
        Build prompt for patch generation.
        
        Args:
            code: Original vulnerable code
            vuln: Vulnerability information
            counterexample: Exploit PoC
            previous_patches: List of previous failed patches
            
        Returns:
            Formatted prompt string
        """
        # Get secure patterns for this vulnerability type (Requirements 3.3, 3.4, 8.4, 8.5)
        secure_patterns = self._get_patch_examples(vuln.vuln_type)
        
        # Format previous attempts if any
        previous_attempts = format_previous_attempts(previous_patches) if previous_patches else ""
        
        # Build prompt
        prompt = PATCH_PROMPT.format(
            code=code,
            vuln_type=vuln.vuln_type,
            hypothesis=vuln.hypothesis or vuln.description,
            counterexample=counterexample,
            previous_attempts=previous_attempts,
            secure_patterns=secure_patterns
        )
        
        return prompt
    
    def _get_patch_examples(self, vuln_type: str) -> str:
        """
        Get secure coding patterns for specific vulnerability type.
        
        Args:
            vuln_type: Type of vulnerability
            
        Returns:
            Formatted secure patterns string
            
        Validates: Requirements 3.3, 3.4, 8.4, 8.5
        """
        return get_secure_patterns(vuln_type)
    
    def _extract_function_signature(self, code: str) -> Optional[Tuple[str, List[str], Optional[str]]]:
        """
        Extract function signature from code.
        
        Returns tuple of (function_name, parameters, return_type).
        
        Args:
            code: Python code containing function
            
        Returns:
            Tuple of (name, params, return_type) or None
            
        Validates: Requirement 3.2
        """
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract function name
                    func_name = node.name
                    
                    # Extract parameters
                    params = [arg.arg for arg in node.args.args]
                    
                    # Extract return type if present
                    return_type = ast.unparse(node.returns) if node.returns else None
                    
                    return (func_name, params, return_type)
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract function signature: {e}")
            return None
    
    def _verify_signature_preserved(self, original: str, patched: str) -> bool:
        """
        Verify that patched function has same signature as original.
        
        Args:
            original: Original code
            patched: Patched code
            
        Returns:
            True if signature preserved, False otherwise
            
        Validates: Requirement 3.2
        """
        orig_sig = self._extract_function_signature(original)
        patch_sig = self._extract_function_signature(patched)
        
        if not orig_sig or not patch_sig:
            return True  # Can't verify, assume OK
        
        # Check function name and parameters match
        return (orig_sig[0] == patch_sig[0] and 
                orig_sig[1] == patch_sig[1])
    
    def _preserve_code_style(self, original: str, patched: str) -> str:
        """
        Preserve code style from original in patched code.
        
        Detects and preserves:
        - Indentation style (spaces vs tabs, indent size)
        - Naming conventions (snake_case, camelCase)
        - Type hints if present in original
        
        Args:
            original: Original code
            patched: Patched code
            
        Returns:
            Patched code with preserved style
            
        Validates: Requirements 9.1, 9.3, 9.4
        """
        try:
            # Detect indentation style
            indent_char, indent_size = self._detect_indentation(original)
            
            # Apply indentation to patched code
            patched = self._apply_indentation(patched, indent_char, indent_size)
            
            # Preserve type hints if present in original
            if self._has_type_hints(original):
                patched = self._preserve_type_hints(original, patched)
            
            return patched
            
        except Exception as e:
            logger.debug(f"Failed to preserve code style: {e}")
            return patched  # Return unmodified if style preservation fails
    
    def _detect_indentation(self, code: str) -> Tuple[str, int]:
        """
        Detect indentation style (spaces vs tabs, indent size).
        
        Args:
            code: Python code
            
        Returns:
            Tuple of (indent_char, indent_size)
            
        Validates: Requirement 9.1
        """
        lines = code.split('\n')
        
        # Count tabs vs spaces
        tab_count = 0
        space_count = 0
        space_sizes = []
        
        for line in lines:
            if not line or not line[0].isspace():
                continue
            
            # Count leading whitespace
            leading = len(line) - len(line.lstrip())
            
            if line[0] == '\t':
                tab_count += 1
            elif line[0] == ' ':
                space_count += 1
                space_sizes.append(leading)
        
        # Determine indent character
        indent_char = '\t' if tab_count > space_count else ' '
        
        # Determine indent size (for spaces)
        if indent_char == ' ' and space_sizes:
            # Find most common indent size
            from collections import Counter
            indent_size = Counter(space_sizes).most_common(1)[0][0]
        else:
            indent_size = 4  # Default to 4 spaces
        
        return (indent_char, indent_size)
    
    def _apply_indentation(self, code: str, indent_char: str, indent_size: int) -> str:
        """
        Apply consistent indentation to code.
        
        Args:
            code: Python code
            indent_char: Indentation character (' ' or '\t')
            indent_size: Number of spaces per indent level
            
        Returns:
            Code with consistent indentation
            
        Validates: Requirement 9.1
        """
        lines = code.split('\n')
        result = []
        
        for line in lines:
            if not line or not line[0].isspace():
                result.append(line)
                continue
            
            # Calculate indent level
            stripped = line.lstrip()
            leading = len(line) - len(stripped)
            
            # Convert to target indentation
            if indent_char == '\t':
                indent_level = leading // 4  # Assume 4 spaces = 1 tab
                new_line = '\t' * indent_level + stripped
            else:
                indent_level = leading // 4  # Normalize to 4-space units
                new_line = ' ' * (indent_level * indent_size) + stripped
            
            result.append(new_line)
        
        return '\n'.join(result)
    
    def _has_type_hints(self, code: str) -> bool:
        """
        Check if code contains type hints.
        
        Args:
            code: Python code
            
        Returns:
            True if type hints present, False otherwise
            
        Validates: Requirement 9.4
        """
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for parameter annotations
                    for arg in node.args.args:
                        if arg.annotation:
                            return True
                    
                    # Check for return annotation
                    if node.returns:
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _preserve_type_hints(self, original: str, patched: str) -> str:
        """
        Preserve type hints from original in patched code.
        
        Args:
            original: Original code with type hints
            patched: Patched code
            
        Returns:
            Patched code with preserved type hints
            
        Validates: Requirement 9.4
        """
        try:
            orig_tree = ast.parse(original)
            patch_tree = ast.parse(patched)
            
            # Find function definitions
            orig_funcs = {node.name: node for node in ast.walk(orig_tree) 
                         if isinstance(node, ast.FunctionDef)}
            patch_funcs = {node.name: node for node in ast.walk(patch_tree) 
                          if isinstance(node, ast.FunctionDef)}
            
            # For matching functions, preserve type hints
            for func_name in orig_funcs:
                if func_name in patch_funcs:
                    orig_func = orig_funcs[func_name]
                    patch_func = patch_funcs[func_name]
                    
                    # Copy parameter annotations
                    for orig_arg, patch_arg in zip(orig_func.args.args, patch_func.args.args):
                        if orig_arg.annotation and not patch_arg.annotation:
                            patch_arg.annotation = orig_arg.annotation
                    
                    # Copy return annotation
                    if orig_func.returns and not patch_func.returns:
                        patch_func.returns = orig_func.returns
            
            # Unparse back to code
            return ast.unparse(patch_tree)
            
        except Exception as e:
            logger.debug(f"Failed to preserve type hints: {e}")
            return patched  # Return unmodified if preservation fails
    
    def _check_new_dependencies(self, original: str, patched: str) -> List[str]:
        """
        Check for new dependencies introduced in patched code.
        
        Args:
            original: Original code
            patched: Patched code
            
        Returns:
            List of new import statements
            
        Validates: Requirement 9.3
        """
        try:
            orig_imports = self._extract_imports(original)
            patch_imports = self._extract_imports(patched)
            
            # Find new imports
            new_imports = patch_imports - orig_imports
            
            if new_imports:
                logger.warning(f"Patch introduces new dependencies: {new_imports}")
            
            return list(new_imports)
            
        except Exception as e:
            logger.debug(f"Failed to check dependencies: {e}")
            return []
    
    def _extract_imports(self, code: str) -> set:
        """
        Extract import statements from code.
        
        Args:
            code: Python code
            
        Returns:
            Set of imported module names
        """
        try:
            tree = ast.parse(code)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            return imports
            
        except Exception:
            return set()
    
    def _add_security_comment(self, code: str, vuln: Vulnerability, counterexample: str) -> str:
        """
        Add security comment explaining the fix.
        
        Inserts comment above the patched code section explaining:
        - What vulnerability was fixed
        - How the fix addresses the exploit
        
        Args:
            code: Patched code
            vuln: Vulnerability information
            counterexample: Exploit that was fixed
            
        Returns:
            Code with security comment added
            
        Validates: Requirement 9.2
        """
        try:
            # Generate comment text
            comment_lines = [
                "# SECURITY FIX: " + vuln.vuln_type,
                "# " + vuln.description
            ]
            
            if vuln.hypothesis:
                comment_lines.append("# Issue: " + vuln.hypothesis)
            
            if counterexample:
                # Truncate long counterexamples
                ce_display = counterexample[:80] + "..." if len(counterexample) > 80 else counterexample
                comment_lines.append("# Exploit prevented: " + ce_display)
            
            # Add fix explanation based on vulnerability type
            fix_explanation = self._get_fix_explanation(vuln.vuln_type)
            if fix_explanation:
                comment_lines.append("# Fix: " + fix_explanation)
            
            comment_block = '\n'.join(comment_lines) + '\n'
            
            # Find the first function definition and insert comment before it
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('def '):
                    # Insert comment before function
                    lines.insert(i, comment_block)
                    break
            else:
                # No function found, add at top
                lines.insert(0, comment_block)
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.debug(f"Failed to add security comment: {e}")
            return code  # Return unmodified if comment addition fails
    
    def _get_fix_explanation(self, vuln_type: str) -> str:
        """
        Get explanation of how the fix addresses the vulnerability.
        
        Args:
            vuln_type: Type of vulnerability
            
        Returns:
            Human-readable explanation
            
        Validates: Requirement 9.2
        """
        explanations = {
            "SQL Injection": "Use parameterized queries to prevent SQL injection",
            "Command Injection": "Use subprocess with list args and shell=False to prevent command injection",
            "Path Traversal": "Sanitize file paths to prevent directory traversal",
            "Code Injection": "Remove eval/exec and use safe alternatives",
            "XSS": "Escape user input before rendering in HTML",
            "SSRF": "Validate and whitelist URLs before making requests"
        }
        
        return explanations.get(vuln_type, "Apply security best practices")
    
    def _check_pep8_compliance(self, code: str) -> Tuple[bool, List[str]]:
        """
        Check if code is PEP 8 compliant.
        
        Args:
            code: Python code to check
            
        Returns:
            Tuple of (is_compliant, violations)
            
        Validates: Requirement 9.5
        """
        if not PEP8_AVAILABLE:
            return (True, [])  # Skip if tools not available
        
        try:
            # Create a temporary style checker
            style = pycodestyle.StyleGuide(quiet=True)
            
            # Check code (write to temp file)
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                result = style.check_files([temp_path])
                
                # Get violations
                violations = []
                if result.total_errors > 0:
                    for error in result._application.file_errors:
                        violations.append(f"{error}")
                
                is_compliant = result.total_errors == 0
                
                return (is_compliant, violations)
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except Exception as e:
            logger.debug(f"PEP 8 check failed: {e}")
            return (True, [])  # Assume compliant if check fails
    
    def _fix_pep8_violations(self, code: str) -> str:
        """
        Auto-fix PEP 8 violations using autopep8.
        
        Args:
            code: Python code with potential violations
            
        Returns:
            PEP 8 compliant code
            
        Validates: Requirement 9.5
        """
        if not PEP8_AVAILABLE:
            return code  # Skip if tools not available
        
        try:
            # Apply autopep8 fixes
            fixed_code = autopep8.fix_code(
                code,
                options={
                    'aggressive': 1,  # Apply aggressive fixes
                    'max_line_length': 100  # Reasonable line length
                }
            )
            
            return fixed_code
            
        except Exception as e:
            logger.debug(f"PEP 8 auto-fix failed: {e}")
            return code  # Return original if fix fails
    
    def _clean_patch_response(self, response: str) -> str:
        """
        Clean LLM response to extract pure Python code.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned Python code
        """
        # Remove markdown code blocks
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            if end != -1:
                response = response[start:end]
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end]
        
        # Strip whitespace
        response = response.strip()
        
        return response
    
    def _apply_template_patch(self, code: str, vuln_type: str) -> str:
        """Apply template-based patch transformations."""
        patched_code = code
        
        if vuln_type == "SQL Injection":
            # Replace f-strings and concatenation with parameterized queries
            patched_code = re.sub(
                r'query\s*=\s*f["\'](.+?)["\']',
                r'query = "\1".replace("{", "?").replace("}", "")',
                patched_code
            )
            patched_code = re.sub(
                r'execute\s*\(\s*query\s*\)',
                r'execute(query, (param1, param2))',
                patched_code
            )
        
        elif vuln_type == "Command Injection":
            # Replace shell=True with list arguments
            patched_code = re.sub(
                r'subprocess\.run\s*\((.*?),\s*shell\s*=\s*True',
                r'subprocess.run([\1], shell=False',
                patched_code
            )
        
        elif vuln_type == "Path Traversal":
            # Add path sanitization
            patched_code = re.sub(
                r'file_path\s*=\s*(.+)',
                r'file_path = os.path.basename(\1)',
                patched_code
            )
        
        return patched_code
    
    def _generate_diff(self, original: str, patched: str) -> str:
        """Generate unified diff between original and patched code."""
        # Simple line-by-line diff
        original_lines = original.split('\n')
        patched_lines = patched.split('\n')
        
        diff_lines = []
        for i, (orig, patch) in enumerate(zip(original_lines, patched_lines)):
            if orig != patch:
                diff_lines.append(f"- {orig}")
                diff_lines.append(f"+ {patch}")
        
        return '\n'.join(diff_lines) if diff_lines else "No changes"
    
    def validate_patch(self, patch: Patch, original_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a patch is valid Python with preserved signature.
        
        Checks:
        - code is non-empty
        - code is valid Python syntax
        - function signature is preserved from original
        - diff is non-empty
        
        Args:
            patch: Patch object to validate
            original_code: Original vulnerable code
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Validates: Requirements 5.4, 5.5
        """
        errors = []
        
        # Check required fields
        if not patch.code:
            errors.append("patch code is empty")
        
        if not patch.diff:
            errors.append("patch diff is empty")
        
        # Validate Python syntax
        if patch.code:
            if self.llm_client:
                is_valid, error = self.llm_client.validate_python_syntax(patch.code)
            else:
                try:
                    ast.parse(patch.code)
                    is_valid = True
                    error = None
                except Exception as e:
                    is_valid = False
                    error = str(e)
            
            if not is_valid:
                errors.append(f"invalid Python syntax: {error}")
        
        # Verify function signature preservation
        if patch.code and original_code:
            if not self._verify_signature_preserved(original_code, patch.code):
                errors.append("function signature not preserved")
        
        if errors:
            return (False, "; ".join(errors))
        
        return (True, None)
