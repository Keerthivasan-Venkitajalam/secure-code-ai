"""
SecureCodeAI - Patcher Agent
Generates security patches based on counterexamples from symbolic execution.
"""

import time
import re
from typing import Optional

from ..state import AgentState, Patch, VerificationResult


class PatcherAgent:
    """
    Patcher Agent: Generates and validates security patches.
    
    Uses LLM to generate patches that fix vulnerabilities found by SymBot.
    """
    
    def __init__(self, llm=None):
        """
        Initialize Patcher Agent.
        
        Args:
            llm: LLM instance for patch generation (optional, uses templates if None)
        """
        self.llm = llm
        
        # Template patches for common vulnerabilities
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
            # Generate patch
            code = state.get("code", "")
            patch_code = self._generate_patch(
                code,
                current_vuln.vuln_type,
                latest_result.counterexample
            )
            
            # Create patch object
            patch = Patch(
                code=patch_code,
                diff=self._generate_diff(code, patch_code),
                verified=False
            )
            
            state["current_patch"] = patch
            state["patches"] = state.get("patches", []) + [patch]
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            
            state["logs"].append(f"Patcher Agent: Generated patch (iteration {state['iteration_count']})")
        
        except Exception as e:
            state["errors"].append(f"Patcher Agent: Error - {str(e)}")
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        return state
    
    def _generate_patch(self, code: str, vuln_type: str, counterexample: str) -> str:
        """
        Generate a security patch.
        
        Args:
            code: Original vulnerable code
            vuln_type: Type of vulnerability
            counterexample: Exploit PoC from SymBot
            
        Returns:
            Patched code
        """
        if self.llm:
            # Use LLM to generate custom patch
            # TODO: Implement LLM-based patch generation
            pass
        
        # Fall back to template-based patching
        return self._apply_template_patch(code, vuln_type)
    
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
