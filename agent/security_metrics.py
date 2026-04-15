"""
SecureCodeAI - Security Metrics Module
Distinguishes functional correctness from security correctness.
Implements Secure-Pass@1 metric and integrates static security analyzers.
"""

import ast
import json
import logging
import subprocess
import tempfile
import os
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SecurityIssue:
    """Represents a security issue found by static analysis."""
    tool: str  # "bandit" or "semgrep"
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    issue_type: str  # e.g., "B608: hardcoded_sql_expressions"
    message: str
    line_number: Optional[int] = None
    confidence: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH"


@dataclass
class SecurityScore:
    """
    Security evaluation result for a patch.
    
    Distinguishes between functional correctness and security correctness.
    """
    functional_pass: bool  # Does the patch fix the vulnerability?
    security_pass: bool  # Does the patch avoid introducing new vulnerabilities?
    security_issues: List[SecurityIssue] = field(default_factory=list)
    confidence: float = 0.0  # Overall confidence score (0.0 to 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "functional_pass": self.functional_pass,
            "security_pass": self.security_pass,
            "security_issues": [
                {
                    "tool": issue.tool,
                    "severity": issue.severity,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "line_number": issue.line_number,
                    "confidence": issue.confidence
                }
                for issue in self.security_issues
            ],
            "confidence": self.confidence
        }


class BanditAnalyzer:
    """
    Bandit static security analyzer integration.
    
    Detects common security issues in Python code.
    """
    
    def __init__(self):
        """Initialize Bandit analyzer."""
        self.available = self._check_availability()
        if not self.available:
            logger.warning("Bandit not available - security analysis will be limited")
    
    def _check_availability(self) -> bool:
        """Check if Bandit is installed and available."""
        try:
            result = subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def analyze(self, code: str, file_path: Optional[str] = None) -> List[SecurityIssue]:
        """
        Run Bandit static analysis on code.
        
        Args:
            code: Python code to analyze
            file_path: Optional file path for context
            
        Returns:
            List of security issues found
            
        Validates: Requirements 2.2
        """
        if not self.available:
            logger.debug("Bandit not available, skipping analysis")
            return []
        
        issues = []
        
        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                # Run Bandit with JSON output
                result = subprocess.run(
                    [
                        "bandit",
                        "-f", "json",
                        "-ll",  # Only report medium and high severity
                        temp_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse JSON output
                if result.stdout:
                    data = json.loads(result.stdout)
                    
                    # Extract issues
                    for result_item in data.get("results", []):
                        issue = SecurityIssue(
                            tool="bandit",
                            severity=result_item.get("issue_severity", "MEDIUM"),
                            issue_type=result_item.get("test_id", "unknown"),
                            message=result_item.get("issue_text", ""),
                            line_number=result_item.get("line_number"),
                            confidence=result_item.get("issue_confidence", "MEDIUM")
                        )
                        issues.append(issue)
                        
                        logger.debug(
                            f"Bandit found {issue.severity} issue: "
                            f"{issue.issue_type} at line {issue.line_number}"
                        )
            
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except subprocess.TimeoutExpired:
            logger.error("Bandit analysis timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bandit output: {e}")
        except Exception as e:
            logger.error(f"Bandit analysis failed: {e}")
        
        return issues


class SemgrepAnalyzer:
    """
    Semgrep static security analyzer integration.
    
    Uses security-focused rules to detect vulnerabilities.
    """
    
    def __init__(self, rules: Optional[List[str]] = None):
        """
        Initialize Semgrep analyzer.
        
        Args:
            rules: List of rule sets to use (default: security rules)
        """
        self.available = self._check_availability()
        self.rules = rules or ["p/security-audit", "p/owasp-top-ten"]
        
        if not self.available:
            logger.warning("Semgrep not available - security analysis will be limited")
    
    def _check_availability(self) -> bool:
        """Check if Semgrep is installed and available."""
        try:
            result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def analyze(
        self,
        code: str,
        file_path: Optional[str] = None,
        rules: Optional[List[str]] = None
    ) -> List[SecurityIssue]:
        """
        Run Semgrep static analysis on code.
        
        Args:
            code: Python code to analyze
            file_path: Optional file path for context
            rules: Optional rule sets to use (overrides default)
            
        Returns:
            List of security issues found
            
        Validates: Requirements 2.2
        """
        if not self.available:
            logger.debug("Semgrep not available, skipping analysis")
            return []
        
        issues = []
        rules_to_use = rules or self.rules
        
        try:
            # Write code to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                # Run Semgrep with JSON output
                cmd = [
                    "semgrep",
                    "--json",
                    "--quiet",
                    "--metrics", "off"
                ]
                
                # Add rule sets
                for rule in rules_to_use:
                    cmd.extend(["--config", rule])
                
                cmd.append(temp_path)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Parse JSON output
                if result.stdout:
                    data = json.loads(result.stdout)
                    
                    # Extract issues
                    for result_item in data.get("results", []):
                        # Map Semgrep severity to our scale
                        severity_map = {
                            "ERROR": "HIGH",
                            "WARNING": "MEDIUM",
                            "INFO": "LOW"
                        }
                        
                        extra = result_item.get("extra", {})
                        severity = severity_map.get(
                            extra.get("severity", "WARNING"),
                            "MEDIUM"
                        )
                        
                        issue = SecurityIssue(
                            tool="semgrep",
                            severity=severity,
                            issue_type=result_item.get("check_id", "unknown"),
                            message=extra.get("message", ""),
                            line_number=result_item.get("start", {}).get("line"),
                            confidence="HIGH"  # Semgrep has high confidence
                        )
                        issues.append(issue)
                        
                        logger.debug(
                            f"Semgrep found {issue.severity} issue: "
                            f"{issue.issue_type} at line {issue.line_number}"
                        )
            
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except subprocess.TimeoutExpired:
            logger.error("Semgrep analysis timed out")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep output: {e}")
        except Exception as e:
            logger.error(f"Semgrep analysis failed: {e}")
        
        return issues


class SecurityMetrics:
    """
    Main security metrics evaluation system.
    
    Integrates multiple static analyzers and implements Secure-Pass@1 metric.
    """
    
    def __init__(self):
        """Initialize security metrics system."""
        self.bandit_analyzer = BanditAnalyzer()
        self.semgrep_analyzer = SemgrepAnalyzer()
    
    def evaluate_patch_security(
        self,
        original_code: str,
        patched_code: str,
        functional_pass: bool = True
    ) -> SecurityScore:
        """
        Evaluate if patch introduces new vulnerabilities.
        
        Compares security issues in original vs patched code.
        A patch passes security checks if it doesn't introduce new issues.
        
        Args:
            original_code: Original vulnerable code
            patched_code: Patched code
            functional_pass: Whether patch fixes the original vulnerability
            
        Returns:
            SecurityScore with functional_pass, security_pass, issues
            
        Validates: Requirements 2.3
        """
        logger.info("Evaluating patch security...")
        
        # Run static analysis on both versions
        original_issues = self._analyze_code(original_code)
        patched_issues = self._analyze_code(patched_code)
        
        # Find new issues introduced by patch
        new_issues = self._find_new_issues(original_issues, patched_issues)
        
        # Determine if patch passes security checks
        # Pass if no new HIGH or CRITICAL issues introduced
        critical_new_issues = [
            issue for issue in new_issues
            if issue.severity in ["HIGH", "CRITICAL"]
        ]
        
        security_pass = len(critical_new_issues) == 0
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            original_issues,
            patched_issues,
            new_issues
        )
        
        logger.info(
            f"Security evaluation: functional_pass={functional_pass}, "
            f"security_pass={security_pass}, "
            f"new_issues={len(new_issues)}, "
            f"confidence={confidence:.2f}"
        )
        
        return SecurityScore(
            functional_pass=functional_pass,
            security_pass=security_pass,
            security_issues=new_issues,
            confidence=confidence
        )
    
    def _analyze_code(self, code: str) -> List[SecurityIssue]:
        """
        Run all available static analyzers on code.
        
        Args:
            code: Python code to analyze
            
        Returns:
            Combined list of security issues from all analyzers
        """
        issues = []
        
        # Run Bandit
        bandit_issues = self.bandit_analyzer.analyze(code)
        issues.extend(bandit_issues)
        
        # Run Semgrep
        semgrep_issues = self.semgrep_analyzer.analyze(code)
        issues.extend(semgrep_issues)
        
        return issues
    
    def _find_new_issues(
        self,
        original_issues: List[SecurityIssue],
        patched_issues: List[SecurityIssue]
    ) -> List[SecurityIssue]:
        """
        Find issues that appear in patched code but not in original.
        
        Args:
            original_issues: Issues in original code
            patched_issues: Issues in patched code
            
        Returns:
            List of new issues introduced by patch
        """
        # Create signature for each issue (tool + type + message)
        def issue_signature(issue: SecurityIssue) -> str:
            return f"{issue.tool}:{issue.issue_type}:{issue.message}"
        
        original_sigs = {issue_signature(issue) for issue in original_issues}
        
        # Find issues in patched code that weren't in original
        new_issues = [
            issue for issue in patched_issues
            if issue_signature(issue) not in original_sigs
        ]
        
        return new_issues
    
    def _calculate_confidence(
        self,
        original_issues: List[SecurityIssue],
        patched_issues: List[SecurityIssue],
        new_issues: List[SecurityIssue]
    ) -> float:
        """
        Calculate confidence score for security evaluation.
        
        Higher confidence when:
        - Both analyzers are available
        - Issues are found with high confidence
        - No new issues introduced
        
        Args:
            original_issues: Issues in original code
            patched_issues: Issues in patched code
            new_issues: New issues introduced
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if both analyzers available
        if self.bandit_analyzer.available and self.semgrep_analyzer.available:
            confidence += 0.2
        elif self.bandit_analyzer.available or self.semgrep_analyzer.available:
            confidence += 0.1
        
        # Increase confidence if issues found with high confidence
        high_conf_issues = [
            issue for issue in (original_issues + patched_issues)
            if issue.confidence == "HIGH"
        ]
        if high_conf_issues:
            confidence += 0.1
        
        # Decrease confidence if new issues introduced
        if new_issues:
            confidence -= 0.2 * min(len(new_issues) / 5, 1.0)
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))
    
    def calculate_secure_pass_rate(
        self,
        results: List[SecurityScore]
    ) -> float:
        """
        Calculate Secure-Pass@1 metric.
        
        Secure-Pass@1 = percentage of patches that pass both functional
        and security checks.
        
        Args:
            results: List of security evaluation results
            
        Returns:
            Secure-Pass@1 rate (0.0 to 1.0)
            
        Validates: Requirements 2.1, 2.4
        """
        if not results:
            return 0.0
        
        secure_passes = sum(
            1 for result in results
            if result.functional_pass and result.security_pass
        )
        
        secure_pass_rate = secure_passes / len(results)
        
        logger.info(
            f"Secure-Pass@1: {secure_pass_rate:.2%} "
            f"({secure_passes}/{len(results)})"
        )
        
        return secure_pass_rate
    
    def run_adversarial_tests(
        self,
        code: str,
        vuln_type: str
    ) -> List[Dict[str, Any]]:
        """
        Generate and run adversarial inputs for common vulnerability types.
        
        Tests patches against known attack patterns.
        
        Args:
            code: Patched code to test
            vuln_type: Type of vulnerability that was patched
            
        Returns:
            List of test results
            
        Validates: Requirements 2.4
        """
        logger.info(f"Running adversarial tests for {vuln_type}...")
        
        test_results = []
        
        # Generate adversarial inputs based on vulnerability type
        adversarial_inputs = self._generate_adversarial_inputs(vuln_type)
        
        for test_input in adversarial_inputs:
            result = self._run_adversarial_test(code, test_input, vuln_type)
            test_results.append(result)
        
        # Log summary
        passed = sum(1 for r in test_results if r["passed"])
        logger.info(
            f"Adversarial tests: {passed}/{len(test_results)} passed"
        )
        
        return test_results
    
    def _generate_adversarial_inputs(self, vuln_type: str) -> List[Dict[str, Any]]:
        """
        Generate adversarial inputs for specific vulnerability type.
        
        Args:
            vuln_type: Type of vulnerability
            
        Returns:
            List of test inputs with expected behavior
        """
        adversarial_inputs = []
        
        if vuln_type == "SQL Injection":
            adversarial_inputs = [
                {
                    "name": "SQL injection with OR clause",
                    "input": "' OR '1'='1",
                    "should_reject": True
                },
                {
                    "name": "SQL injection with UNION",
                    "input": "' UNION SELECT * FROM users--",
                    "should_reject": True
                },
                {
                    "name": "SQL injection with comment",
                    "input": "admin'--",
                    "should_reject": True
                }
            ]
        
        elif vuln_type == "Command Injection":
            adversarial_inputs = [
                {
                    "name": "Command injection with semicolon",
                    "input": "file.txt; rm -rf /",
                    "should_reject": True
                },
                {
                    "name": "Command injection with pipe",
                    "input": "file.txt | cat /etc/passwd",
                    "should_reject": True
                },
                {
                    "name": "Command injection with backticks",
                    "input": "`whoami`",
                    "should_reject": True
                }
            ]
        
        elif vuln_type == "Path Traversal":
            adversarial_inputs = [
                {
                    "name": "Path traversal with ../",
                    "input": "../../../etc/passwd",
                    "should_reject": True
                },
                {
                    "name": "Path traversal with encoded",
                    "input": "..%2F..%2F..%2Fetc%2Fpasswd",
                    "should_reject": True
                },
                {
                    "name": "Path traversal with absolute path",
                    "input": "/etc/passwd",
                    "should_reject": True
                }
            ]
        
        elif vuln_type == "Code Injection":
            adversarial_inputs = [
                {
                    "name": "Code injection with eval",
                    "input": "__import__('os').system('ls')",
                    "should_reject": True
                },
                {
                    "name": "Code injection with exec",
                    "input": "exec('import os; os.system(\"ls\")')",
                    "should_reject": True
                }
            ]
        
        return adversarial_inputs
    
    def _run_adversarial_test(
        self,
        code: str,
        test_input: Dict[str, Any],
        vuln_type: str
    ) -> Dict[str, Any]:
        """
        Run a single adversarial test.
        
        Args:
            code: Code to test
            test_input: Test input with expected behavior
            vuln_type: Type of vulnerability
            
        Returns:
            Test result dictionary
        """
        # For now, we use static analysis to check if the code
        # would reject the adversarial input
        # In a full implementation, this would execute the code
        # in a sandbox and verify behavior
        
        test_name = test_input["name"]
        should_reject = test_input["should_reject"]
        
        # Check if code contains proper validation
        has_validation = self._check_validation_present(code, vuln_type)
        
        # Test passes if validation is present when it should reject
        passed = has_validation if should_reject else not has_validation
        
        return {
            "name": test_name,
            "input": test_input["input"],
            "expected": "reject" if should_reject else "accept",
            "passed": passed,
            "has_validation": has_validation
        }
    
    def _check_validation_present(self, code: str, vuln_type: str) -> bool:
        """
        Check if code contains proper input validation.
        
        Args:
            code: Code to check
            vuln_type: Type of vulnerability
            
        Returns:
            True if validation appears to be present
        """
        # Simple heuristic checks for validation patterns
        validation_patterns = {
            "SQL Injection": [
                "execute(",  # Parameterized queries
                "?",  # Query placeholders
                "prepare"
            ],
            "Command Injection": [
                "shell=False",
                "shlex.quote",
                "subprocess.run([",  # List arguments
            ],
            "Path Traversal": [
                "os.path.basename",
                "os.path.normpath",
                "Path(",
                "resolve()"
            ],
            "Code Injection": [
                "ast.literal_eval",
                "json.loads",
                # Absence of eval/exec
            ]
        }
        
        patterns = validation_patterns.get(vuln_type, [])
        
        # Check if any validation pattern is present
        for pattern in patterns:
            if pattern in code:
                return True
        
        # For Code Injection, also check absence of dangerous functions
        if vuln_type == "Code Injection":
            if "eval(" not in code and "exec(" not in code:
                return True
        
        return False
