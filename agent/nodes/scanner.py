"""
SecureCodeAI - Scanner Agent
Identifies potential vulnerability hotspots using AST analysis and static analysis tools.
"""

import ast
import re
from typing import List, Dict
import time

from ..state import AgentState, Vulnerability


class ScannerAgent:
    """
    Scanner Agent: Identifies vulnerability hotspots in code.
    
    Uses:
    1. AST parsing (Python's ast module)
    2. Pattern matching for dangerous functions (eval, exec, subprocess.run with shell=True)
    3. Static analysis tools (Bandit, Semgrep) - optional integration
    """
    
    def __init__(self):
        """Initialize Scanner Agent."""
        self.dangerous_patterns = {
            "SQL Injection": [
                r"execute\s*\(\s*f['\"].*?\{.*?\}",  # f-string in execute()
                r"execute\s*\(\s*['\"].*?\%",  # % formatting in execute()
                r"execute\s*\(\s*.*?\+",  # String concatenation in execute()
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
        
        code = state.get("code", "")
        vulnerabilities = []
        
        try:
            # Pattern-based scanning
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
        
        except Exception as e:
            state["errors"].append(f"Scanner Agent: Error - {str(e)}")
        
        # Deduplicate vulnerabilities by location
        unique_vulns = []
        seen_locations = set()
        for vuln in vulnerabilities:
            if vuln.location not in seen_locations:
                unique_vulns.append(vuln)
                seen_locations.add(vuln.location)
        
        state["vulnerabilities"] = unique_vulns
        state["logs"].append(f"Scanner Agent: Found {len(unique_vulns)} potential vulnerabilities")
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        return state
    
    def _scan_ast(self, tree: ast.AST, file_path: str) -> List[Vulnerability]:
        """Scan AST for vulnerable patterns."""
        vulnerabilities = []
        
        for node in ast.walk(tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    
                    # eval/exec detection
                    if func_name in ['eval', 'exec']:
                        vulnerabilities.append(Vulnerability(
                            location=f"{file_path}:{node.lineno}",
                            vuln_type="Code Injection",
                            severity="CRITICAL",
                            description=f"Use of dangerous function: {func_name}()",
                            confidence=0.9
                        ))
                
                # Check for subprocess/os.system with shell=True
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['system', 'popen']:
                        vulnerabilities.append(Vulnerability(
                            location=f"{file_path}:{node.lineno}",
                            vuln_type="Command Injection",
                            severity="HIGH",
                            description=f"Dangerous system call: {node.func.attr}",
                            confidence=0.85
                        ))
            
            # Check for SQL string formatting
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'execute':
                    # Check if argument uses f-string or string concatenation
                    if node.args:
                        arg = node.args[0]
                        if isinstance(arg, ast.JoinedStr):  # f-string
                            vulnerabilities.append(Vulnerability(
                                location=f"{file_path}:{node.lineno}",
                                vuln_type="SQL Injection",
                                severity="HIGH",
                                description="SQL query uses f-string formatting",
                                confidence=0.9
                            ))
                        elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):  # String concatenation
                            vulnerabilities.append(Vulnerability(
                                location=f"{file_path}:{node.lineno}",
                                vuln_type="SQL Injection",
                                severity="HIGH",
                                description="SQL query uses string concatenation",
                                confidence=0.85
                            ))
        
        return vulnerabilities
