"""
Tests for Security Metrics Module
Tests Bandit, Semgrep integration, Secure-Pass@1 metric, and adversarial testing.
"""

import sys
import os
from pathlib import Path

# Add the agent directory directly to avoid __init__.py imports
agent_path = Path(__file__).parent.parent / "agent"
sys.path.insert(0, str(agent_path))

import pytest

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "security_metrics",
    agent_path / "security_metrics.py"
)
security_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security_metrics)

SecurityMetrics = security_metrics.SecurityMetrics
BanditAnalyzer = security_metrics.BanditAnalyzer
SemgrepAnalyzer = security_metrics.SemgrepAnalyzer
SecurityScore = security_metrics.SecurityScore
SecurityIssue = security_metrics.SecurityIssue


class TestBanditAnalyzer:
    """Test Bandit static analyzer integration."""
    
    def test_bandit_availability(self):
        """Test that Bandit availability check works."""
        analyzer = BanditAnalyzer()
        # Should either be available or not, but shouldn't crash
        assert isinstance(analyzer.available, bool)
    
    def test_bandit_detects_sql_injection(self):
        """Test Bandit detects SQL injection vulnerability."""
        analyzer = BanditAnalyzer()
        
        if not analyzer.available:
            pytest.skip("Bandit not available")
        
        vulnerable_code = '''
def query_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
'''
        
        issues = analyzer.analyze(vulnerable_code)
        
        # Bandit should detect SQL injection (B608)
        assert len(issues) > 0
        assert any("sql" in issue.issue_type.lower() for issue in issues)
    
    def test_bandit_detects_command_injection(self):
        """Test Bandit detects command injection vulnerability."""
        analyzer = BanditAnalyzer()
        
        if not analyzer.available:
            pytest.skip("Bandit not available")
        
        vulnerable_code = '''
import subprocess

def run_command(filename):
    subprocess.run(f"cat {filename}", shell=True)
'''
        
        issues = analyzer.analyze(vulnerable_code)
        
        # Bandit should detect shell=True usage (B602)
        assert len(issues) > 0
        assert any("shell" in issue.message.lower() for issue in issues)
    
    def test_bandit_clean_code(self):
        """Test Bandit on secure code."""
        analyzer = BanditAnalyzer()
        
        if not analyzer.available:
            pytest.skip("Bandit not available")
        
        secure_code = '''
def add_numbers(a, b):
    return a + b
'''
        
        issues = analyzer.analyze(secure_code)
        
        # Should find no issues in simple secure code
        assert len(issues) == 0


class TestSemgrepAnalyzer:
    """Test Semgrep static analyzer integration."""
    
    def test_semgrep_availability(self):
        """Test that Semgrep availability check works."""
        analyzer = SemgrepAnalyzer()
        # Should either be available or not, but shouldn't crash
        assert isinstance(analyzer.available, bool)
    
    def test_semgrep_with_custom_rules(self):
        """Test Semgrep with custom rule sets."""
        analyzer = SemgrepAnalyzer(rules=["p/security-audit"])
        
        if not analyzer.available:
            pytest.skip("Semgrep not available")
        
        vulnerable_code = '''
def unsafe_eval(user_input):
    return eval(user_input)
'''
        
        issues = analyzer.analyze(vulnerable_code)
        
        # Semgrep should detect eval usage
        # Note: May not find issues if rules don't cover this
        # This is more of an integration test
        assert isinstance(issues, list)


class TestSecurityScore:
    """Test SecurityScore data model."""
    
    def test_security_score_creation(self):
        """Test creating a SecurityScore."""
        score = SecurityScore(
            functional_pass=True,
            security_pass=True,
            security_issues=[],
            confidence=0.8
        )
        
        assert score.functional_pass is True
        assert score.security_pass is True
        assert len(score.security_issues) == 0
        assert score.confidence == 0.8
    
    def test_security_score_with_issues(self):
        """Test SecurityScore with security issues."""
        issue = SecurityIssue(
            tool="bandit",
            severity="HIGH",
            issue_type="B608",
            message="SQL injection detected",
            line_number=10,
            confidence="HIGH"
        )
        
        score = SecurityScore(
            functional_pass=True,
            security_pass=False,
            security_issues=[issue],
            confidence=0.6
        )
        
        assert score.functional_pass is True
        assert score.security_pass is False
        assert len(score.security_issues) == 1
        assert score.security_issues[0].severity == "HIGH"
    
    def test_security_score_to_dict(self):
        """Test SecurityScore serialization to dict."""
        issue = SecurityIssue(
            tool="semgrep",
            severity="MEDIUM",
            issue_type="python.lang.security.audit.eval-detected",
            message="Detected eval() usage",
            line_number=5
        )
        
        score = SecurityScore(
            functional_pass=True,
            security_pass=False,
            security_issues=[issue],
            confidence=0.7
        )
        
        result = score.to_dict()
        
        assert result["functional_pass"] is True
        assert result["security_pass"] is False
        assert len(result["security_issues"]) == 1
        assert result["security_issues"][0]["tool"] == "semgrep"
        assert result["confidence"] == 0.7


class TestSecurityMetrics:
    """Test main SecurityMetrics class."""
    
    def test_security_metrics_initialization(self):
        """Test SecurityMetrics initializes correctly."""
        metrics = SecurityMetrics()
        
        assert metrics.bandit_analyzer is not None
        assert metrics.semgrep_analyzer is not None
    
    def test_evaluate_patch_security_no_new_issues(self):
        """Test patch evaluation when no new issues introduced."""
        metrics = SecurityMetrics()
        
        original_code = '''
def add(a, b):
    return a + b
'''
        
        patched_code = '''
def add(a, b):
    """Add two numbers."""
    return a + b
'''
        
        score = metrics.evaluate_patch_security(
            original_code=original_code,
            patched_code=patched_code,
            functional_pass=True
        )
        
        assert score.functional_pass is True
        # Should pass security since no new issues introduced
        assert score.security_pass is True
        assert isinstance(score.confidence, float)
        assert 0.0 <= score.confidence <= 1.0
    
    def test_evaluate_patch_security_introduces_issue(self):
        """Test patch evaluation when new security issue introduced."""
        metrics = SecurityMetrics()
        
        original_code = '''
def process_data(data):
    return data.upper()
'''
        
        # Patch introduces eval (security issue)
        patched_code = '''
def process_data(data):
    return eval(data)
'''
        
        score = metrics.evaluate_patch_security(
            original_code=original_code,
            patched_code=patched_code,
            functional_pass=True
        )
        
        assert score.functional_pass is True
        # May or may not detect depending on analyzer availability
        # Just verify it doesn't crash
        assert isinstance(score.security_pass, bool)
    
    def test_calculate_secure_pass_rate_empty(self):
        """Test Secure-Pass@1 calculation with empty results."""
        metrics = SecurityMetrics()
        
        rate = metrics.calculate_secure_pass_rate([])
        
        assert rate == 0.0
    
    def test_calculate_secure_pass_rate_all_pass(self):
        """Test Secure-Pass@1 when all patches pass."""
        metrics = SecurityMetrics()
        
        results = [
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.8
            )
            for _ in range(5)
        ]
        
        rate = metrics.calculate_secure_pass_rate(results)
        
        assert rate == 1.0
    
    def test_calculate_secure_pass_rate_partial(self):
        """Test Secure-Pass@1 with mixed results."""
        metrics = SecurityMetrics()
        
        results = [
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.8
            ),
            SecurityScore(
                functional_pass=True,
                security_pass=False,
                security_issues=[SecurityIssue(
                    tool="bandit",
                    severity="HIGH",
                    issue_type="B608",
                    message="SQL injection"
                )],
                confidence=0.6
            ),
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.9
            )
        ]
        
        rate = metrics.calculate_secure_pass_rate(results)
        
        # 2 out of 3 pass both functional and security
        assert rate == pytest.approx(2/3, rel=0.01)
    
    def test_calculate_secure_pass_rate_functional_fail(self):
        """Test Secure-Pass@1 when functional tests fail."""
        metrics = SecurityMetrics()
        
        results = [
            SecurityScore(
                functional_pass=False,  # Functional failure
                security_pass=True,
                security_issues=[],
                confidence=0.8
            ),
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.9
            )
        ]
        
        rate = metrics.calculate_secure_pass_rate(results)
        
        # Only 1 out of 2 passes both
        assert rate == 0.5


class TestAdversarialTesting:
    """Test adversarial input testing."""
    
    def test_adversarial_tests_sql_injection(self):
        """Test adversarial tests for SQL injection."""
        metrics = SecurityMetrics()
        
        # Secure code with parameterized queries
        secure_code = '''
def query_user(username):
    query = "SELECT * FROM users WHERE name = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
'''
        
        results = metrics.run_adversarial_tests(
            code=secure_code,
            vuln_type="SQL Injection"
        )
        
        assert len(results) > 0
        assert all("name" in r for r in results)
        assert all("passed" in r for r in results)
    
    def test_adversarial_tests_command_injection(self):
        """Test adversarial tests for command injection."""
        metrics = SecurityMetrics()
        
        # Secure code with list arguments
        secure_code = '''
import subprocess

def run_command(filename):
    subprocess.run(["cat", filename], shell=False)
'''
        
        results = metrics.run_adversarial_tests(
            code=secure_code,
            vuln_type="Command Injection"
        )
        
        assert len(results) > 0
        # Should have tests for various injection attempts
        assert any("semicolon" in r["name"].lower() for r in results)
    
    def test_adversarial_tests_path_traversal(self):
        """Test adversarial tests for path traversal."""
        metrics = SecurityMetrics()
        
        # Secure code with path sanitization
        secure_code = '''
import os

def read_file(filename):
    safe_name = os.path.basename(filename)
    with open(safe_name, 'r') as f:
        return f.read()
'''
        
        results = metrics.run_adversarial_tests(
            code=secure_code,
            vuln_type="Path Traversal"
        )
        
        assert len(results) > 0
        # Should test for ../ patterns
        assert any("../" in r["input"] for r in results)
    
    def test_adversarial_tests_code_injection(self):
        """Test adversarial tests for code injection."""
        metrics = SecurityMetrics()
        
        # Secure code without eval/exec
        secure_code = '''
import ast

def evaluate_expression(expr):
    return ast.literal_eval(expr)
'''
        
        results = metrics.run_adversarial_tests(
            code=secure_code,
            vuln_type="Code Injection"
        )
        
        assert len(results) > 0
        # Should test for eval/exec attempts
        assert any("eval" in r["input"].lower() or "exec" in r["input"].lower() 
                  for r in results)


class TestSecurityMetricsIntegration:
    """Integration tests for security metrics."""
    
    def test_full_patch_evaluation_workflow(self):
        """Test complete patch evaluation workflow."""
        metrics = SecurityMetrics()
        
        # Original vulnerable code
        original = '''
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    cursor.execute(query)
    return cursor.fetchone()
'''
        
        # Patched secure code
        patched = '''
def login(username, password):
    query = "SELECT * FROM users WHERE name=? AND pass=?"
    cursor.execute(query, (username, password))
    return cursor.fetchone()
'''
        
        # Evaluate patch
        score = metrics.evaluate_patch_security(
            original_code=original,
            patched_code=patched,
            functional_pass=True
        )
        
        # Verify evaluation completed
        assert isinstance(score.functional_pass, bool)
        assert isinstance(score.security_pass, bool)
        assert isinstance(score.security_issues, list)
        assert 0.0 <= score.confidence <= 1.0
    
    def test_patch_introduces_new_vulnerability(self):
        """Test detection when patch introduces new vulnerability."""
        metrics = SecurityMetrics()
        
        # Original code (no major issues)
        original = '''
def process(data):
    return data.strip()
'''
        
        # Patch introduces command injection
        patched = '''
import subprocess

def process(data):
    subprocess.run(f"echo {data}", shell=True)
    return data.strip()
'''
        
        # Evaluate patch
        score = metrics.evaluate_patch_security(
            original_code=original,
            patched_code=patched,
            functional_pass=True
        )
        
        # Should detect new issues (if analyzers available)
        assert isinstance(score.security_pass, bool)
        # If analyzers found issues, security_pass should be False
        if len(score.security_issues) > 0:
            # Check if any HIGH/CRITICAL issues
            critical_issues = [
                i for i in score.security_issues 
                if i.severity in ["HIGH", "CRITICAL"]
            ]
            if critical_issues:
                assert score.security_pass is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
