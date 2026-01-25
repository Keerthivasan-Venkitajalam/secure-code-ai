"""
SecureCodeAI - Smart Contract Analysis Agent
Scans Solidity code for common vulnerabilities using pattern matching (Lite Mode) 
and integrates with Slither if available (Advanced Mode).
"""

import re
import logging
import shutil
import subprocess
from typing import Dict, Any, List

from ..state import AgentState, Vulnerability

logger = logging.getLogger(__name__)

class SmartContractAgent:
    """
    Agent responsible for analyzing Solidity smart contracts.
    """
    
    # Common Solidity Vulnerability Patterns
    VULN_PATTERNS = [
        {
            "name": "Reentrancy",
            "regex": r"call\.value\(.*\)",
            "severity": "HIGH",
            "description": "Detected use of low-level call.value(), which can lead to reentrancy attacks. Use transfer() or send() instead, or ensure CEI pattern."
        },
        {
            "name": "Tx.Origin Authorization",
            "regex": r"tx\.origin",
            "severity": "MEDIUM",
            "description": "Use of tx.origin for authorization is insecure and can be exploited via phishing/intermediary contracts. Use msg.sender instead."
        },
        {
            "name": "Unchecked Low-Level Call",
            "regex": r"\.call\(",
            "severity": "MEDIUM",
            "description": "Low-level .call() does not revert on failure. Ensure the return value is checked."
        },
        {
            "name": "Selfdestruct / Suicide",
            "regex": r"selfdestruct\(|suicide\(",
            "severity": "CRITICAL",
            "description": "Use of selfdestruct can be dangerous. Ensure strict access control."
        },
        {
            "name": "Block Timestamp Dependence",
            "regex": r"block\.timestamp|now",
            "severity": "LOW",
            "description": "Reliance on block.timestamp (or 'now') for critical logic can be manipulated by miners."
        }
    ]

    def __init__(self):
        self.slither_available = shutil.which("slither") is not None

    def scan_patterns(self, code: str) -> List[Vulnerability]:
        """Scan code against regex patterns."""
        vulnerabilities = []
        for pattern in self.VULN_PATTERNS:
            matches = re.finditer(pattern["regex"], code)
            for match in matches:
                # Get line number
                line_no = code.count('\n', 0, match.start()) + 1
                vuln = Vulnerability(
                    location=f"Line {line_no}",
                    vuln_type=pattern["name"],
                    severity=pattern["severity"],
                    description=pattern["description"],
                    confidence=0.8
                )
                vulnerabilities.append(vuln)
        return vulnerabilities

    def execute(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the smart contract analysis.
        """
        code = state.get("code")
        file_path = state.get("file_path", "")
        
        # Only run if it's a solidity file
        if not file_path.endswith(".sol"):
             return {}

        logger.info(f"Scanning smart contract: {file_path}")
        
        detected_vulns = self.scan_patterns(code)
        
        return {
            "vulnerabilities": state.get("vulnerabilities", []) + detected_vulns,
            "logs": state.get("logs", []) + [f"Scanned Solidity contract: {file_path}. Found {len(detected_vulns)} issues."]
        }
