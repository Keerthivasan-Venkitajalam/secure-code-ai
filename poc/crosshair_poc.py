#!/usr/bin/env python3
"""
SecureCodeAI - Proof of Concept: CrossHair Integration
Tests symbolic execution with CrossHair for vulnerability verification.
"""

import argparse
import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result from symbolic execution verification."""
    verified: bool
    counterexample: Optional[str]
    error_message: Optional[str]
    execution_time: float


class CrossHairVerifier:
    """Wrapper for CrossHair symbolic execution tool."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize CrossHair verifier.
        
        Args:
            timeout: Maximum time (seconds) for symbolic execution per function
        """
        self.timeout = timeout
        self._check_crosshair_installed()
    
    def _check_crosshair_installed(self):
        """Verify CrossHair is installed and accessible."""
        try:
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "crosshair", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ CrossHair version: {result.stdout.strip()}")
            else:
                raise RuntimeError("CrossHair not found")
        except (subprocess.SubprocessError, FileNotFoundError):
            print("❌ Error: CrossHair not installed")
            print("Install with: pip install crosshair-tool z3-solver")
            exit(1)
    
    def verify_code_with_contract(self, code: str, contract: str) -> VerificationResult:
        """
        Verify code against a formal contract using symbolic execution.
        
        Args:
            code: Python function source code
            contract: icontract decorator with preconditions/postconditions
            
        Returns:
            VerificationResult with counterexample if vulnerability found
        """
        import time
        
        # Combine contract and code
        full_code = f"""import icontract
from typing import Any

{contract}
{code}
"""
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_code)
            temp_file = f.name
        
        try:
            start_time = time.time()
            
            # Run CrossHair check
            result = subprocess.run(
                [
                    sys.executable, "-m", "crosshair",
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
            stderr = result.stderr
            
            # Check for counterexamples (vulnerabilities)
            if "false when calling" in stdout.lower() or "counterexample" in stdout.lower():
                # Extract counterexample
                counterexample = self._extract_counterexample(stdout)
                return VerificationResult(
                    verified=False,
                    counterexample=counterexample,
                    error_message=None,
                    execution_time=execution_time
                )
            elif "no issues found" in stdout.lower() or result.returncode == 0:
                return VerificationResult(
                    verified=True,
                    counterexample=None,
                    error_message=None,
                    execution_time=execution_time
                )
            else:
                # Execution error
                return VerificationResult(
                    verified=False,
                    counterexample=None,
                    error_message=stderr or stdout,
                    execution_time=execution_time
                )
        
        except subprocess.TimeoutExpired:
            return VerificationResult(
                verified=False,
                counterexample=None,
                error_message=f"Timeout after {self.timeout}s (path explosion likely)",
                execution_time=self.timeout
            )
        
        finally:
            # Clean up temp file
            os.unlink(temp_file)
    
    def _extract_counterexample(self, output: str) -> str:
        """Extract counterexample input from CrossHair output."""
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'when calling' in line.lower() or 'counterexample' in line.lower():
                # Return next few lines containing the input
                return '\n'.join(lines[i:min(i+5, len(lines))])
        return output


def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - CrossHair PoC")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for symbolic execution (seconds)")
    
    args = parser.parse_args()
    
    print("="*70)
    print("CROSSHAIR SYMBOLIC EXECUTION DEMO")
    print("="*70 + "\n")
    
    # Initialize verifier
    verifier = CrossHairVerifier(timeout=args.timeout)
    
    # Example 1: SQL Injection Vulnerability
    print("📝 Example 1: SQL Injection Detection\n")
    
    vulnerable_code = '''def execute_query(user_input: str) -> str:
    """Execute SQL query with user input."""
    query = f"SELECT * FROM users WHERE name='{user_input}'"
    return query
'''
    
    # Contract: Ensure no SQL injection characters in output
    sql_contract = '''@icontract.ensure(lambda result: "'" not in result or result.count("'") <= 2)
@icontract.ensure(lambda result: "--" not in result)
@icontract.ensure(lambda result: ";" not in result or result.count(";") <= 1)
'''
    
    print("Code:")
    print(vulnerable_code)
    print("\nContract (Formal Specification):")
    print(sql_contract)
    
    print("\n🔍 Running symbolic execution...")
    result1 = verifier.verify_code_with_contract(vulnerable_code, sql_contract)
    
    print(f"\n{'='*70}")
    print("RESULT:")
    print(f"{'='*70}")
    print(f"Verified: {result1.verified}")
    print(f"Execution Time: {result1.execution_time:.2f}s")
    
    if result1.counterexample:
        print(f"\n⚠️  VULNERABILITY FOUND!")
        print(f"Counterexample (Exploit PoC):")
        print(result1.counterexample)
    elif result1.error_message:
        print(f"\n❌ Verification Error:")
        print(result1.error_message)
    else:
        print("\n✅ No vulnerabilities detected")
    
    # Example 2: Buffer Overflow (Integer Range)
    print(f"\n\n{'='*70}")
    print("📝 Example 2: Integer Overflow Detection\n")
    
    overflow_code = '''def allocate_buffer(size: int) -> list:
    """Allocate buffer of given size."""
    if size < 0:
        return []
    return [0] * size
'''
    
    overflow_contract = '''@icontract.require(lambda size: 0 <= size <= 1000000)
@icontract.ensure(lambda result, size: len(result) == size if size >= 0 else len(result) == 0)
'''
    
    print("Code:")
    print(overflow_code)
    print("\nContract:")
    print(overflow_contract)
    
    print("\n🔍 Running symbolic execution...")
    result2 = verifier.verify_code_with_contract(overflow_code, overflow_contract)
    
    print(f"\n{'='*70}")
    print("RESULT:")
    print(f"{'='*70}")
    print(f"Verified: {result2.verified}")
    print(f"Execution Time: {result2.execution_time:.2f}s")
    
    if result2.counterexample:
        print(f"\n⚠️  VULNERABILITY FOUND!")
        print(f"Counterexample:")
        print(result2.counterexample)
    elif result2.error_message:
        print(f"\n❌ Verification Error:")
        print(result2.error_message)
    else:
        print("\n✅ No vulnerabilities detected")
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total Examples: 2")
    print(f"Vulnerabilities Found: {sum([not r.verified and not r.error_message for r in [result1, result2]])}")
    print(f"Total Execution Time: {result1.execution_time + result2.execution_time:.2f}s")


if __name__ == "__main__":
    main()
