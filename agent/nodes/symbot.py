"""
SecureCodeAI - SymBot Agent
Performs symbolic execution verification using CrossHair/Angr.
"""

import subprocess
import tempfile
import os
import time
from typing import Optional

from ..state import AgentState, VerificationResult as StateVerificationResult, Contract


class SymBotAgent:
    """
    SymBot Agent: Verifies code against contracts using symbolic execution.
    
    Uses:
    1. CrossHair for Python symbolic execution
    2. Angr for binary analysis (advanced track)
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize SymBot Agent.
        
        Args:
            timeout: Maximum time for symbolic execution per contract
        """
        self.timeout = timeout
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute SymBot Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with verification results
        """
        start_time = time.time()
        state["logs"].append("SymBot Agent: Starting symbolic execution...")
        
        contracts = state.get("contracts", [])
        code = state.get("code", "")
        verification_results = []
        
        try:
            for contract in contracts:
                # Verify contract
                result = self._verify_with_crosshair(code, contract)
                verification_results.append(result)
                
                if result.counterexample:
                    state["logs"].append(f"SymBot Agent: Vulnerability confirmed - {contract.vuln_type}")
                    break  # Process one vulnerability at a time
                elif result.error_message:
                    logger.error(f"SymBot verification failed: {result.error_message}")
                    state["errors"].append(f"SymBot Error: {result.error_message}")
                else:
                    state["logs"].append(f"SymBot Agent: No vulnerability found for {contract.vuln_type}")
        
        except Exception as e:
            state["errors"].append(f"SymBot Agent: Error - {str(e)}")
        
        state["verification_results"] = verification_results
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        return state
    
    def _verify_with_crosshair(self, code: str, contract: Contract) -> StateVerificationResult:
        """
        Verify code with CrossHair symbolic execution.
        
        Args:
            code: Full source code
            contract: Contract to verify
            
        Returns:
            Verification result
        """
        # Extract function to verify
        function_code = self._extract_function(code, contract.target_function)
        
        if not function_code:
            return StateVerificationResult(
                verified=False,
                error_message="Could not extract target function"
            )
        
        # Combine contract and code
        full_code = f"""import icontract
from typing import Any
import os

{contract.code}
{function_code}
"""
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_code)
            temp_file = f.name
        
        try:
            start_time = time.time()
            
            # Run CrossHair
            result = subprocess.run(
                [
                    "crosshair",
                    "check",
                    "--per_condition_timeout", str(self.timeout),
                    temp_file
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout + 10
            )
            
            execution_time = time.time() - start_time
            
            # Parse output
            stdout = result.stdout
            
            # Check for counterexamples
            if "false when calling" in stdout.lower() or "counterexample" in stdout.lower():
                counterexample = self._extract_counterexample(stdout)
                return StateVerificationResult(
                    verified=False,
                    counterexample=counterexample,
                    execution_time=execution_time
                )
            elif "no issues found" in stdout.lower() or result.returncode == 0:
                return StateVerificationResult(
                    verified=True,
                    execution_time=execution_time
                )
            else:
                return StateVerificationResult(
                    verified=False,
                    error_message=result.stderr or stdout,
                    execution_time=execution_time
                )
        
        except subprocess.TimeoutExpired:
            return StateVerificationResult(
                verified=False,
                error_message=f"Timeout after {self.timeout}s",
                execution_time=self.timeout
            )
        
        finally:
            os.unlink(temp_file)
    
    def _extract_function(self, code: str, function_name: str) -> str:
        """Extract a specific function from code."""
        if not function_name:
            return ""
        
        lines = code.split('\n')
        function_lines = []
        in_function = False
        indent_level = 0
        
        for line in lines:
            if f"def {function_name}(" in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                function_lines.append(line)
            elif in_function:
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= indent_level:
                    # End of function
                    break
                function_lines.append(line)
        
        return '\n'.join(function_lines)
    
    def _extract_counterexample(self, output: str) -> str:
        """Extract counterexample from CrossHair output."""
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'when calling' in line.lower() or 'counterexample' in line.lower():
                return '\n'.join(lines[i:min(i+5, len(lines))])
        return output
