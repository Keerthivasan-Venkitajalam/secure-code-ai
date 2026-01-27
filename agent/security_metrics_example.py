"""
Example usage of Security Metrics Module

This script demonstrates how to use the security metrics system to:
1. Evaluate patch security
2. Calculate Secure-Pass@1 metric
3. Run adversarial tests
"""

from security_metrics import (
    SecurityMetrics,
    SecurityScore,
    SecurityIssue
)


def example_patch_evaluation():
    """Example: Evaluate a security patch."""
    print("=" * 60)
    print("Example 1: Patch Security Evaluation")
    print("=" * 60)
    
    metrics = SecurityMetrics()
    
    # Original vulnerable code (SQL injection)
    original_code = '''
def login(username, password):
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    cursor.execute(query)
    return cursor.fetchone()
'''
    
    # Patched secure code (parameterized queries)
    patched_code = '''
def login(username, password):
    query = "SELECT * FROM users WHERE name=? AND pass=?"
    cursor.execute(query, (username, password))
    return cursor.fetchone()
'''
    
    print("\nOriginal Code:")
    print(original_code)
    print("\nPatched Code:")
    print(patched_code)
    
    # Evaluate the patch
    score = metrics.evaluate_patch_security(
        original_code=original_code,
        patched_code=patched_code,
        functional_pass=True
    )
    
    print("\nEvaluation Results:")
    print(f"  Functional Pass: {score.functional_pass}")
    print(f"  Security Pass: {score.security_pass}")
    print(f"  New Issues: {len(score.security_issues)}")
    print(f"  Confidence: {score.confidence:.2f}")
    
    if score.security_issues:
        print("\n  Security Issues Found:")
        for issue in score.security_issues:
            print(f"    - [{issue.severity}] {issue.tool}: {issue.issue_type}")
            print(f"      {issue.message}")


def example_secure_pass_rate():
    """Example: Calculate Secure-Pass@1 metric."""
    print("\n" + "=" * 60)
    print("Example 2: Secure-Pass@1 Metric Calculation")
    print("=" * 60)
    
    metrics = SecurityMetrics()
    
    # Simulate evaluation results from multiple patches
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
        ),
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
            confidence=0.95
        )
    ]
    
    print(f"\nEvaluating {len(results)} patches...")
    
    # Calculate Secure-Pass@1
    secure_pass_rate = metrics.calculate_secure_pass_rate(results)
    
    # Calculate regular Pass@1 (functional only)
    functional_pass_rate = sum(
        1 for r in results if r.functional_pass
    ) / len(results)
    
    print(f"\nResults:")
    print(f"  Pass@1 (functional): {functional_pass_rate:.1%}")
    print(f"  Secure-Pass@1: {secure_pass_rate:.1%}")
    print(f"\n  Difference: {(functional_pass_rate - secure_pass_rate):.1%}")
    print(f"  (Shows patches that pass functionally but fail security)")


def example_adversarial_testing():
    """Example: Run adversarial tests."""
    print("\n" + "=" * 60)
    print("Example 3: Adversarial Testing")
    print("=" * 60)
    
    metrics = SecurityMetrics()
    
    # Secure code with proper validation
    secure_code = '''
import subprocess

def run_command(filename):
    # Use list arguments to prevent command injection
    subprocess.run(["cat", filename], shell=False)
'''
    
    print("\nCode to Test:")
    print(secure_code)
    
    # Run adversarial tests for command injection
    print("\nRunning adversarial tests for Command Injection...")
    results = metrics.run_adversarial_tests(
        code=secure_code,
        vuln_type="Command Injection"
    )
    
    print(f"\nTest Results ({len(results)} tests):")
    for result in results:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"  {status} - {result['name']}")
        print(f"         Input: {result['input']}")
        print(f"         Expected: {result['expected']}")


def example_bad_patch():
    """Example: Patch that introduces new vulnerability."""
    print("\n" + "=" * 60)
    print("Example 4: Detecting Bad Patches")
    print("=" * 60)
    
    metrics = SecurityMetrics()
    
    # Original code (simple, no major issues)
    original_code = '''
def process_data(data):
    return data.strip().upper()
'''
    
    # Bad patch that introduces command injection
    bad_patch = '''
import subprocess

def process_data(data):
    # BAD: Introduces command injection vulnerability
    subprocess.run(f"echo {data}", shell=True)
    return data.strip().upper()
'''
    
    print("\nOriginal Code:")
    print(original_code)
    print("\nBad Patch (introduces vulnerability):")
    print(bad_patch)
    
    # Evaluate the bad patch
    score = metrics.evaluate_patch_security(
        original_code=original_code,
        patched_code=bad_patch,
        functional_pass=True
    )
    
    print("\nEvaluation Results:")
    print(f"  Functional Pass: {score.functional_pass}")
    print(f"  Security Pass: {score.security_pass}")
    print(f"  New Issues: {len(score.security_issues)}")
    
    if not score.security_pass:
        print("\n  ⚠️  PATCH REJECTED - Introduces new security issues:")
        for issue in score.security_issues:
            print(f"    - [{issue.severity}] {issue.tool}: {issue.issue_type}")
            print(f"      {issue.message}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Security Metrics Module - Usage Examples")
    print("=" * 60)
    
    # Run examples
    example_patch_evaluation()
    example_secure_pass_rate()
    example_adversarial_testing()
    example_bad_patch()
    
    print("\n" + "=" * 60)
    print("Examples Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
