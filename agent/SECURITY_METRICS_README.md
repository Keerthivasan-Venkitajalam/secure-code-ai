# Security Metrics Module

The Security Metrics module provides comprehensive security evaluation for code patches, distinguishing between functional correctness and security correctness.

## Features

- **Bandit Integration**: Static security analysis for Python code
- **Semgrep Integration**: Advanced security pattern matching
- **Secure-Pass@1 Metric**: Measures patches that pass both functional and security checks
- **Adversarial Testing**: Tests patches against known attack patterns
- **Security Score**: Comprehensive evaluation with confidence scoring

## Installation

The required dependencies are already in `requirements.txt`:

```bash
pip install bandit>=1.7.5
pip install semgrep>=1.50.0
```

## Quick Start

```python
from agent.security_metrics import SecurityMetrics

# Initialize
metrics = SecurityMetrics()

# Evaluate a patch
score = metrics.evaluate_patch_security(
    original_code=vulnerable_code,
    patched_code=fixed_code,
    functional_pass=True
)

print(f"Security Pass: {score.security_pass}")
print(f"New Issues: {len(score.security_issues)}")
```

## Components

### SecurityMetrics

Main class that orchestrates security evaluation.

**Methods:**

- `evaluate_patch_security(original_code, patched_code, functional_pass)`: Evaluates if a patch introduces new vulnerabilities
- `calculate_secure_pass_rate(results)`: Calculates Secure-Pass@1 metric
- `run_adversarial_tests(code, vuln_type)`: Tests code against attack patterns

### BanditAnalyzer

Integrates Bandit static security analyzer.

**Methods:**

- `analyze(code, file_path)`: Runs Bandit analysis on code

**Detects:**
- SQL injection (B608)
- Command injection (B602, B605)
- Hardcoded passwords (B105, B106)
- Insecure cryptography (B301-B324)
- And more...

### SemgrepAnalyzer

Integrates Semgrep with security-focused rules.

**Methods:**

- `analyze(code, file_path, rules)`: Runs Semgrep analysis with specified rules

**Default Rule Sets:**
- `p/security-audit`: General security audit rules
- `p/owasp-top-ten`: OWASP Top 10 vulnerability patterns

### SecurityScore

Data model for security evaluation results.

**Fields:**
- `functional_pass`: Whether patch fixes the vulnerability
- `security_pass`: Whether patch avoids introducing new issues
- `security_issues`: List of SecurityIssue objects
- `confidence`: Confidence score (0.0 to 1.0)

**Methods:**
- `to_dict()`: Serializes to dictionary for JSON export

### SecurityIssue

Represents a security issue found by static analysis.

**Fields:**
- `tool`: Analyzer that found the issue ("bandit" or "semgrep")
- `severity`: Issue severity ("LOW", "MEDIUM", "HIGH", "CRITICAL")
- `issue_type`: Specific issue identifier (e.g., "B608")
- `message`: Human-readable description
- `line_number`: Line where issue was found
- `confidence`: Confidence level ("LOW", "MEDIUM", "HIGH")

## Usage Examples

### Example 1: Evaluate Patch Security

```python
from agent.security_metrics import SecurityMetrics

metrics = SecurityMetrics()

# Original vulnerable code
original = '''
def query_user(username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()
'''

# Patched secure code
patched = '''
def query_user(username):
    query = "SELECT * FROM users WHERE name = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
'''

# Evaluate
score = metrics.evaluate_patch_security(
    original_code=original,
    patched_code=patched,
    functional_pass=True
)

if score.security_pass:
    print("✓ Patch is secure")
else:
    print("✗ Patch introduces new issues:")
    for issue in score.security_issues:
        print(f"  - {issue.severity}: {issue.message}")
```

### Example 2: Calculate Secure-Pass@1

```python
from agent.security_metrics import SecurityMetrics, SecurityScore

metrics = SecurityMetrics()

# Collect evaluation results from multiple patches
results = []
for original, patched in patch_pairs:
    score = metrics.evaluate_patch_security(original, patched, True)
    results.append(score)

# Calculate Secure-Pass@1
secure_pass_rate = metrics.calculate_secure_pass_rate(results)
print(f"Secure-Pass@1: {secure_pass_rate:.1%}")
```

### Example 3: Run Adversarial Tests

```python
from agent.security_metrics import SecurityMetrics

metrics = SecurityMetrics()

# Test a patch against command injection attacks
results = metrics.run_adversarial_tests(
    code=patched_code,
    vuln_type="Command Injection"
)

passed = sum(1 for r in results if r["passed"])
print(f"Adversarial tests: {passed}/{len(results)} passed")

for result in results:
    if not result["passed"]:
        print(f"Failed: {result['name']}")
        print(f"  Input: {result['input']}")
```

## Integration with Patcher Agent

The Security Metrics module is integrated into the Patcher agent workflow:

```python
from agent.nodes.patcher import PatcherAgent
from agent.llm_client import LLMClient

# Initialize Patcher with security verification
patcher = PatcherAgent(llm_client=LLMClient())

# The Patcher automatically:
# 1. Generates a patch
# 2. Validates syntax
# 3. Runs security verification
# 4. Rejects patches that fail security checks
# 5. Logs security issues for analysis
```

## Secure-Pass@1 Metric

The Secure-Pass@1 metric extends the traditional Pass@1 metric by requiring patches to pass both functional and security checks.

**Formula:**
```
Secure-Pass@1 = (Patches passing functional AND security) / Total patches
```

**Comparison:**
- **Pass@1**: Measures functional correctness only
- **Secure-Pass@1**: Measures functional correctness AND security

**Example:**
```
5 patches generated:
- Patch 1: Functional ✓, Security ✓  → Counts toward Secure-Pass@1
- Patch 2: Functional ✓, Security ✗  → Does NOT count
- Patch 3: Functional ✗, Security ✓  → Does NOT count
- Patch 4: Functional ✓, Security ✓  → Counts toward Secure-Pass@1
- Patch 5: Functional ✓, Security ✓  → Counts toward Secure-Pass@1

Pass@1 = 4/5 = 80%
Secure-Pass@1 = 3/5 = 60%
```

## Adversarial Testing

The module includes adversarial test generators for common vulnerability types:

### SQL Injection
- `' OR '1'='1`
- `' UNION SELECT * FROM users--`
- `admin'--`

### Command Injection
- `file.txt; rm -rf /`
- `file.txt | cat /etc/passwd`
- `` `whoami` ``

### Path Traversal
- `../../../etc/passwd`
- `..%2F..%2F..%2Fetc%2Fpasswd`
- `/etc/passwd`

### Code Injection
- `__import__('os').system('ls')`
- `exec('import os; os.system("ls")')`

## Configuration

### Custom Semgrep Rules

```python
from agent.security_metrics import SemgrepAnalyzer

# Use custom rule sets
analyzer = SemgrepAnalyzer(rules=[
    "p/security-audit",
    "p/owasp-top-ten",
    "p/python"
])

issues = analyzer.analyze(code)
```

### Severity Filtering

```python
# Filter for HIGH and CRITICAL issues only
critical_issues = [
    issue for issue in score.security_issues
    if issue.severity in ["HIGH", "CRITICAL"]
]
```

## Testing

Run the test suite:

```bash
# Test security metrics module
pytest tests/test_security_metrics.py -v

# Test Patcher integration
pytest tests/test_patcher_security_integration.py -v
```

## Performance

- **Bandit**: ~1-2 seconds per analysis
- **Semgrep**: ~3-5 seconds per analysis (depends on rule sets)
- **Adversarial Tests**: ~0.1 seconds per test

**Optimization Tips:**
- Use fewer Semgrep rule sets for faster analysis
- Cache analysis results for unchanged code
- Run analyzers in parallel when evaluating multiple patches

## Limitations

1. **Static Analysis Only**: Cannot detect runtime vulnerabilities
2. **False Positives**: May flag secure code as vulnerable
3. **Language Support**: Currently Python only (Bandit/Semgrep support)
4. **Rule Coverage**: Limited to rules in Bandit/Semgrep databases

## Future Enhancements

- [ ] Support for more languages (JavaScript, Java, C++)
- [ ] Dynamic analysis integration
- [ ] Custom rule creation interface
- [ ] Machine learning-based false positive reduction
- [ ] Integration with CVE databases
- [ ] Automated fix suggestions

## Requirements Validation

This module validates the following requirements from the design document:

- **Requirement 2.1**: Secure-Pass@1 metric implementation ✓
- **Requirement 2.2**: Bandit and Semgrep integration ✓
- **Requirement 2.3**: Security verification in Patcher workflow ✓
- **Requirement 2.4**: Adversarial input testing ✓

## References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Database](https://cwe.mitre.org/)

## Support

For issues or questions:
1. Check the test files for usage examples
2. Run `python security_metrics_example.py` for demonstrations
3. Review the inline documentation in `security_metrics.py`
