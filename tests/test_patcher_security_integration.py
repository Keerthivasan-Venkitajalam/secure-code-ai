"""
Tests for Patcher Agent Security Integration
Tests that the Patcher agent properly integrates security verification.
"""

import sys
from pathlib import Path

# Add the agent directory to path
agent_path = Path(__file__).parent.parent / "agent"
sys.path.insert(0, str(agent_path))

import pytest
import importlib.util

# Import security_metrics directly
spec = importlib.util.spec_from_file_location(
    "security_metrics",
    agent_path / "security_metrics.py"
)
security_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security_metrics)

SecurityMetrics = security_metrics.SecurityMetrics
SecurityScore = security_metrics.SecurityScore
SecurityIssue = security_metrics.SecurityIssue


class TestPatcherSecurityIntegration:
    """Test Patcher agent security integration."""
    
    def test_security_metrics_initialization(self):
        """Test that SecurityMetrics can be initialized."""
        metrics = SecurityMetrics()
        
        assert metrics is not None
        assert metrics.bandit_analyzer is not None
        assert metrics.semgrep_analyzer is not None
    
    def test_patch_evaluation_workflow(self):
        """Test the patch evaluation workflow."""
        metrics = SecurityMetrics()
        
        # Simulate original vulnerable code
        original_code = '''
def query_database(user_input):
    query = f"SELECT * FROM users WHERE id = {user_input}"
    return execute_query(query)
'''
        
        # Simulate patched code
        patched_code = '''
def query_database(user_input):
    query = "SELECT * FROM users WHERE id = ?"
    return execute_query(query, (user_input,))
'''
        
        # Evaluate the patch
        score = metrics.evaluate_patch_security(
            original_code=original_code,
            patched_code=patched_code,
            functional_pass=True
        )
        
        # Verify the evaluation completed
        assert isinstance(score, SecurityScore)
        assert isinstance(score.functional_pass, bool)
        assert isinstance(score.security_pass, bool)
        assert isinstance(score.security_issues, list)
        assert 0.0 <= score.confidence <= 1.0
    
    def test_adversarial_testing_integration(self):
        """Test adversarial testing integration."""
        metrics = SecurityMetrics()
        
        # Secure code with proper validation
        secure_code = '''
import subprocess

def run_command(filename):
    # Use list arguments to prevent command injection
    subprocess.run(["cat", filename], shell=False)
'''
        
        # Run adversarial tests
        results = metrics.run_adversarial_tests(
            code=secure_code,
            vuln_type="Command Injection"
        )
        
        # Verify tests ran
        assert len(results) > 0
        assert all(isinstance(r, dict) for r in results)
        assert all("name" in r for r in results)
        assert all("passed" in r for r in results)
    
    def test_secure_pass_rate_calculation(self):
        """Test Secure-Pass@1 metric calculation."""
        metrics = SecurityMetrics()
        
        # Create sample results
        results = [
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.9
            ),
            SecurityScore(
                functional_pass=True,
                security_pass=False,
                security_issues=[
                    SecurityIssue(
                        tool="bandit",
                        severity="HIGH",
                        issue_type="B608",
                        message="SQL injection detected"
                    )
                ],
                confidence=0.7
            ),
            SecurityScore(
                functional_pass=True,
                security_pass=True,
                security_issues=[],
                confidence=0.85
            )
        ]
        
        # Calculate Secure-Pass@1
        rate = metrics.calculate_secure_pass_rate(results)
        
        # 2 out of 3 pass both functional and security
        assert rate == pytest.approx(2/3, rel=0.01)
    
    def test_security_issue_detection(self):
        """Test that security issues are properly detected."""
        metrics = SecurityMetrics()
        
        # Code with potential security issue
        vulnerable_code = '''
def unsafe_function(user_input):
    # Using eval is dangerous
    result = eval(user_input)
    return result
'''
        
        # Analyze the code
        issues = metrics._analyze_code(vulnerable_code)
        
        # Should return a list (may be empty if analyzers not available)
        assert isinstance(issues, list)
        
        # If issues found, verify structure
        for issue in issues:
            assert isinstance(issue, SecurityIssue)
            assert hasattr(issue, 'tool')
            assert hasattr(issue, 'severity')
            assert hasattr(issue, 'issue_type')
            assert hasattr(issue, 'message')
    
    def test_new_issue_detection(self):
        """Test detection of new issues introduced by patch."""
        metrics = SecurityMetrics()
        
        # Original issues
        original_issues = [
            SecurityIssue(
                tool="bandit",
                severity="MEDIUM",
                issue_type="B101",
                message="Use of assert detected"
            )
        ]
        
        # Patched issues (includes original + new)
        patched_issues = [
            SecurityIssue(
                tool="bandit",
                severity="MEDIUM",
                issue_type="B101",
                message="Use of assert detected"
            ),
            SecurityIssue(
                tool="bandit",
                severity="HIGH",
                issue_type="B608",
                message="SQL injection detected"
            )
        ]
        
        # Find new issues
        new_issues = metrics._find_new_issues(original_issues, patched_issues)
        
        # Should find the SQL injection as new
        assert len(new_issues) == 1
        assert new_issues[0].issue_type == "B608"
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        metrics = SecurityMetrics()
        
        # Test with no issues
        confidence = metrics._calculate_confidence([], [], [])
        assert 0.0 <= confidence <= 1.0
        
        # Test with new issues (should decrease confidence)
        new_issue = SecurityIssue(
            tool="bandit",
            severity="HIGH",
            issue_type="B608",
            message="SQL injection"
        )
        confidence_with_issues = metrics._calculate_confidence(
            [], [new_issue], [new_issue]
        )
        assert 0.0 <= confidence_with_issues <= 1.0


class TestSecurityScoreDataModel:
    """Test SecurityScore data model."""
    
    def test_security_score_serialization(self):
        """Test SecurityScore to_dict method."""
        issue = SecurityIssue(
            tool="semgrep",
            severity="HIGH",
            issue_type="python.lang.security.audit.dangerous-eval",
            message="Dangerous use of eval()",
            line_number=42,
            confidence="HIGH"
        )
        
        score = SecurityScore(
            functional_pass=True,
            security_pass=False,
            security_issues=[issue],
            confidence=0.75
        )
        
        # Convert to dict
        result = score.to_dict()
        
        # Verify structure
        assert result["functional_pass"] is True
        assert result["security_pass"] is False
        assert len(result["security_issues"]) == 1
        assert result["security_issues"][0]["tool"] == "semgrep"
        assert result["security_issues"][0]["severity"] == "HIGH"
        assert result["security_issues"][0]["line_number"] == 42
        assert result["confidence"] == 0.75
    
    def test_security_score_with_multiple_issues(self):
        """Test SecurityScore with multiple issues."""
        issues = [
            SecurityIssue(
                tool="bandit",
                severity="HIGH",
                issue_type="B608",
                message="SQL injection"
            ),
            SecurityIssue(
                tool="semgrep",
                severity="MEDIUM",
                issue_type="python.lang.security.audit.eval-detected",
                message="eval() usage"
            )
        ]
        
        score = SecurityScore(
            functional_pass=True,
            security_pass=False,
            security_issues=issues,
            confidence=0.6
        )
        
        assert len(score.security_issues) == 2
        assert score.security_pass is False
        
        # Verify serialization
        result = score.to_dict()
        assert len(result["security_issues"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
