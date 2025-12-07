"""
SecureCodeAI - Speculator Agent
Generates formal contracts (icontract decorators) for symbolic execution.
"""

import time
from typing import List

from ..state import AgentState, Contract, Vulnerability


class SpeculatorAgent:
    """
    Speculator Agent: Generates formal security contracts.
    
    Takes vulnerabilities identified by Scanner and creates formal specifications
    (icontract decorators) that can be verified by symbolic execution.
    """
    
    def __init__(self, llm=None):
        """
        Initialize Speculator Agent.
        
        Args:
            llm: LLM instance for contract generation (optional, uses templates if None)
        """
        self.llm = llm
        
        # Template contracts for common vulnerabilities
        self.contract_templates = {
            "SQL Injection": """@icontract.ensure(lambda result: "'" not in str(result) or str(result).count("'") <= 2)
@icontract.ensure(lambda result: "--" not in str(result))
@icontract.ensure(lambda result: ";" not in str(result) or str(result).count(";") <= 1)
@icontract.ensure(lambda result: " OR " not in str(result).upper())""",
            
            "Command Injection": """@icontract.require(lambda cmd: "|" not in cmd and ";" not in cmd and "&" not in cmd)
@icontract.require(lambda cmd: "`" not in cmd and "$(" not in cmd)
@icontract.ensure(lambda result: result is not None)""",
            
            "Path Traversal": """@icontract.require(lambda path: ".." not in path)
@icontract.require(lambda path: not path.startswith("/"))
@icontract.ensure(lambda result, path: os.path.basename(path) in str(result))""",
            
            "Code Injection": """@icontract.require(lambda code: "import" not in code)
@icontract.require(lambda code: "__" not in code)
@icontract.ensure(lambda result: result is not None)"""
        }
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute Speculator Agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated contracts
        """
        start_time = time.time()
        state["logs"].append("Speculator Agent: Generating contracts...")
        
        vulnerabilities = state.get("vulnerabilities", [])
        contracts = []
        
        try:
            for vuln in vulnerabilities:
                # Extract function from code slice
                code = state.get("code", "")
                target_function = self._extract_function_at_line(code, vuln.location)
                
                if target_function:
                    # Generate contract
                    contract_code = self._generate_contract(vuln)
                    
                    contracts.append(Contract(
                        code=contract_code,
                        vuln_type=vuln.vuln_type,
                        target_function=target_function
                    ))
                    
                    state["logs"].append(f"Speculator Agent: Generated contract for {vuln.vuln_type}")
        
        except Exception as e:
            state["errors"].append(f"Speculator Agent: Error - {str(e)}")
        
        state["contracts"] = contracts
        
        # Set current vulnerability for SymBot
        if vulnerabilities:
            state["current_vulnerability"] = vulnerabilities[0]
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        return state
    
    def _generate_contract(self, vuln: Vulnerability) -> str:
        """
        Generate icontract contract for a vulnerability.
        
        Args:
            vuln: Vulnerability to generate contract for
            
        Returns:
            icontract decorator code
        """
        if self.llm:
            # Use LLM to generate custom contract
            # TODO: Implement LLM-based contract generation
            pass
        
        # Fall back to template
        return self.contract_templates.get(
            vuln.vuln_type,
            "@icontract.ensure(lambda result: result is not None)"
        )
    
    def _extract_function_at_line(self, code: str, location: str) -> str:
        """
        Extract function name at a specific line.
        
        Args:
            code: Full source code
            location: Location string (e.g., "file.py:42")
            
        Returns:
            Function name or empty string
        """
        try:
            # Parse line number from location
            line_num = int(location.split(":")[-1])
            
            # Simple heuristic: find function definition above the line
            lines = code.split('\n')
            for i in range(line_num - 1, -1, -1):
                if lines[i].strip().startswith('def '):
                    # Extract function name
                    func_name = lines[i].split('def ')[1].split('(')[0].strip()
                    return func_name
        
        except (ValueError, IndexError):
            pass
        
        return ""
