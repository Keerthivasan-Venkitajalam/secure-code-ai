"""
SecureCodeAI - Speculator Agent
Generates formal contracts (icontract decorators) for symbolic execution.
"""

import ast
import logging
import time
from typing import List, Optional, Tuple

from ..state import AgentState, Contract, Vulnerability
from ..llm_client import LLMClient
from ..prompts import CONTRACT_PROMPT


logger = logging.getLogger(__name__)


class SpeculatorAgent:
    """
    Speculator Agent: Generates formal security contracts.
    
    Takes vulnerabilities identified by Scanner and creates formal specifications
    (icontract decorators) that can be verified by symbolic execution.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize Speculator Agent.
        
        Args:
            llm_client: LLM client for contract generation (optional, uses templates if None)
        """
        self.llm_client = llm_client
        
        # Load few-shot examples for contract generation (Requirement 2.1)
        self.few_shot_examples = CONTRACT_PROMPT.few_shot_examples
        
        # Template contracts for common vulnerabilities (fallback)
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
                # Generate contract with retry logic (Requirements 2.1, 2.2, 2.5, 7.1)
                contract = self._generate_contract_with_retry(vuln, state.get("code", ""))
                
                if contract:
                    # Validate contract (Requirement 5.4, 5.5)
                    is_valid, error = self.validate_contract(contract)
                    if is_valid:
                        contracts.append(contract)
                        state["logs"].append(f"Speculator Agent: Generated contract for {vuln.vuln_type}")
                    else:
                        logger.warning(f"Invalid contract for {vuln.vuln_type}: {error}")
                        state["errors"].append(f"Speculator Agent: Invalid contract - {error}")
                else:
                    state["logs"].append(f"Speculator Agent: Failed to generate contract for {vuln.vuln_type}")
        
        except Exception as e:
            state["errors"].append(f"Speculator Agent: Error - {str(e)}")
            logger.error(f"Speculator execution error: {e}")
        
        state["contracts"] = contracts
        
        # Set current vulnerability for SymBot
        if vulnerabilities:
            state["current_vulnerability"] = vulnerabilities[0]
        
        execution_time = time.time() - start_time
        state["total_execution_time"] = state.get("total_execution_time", 0) + execution_time
        
        return state
    
    def _generate_contract_with_retry(
        self,
        vuln: Vulnerability,
        code: str,
        max_retries: int = 3
    ) -> Optional[Contract]:
        """
        Generate contract with automatic retry on syntax errors.
        
        Implements self-correction loop using LLMClient.generate_with_self_correction():
        1. Generate contract using LLM
        2. Validate syntax
        3. If invalid, retry with error feedback
        4. Return Contract object or None after max retries
        
        Args:
            vuln: Vulnerability to generate contract for
            code: Full source code
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            Contract object or None if generation fails
            
        Validates: Requirements 2.1, 2.2, 2.5, 7.1, 7.2, 7.3
        """
        # Extract target function name
        target_function = self._extract_function_at_line(code, vuln.location)
        
        if not target_function:
            logger.warning(f"Could not extract function for {vuln.location}")
            target_function = "unknown"
        
        # If no LLM client, use template
        if not self.llm_client:
            contract_code = self._generate_contract_template(vuln)
            return Contract(
                code=contract_code,
                vuln_type=vuln.vuln_type,
                target_function=target_function
            )
        
        # Use self-correction loop (Requirements 7.1, 7.2, 7.3)
        def prompt_builder(error_feedback: Optional[str]) -> str:
            return self._build_contract_prompt(vuln, target_function, error_feedback)
        
        def validator(output: str) -> tuple:
            # Clean and validate contract
            cleaned = self._clean_contract_response(output)
            is_valid, error = self.llm_client.validate_python_syntax(cleaned)
            return (is_valid, error)
        
        # Generate with self-correction
        params = CONTRACT_PROMPT.get_generation_params()
        contract_code = self.llm_client.generate_with_self_correction(
            prompt_builder,
            validator,
            max_retries=max_retries,
            max_tokens=params["max_tokens"],
            temperature=params["temperature"]
        )
        
        if contract_code:
            # Clean the final output
            contract_code = self._clean_contract_response(contract_code)
            logger.info(f"Contract generated successfully for {vuln.vuln_type}")
            return Contract(
                code=contract_code,
                vuln_type=vuln.vuln_type,
                target_function=target_function
            )
        
        # All retries failed - fall back to template
        logger.error(f"Failed to generate valid contract after {max_retries} attempts, using template")
        contract_code = self._generate_contract_template(vuln)
        return Contract(
            code=contract_code,
            vuln_type=vuln.vuln_type,
            target_function=target_function
        )
    
    def _build_contract_prompt(
        self,
        vuln: Vulnerability,
        function_name: str,
        error_feedback: Optional[str] = None
    ) -> str:
        """
        Build prompt for contract generation with optional error feedback.
        
        Args:
            vuln: Vulnerability to generate contract for
            function_name: Target function name
            error_feedback: Error message from previous attempt (if any)
            
        Returns:
            Formatted prompt string
        """
        # Get relevant examples for this vulnerability type (Requirement 2.3, 2.4)
        examples = self._get_relevant_examples(vuln.vuln_type)
        
        # Build base prompt
        base_prompt = CONTRACT_PROMPT.format(
            vuln_type=vuln.vuln_type,
            hypothesis=vuln.hypothesis or vuln.description,
            function_name=function_name
        )
        
        # Add error feedback if this is a retry
        if error_feedback:
            base_prompt += f"\n\n# Previous Attempt Error\n{error_feedback}\n\nGenerate corrected contract:\n```python"
        
        return base_prompt
    
    def _get_relevant_examples(self, vuln_type: str) -> str:
        """
        Get few-shot examples for specific vulnerability type.
        
        Args:
            vuln_type: Type of vulnerability
            
        Returns:
            Formatted examples string
            
        Validates: Requirements 2.3, 2.4, 8.1, 8.2, 8.3
        """
        return self.few_shot_examples.get(vuln_type, "")
    
    def _generate_contract_template(self, vuln: Vulnerability) -> str:
        """
        Generate contract using template (fallback when LLM unavailable).
        
        Args:
            vuln: Vulnerability to generate contract for
            
        Returns:
            icontract decorator code
        """
        return self.contract_templates.get(
            vuln.vuln_type,
            "@icontract.ensure(lambda result: result is not None)"
        )
    
    def _clean_contract_response(self, response: str) -> str:
        """
        Clean LLM response to extract pure icontract code.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Cleaned contract code
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
        
        # Ensure it starts with @icontract
        if not response.startswith("@icontract"):
            # Try to find the first @icontract line
            lines = response.split('\n')
            contract_lines = [line for line in lines if line.strip().startswith("@icontract")]
            if contract_lines:
                response = '\n'.join(contract_lines)
        
        return response
    
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
    
    def validate_contract(self, contract: Contract) -> Tuple[bool, Optional[str]]:
        """
        Validate that a contract is valid Python with icontract decorators.
        
        Checks:
        - code is non-empty
        - code is valid Python syntax
        - code contains at least one @icontract decorator
        - vuln_type is non-empty
        - target_function is non-empty
        
        Args:
            contract: Contract object to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Validates: Requirements 5.4, 5.5
        """
        errors = []
        
        # Check required fields
        if not contract.code:
            errors.append("contract code is empty")
        
        if not contract.vuln_type:
            errors.append("vuln_type is empty")
        
        if not contract.target_function:
            errors.append("target_function is empty")
        
        # Validate Python syntax
        if contract.code:
            if self.llm_client:
                is_valid, error = self.llm_client.validate_python_syntax(contract.code)
            else:
                try:
                    ast.parse(contract.code)
                    is_valid = True
                    error = None
                except Exception as e:
                    is_valid = False
                    error = str(e)
            
            if not is_valid:
                errors.append(f"invalid Python syntax: {error}")
        
        # Check for icontract decorators
        if contract.code and "@icontract" not in contract.code:
            errors.append("contract does not contain @icontract decorators")
        
        if errors:
            return (False, "; ".join(errors))
        
        return (True, None)
