"""
SecureCodeAI - Binary Analysis Agent
Uses Angr for symbolic execution and vulnerability discovery in binaries.
"""

from typing import Dict, Any, List, Optional
import angr

import logging

from ..state import AgentState, Vulnerability, VerificationResult

logger = logging.getLogger(__name__)

class BinaryAnalyzerAgent:
    """
    Agent responsible for analyzing compiled binaries using Angr.
    """
    
    def __init__(self):
        self.project: Optional[angr.Project] = None
        
    def load_binary(self, binary_path: str):
        """Load the binary into Angr."""
        try:
            self.project = angr.Project(binary_path, auto_load_libs=False)
            logger.info(f"Successfully loaded binary: {binary_path}")
        except Exception as e:
            logger.error(f"Failed to load binary {binary_path}: {e}")
            raise e

    def generate_exploit_script(self, input_val: bytes, binary_path: str) -> str:
        """
        Generate a standalone Python script to reproduce the exploit.
        """
        # Escape bytes for Python string
        payload_repr = str(input_val)
        
        script = f"""
import sys
import os

def run_exploit():
    payload = {payload_repr}
    
    # Method 1: Print to stdout (for piping)
    # sys.stdout.buffer.write(payload)
    
    # Method 2: Run directly
    print(f"[*] Running exploit against {{os.path.basename('{binary_path}')}}")
    print(f"[*] Payload length: {{len(payload)}} bytes")
    
    try:
        from pwn import process
        p = process('{binary_path}')
        p.send(payload)
        p.interactive()
    except ImportError:
        print("[!] Pwntools not installed. saving payload to 'payload.bin'")
        with open('payload.bin', 'wb') as f:
            f.write(payload)
        print("[*] Run manually: cat payload.bin | {binary_path}")

if __name__ == "__main__":
    run_exploit()
"""
        return script

    def explore_vulnerability(self, entry_state: Optional[Any] = None) -> List[VerificationResult]:
        """
        Explore the binary to find vulnerability paths.
        This is a simplified example looking for straightforward unconstrained paths 
        or specific error states.
        """
        if not self.project:
            return [VerificationResult(verified=False, error_message="No binary loaded")]

        results = []
        
        # Default exploration strategy
        state = entry_state if entry_state else self.project.factory.entry_state()
        simgr = self.project.factory.simgr(state)
        
        # Example: Explore until we find a crash or specific target
        # For this prototype, we'll try to find 'unconstrained' states which often imply control flow hijacking
        simgr.explore(find=lambda s: s.regs.ip.symbolic, step_func=lambda l: l.drop(stash='active')) # Naive symbolic IP check

        if len(simgr.found) > 0:
            found_state = simgr.found[0]
            # Generate input that triggers this state
            input_val = found_state.posix.dumps(0)  # Dump stdin
            
            exploit_script = self.generate_exploit_script(input_val, self.project.filename)
            
            result = VerificationResult(
                verified=False,
                counterexample=exploit_script, # Return full script as counterexample
                error_message="Symbolic instruction pointer detected (potential exploitability)"
            )
            results.append(result)
        else:
            # If no obvious symbolic IP found, we might check for other things
            # This is a very basic placeholder for complex binary analysis
            results.append(VerificationResult(verified=True))
            
        return results

    def search_for_flags(self, patterns: List[str] = None) -> List[str]:
        """
        Search for CTF flag patterns in the binary strings.
        """
        found_flags = []
        
        if patterns is None:
            patterns = ["CTF{", "flag{", "FLAG{"]
            
        # Method 1: Raw file search (Result: Robust & Fast)
        if self.project and self.project.filename:
            try:
                with open(self.project.filename, "rb") as f:
                    content = f.read()
                    
                # Look for printable strings
                import re
                # Regex to find strings matching patterns
                for pattern in patterns:
                    # Look for pattern followed by printable chars until '}'
                    # e.g., CTF{...}
                    regex = bytes(pattern, 'utf-8') + b"[ -~]+}"
                    matches = re.findall(regex, content)
                    for m in matches:
                        found_flags.append(m.decode('utf-8', errors='ignore'))
            except Exception as e:
                logger.error(f"Error reading file for flags: {e}")

        # Method 2: Angr Memory Search (Fallback, existing logic removed for stability)
        # (Angr string loading can be flaky depending on backend)
            
        return list(set(found_flags)) # Deduplicate

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the binary analysis agent.
        """
        binary_path = state.get("binary_path")
        if not binary_path:
            return {"errors": ["No binary path provided for analysis"]}

        try:
            self.load_binary(binary_path)
            self.load_binary(binary_path)
            results = self.explore_vulnerability()
            
            # CTF Tooling: Search for flags
            flags = self.search_for_flags()
            flag_logs = [f"Found Flag: {f}" for f in flags]
            
            # Map results to contract/vulnerability updates if needed
            # For now, just return the verification results
            return {
                "verification_results": state.get("verification_results", []) + results,
                "logs": state.get("logs", []) + [f"Analyzed binary: {binary_path}"] + flag_logs
            }
            
        except Exception as e:
            return {
                "errors": state.get("errors", []) + [f"Binary analysis failed: {str(e)}"]
            }
