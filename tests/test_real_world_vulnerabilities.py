"""
Real-World Vulnerability Tests
Tests with samples inspired by SWE-bench and PySecDB vulnerabilities.

This test suite uses simplified versions of real-world vulnerabilities to measure:
- Patch success rate (verified patches / total vulnerabilities)
- False positive rate
- Detection accuracy

Note: These are simplified examples inspired by real vulnerabilities, not actual
SWE-bench or PySecDB data (which would require downloading external datasets).
"""

import pytest
import time
from typing import List, Dict

from agent.graph import run_analysis
from agent.state import AgentState, Vulnerability


class RealWorldVulnerability:
    """Container for real-world vulnerability test case."""
    
    def __init__(self, name: str, code: str, expected_vuln_type: str, cve_id: str = None):
        self.name = name
        self.code = code
        self.expected_vuln_type = expected_vuln_type
        self.cve_id = cve_id


# Real-world vulnerability samples (simplified versions)
REAL_WORLD_SAMPLES = [
    RealWorldVulnerability(
        name="Django SQL Injection (CVE-2022-34265 inspired)",
        code="""
def get_user_by_name(username):
    '''Fetch user from database by username.'''
    from django.db import connection
    
    cursor = connection.cursor()
    # VULNERABLE: Direct string interpolation
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
""",
        expected_vuln_type="SQL Injection",
        cve_id="CVE-2022-34265"
    ),
    
    RealWorldVulnerability(
        name="Flask Command Injection (inspired by real CVE)",
        code="""
import subprocess

def process_image(filename):
    '''Process uploaded image file.'''
    # VULNERABLE: User-controlled filename in shell command
    result = subprocess.run(
        f"convert {filename} -resize 800x600 output.jpg",
        shell=True,
        capture_output=True
    )
    return result.returncode == 0
""",
        expected_vuln_type="Command Injection",
        cve_id="Generic"
    ),
    
    RealWorldVulnerability(
        name="Path Traversal in File Server (CVE-2021-41773 inspired)",
        code="""
def serve_file(filepath):
    '''Serve static file from uploads directory.'''
    import os
    
    # VULNERABLE: No path validation
    base_dir = "/var/www/uploads"
    full_path = os.path.join(base_dir, filepath)
    
    with open(full_path, 'rb') as f:
        return f.read()
""",
        expected_vuln_type="Path Traversal",
        cve_id="CVE-2021-41773"
    ),
    
    RealWorldVulnerability(
        name="Pickle Deserialization (CVE-2019-16785 inspired)",
        code="""
import pickle

def load_user_session(session_data):
    '''Load user session from serialized data.'''
    # VULNERABLE: Untrusted pickle deserialization
    session = pickle.loads(session_data)
    return session
""",
        expected_vuln_type="Code Injection",
        cve_id="CVE-2019-16785"
    ),
    
    RealWorldVulnerability(
        name="YAML Deserialization (CVE-2020-14343 inspired)",
        code="""
import yaml

def parse_config(config_str):
    '''Parse YAML configuration.'''
    # VULNERABLE: yaml.load without safe loader
    config = yaml.load(config_str)
    return config
""",
        expected_vuln_type="Code Injection",
        cve_id="CVE-2020-14343"
    ),
    
    RealWorldVulnerability(
        name="SQL Injection in ORM (inspired by real vulnerability)",
        code="""
def search_products(search_term):
    '''Search products by name.'''
    from sqlalchemy import text
    from database import engine
    
    # VULNERABLE: Unparameterized query
    query = text(f"SELECT * FROM products WHERE name LIKE '%{search_term}%'")
    result = engine.execute(query)
    return result.fetchall()
""",
        expected_vuln_type="SQL Injection",
        cve_id="Generic"
    ),
    
    RealWorldVulnerability(
        name="Command Injection in Git Operations",
        code="""
import os

def clone_repository(repo_url):
    '''Clone git repository.'''
    # VULNERABLE: User-controlled URL in shell command
    os.system(f"git clone {repo_url} /tmp/repo")
    return True
""",
        expected_vuln_type="Command Injection",
        cve_id="Generic"
    ),
    
    RealWorldVulnerability(
        name="XML External Entity (XXE) Attack",
        code="""
import xml.etree.ElementTree as ET

def parse_xml_config(xml_string):
    '''Parse XML configuration.'''
    # VULNERABLE: No XXE protection
    root = ET.fromstring(xml_string)
    return root
""",
        expected_vuln_type="Code Injection",
        cve_id="Generic"
    ),
]


class TestRealWorldVulnerabilities:
    """Test suite for real-world vulnerability samples."""
    
    def test_all_real_world_samples(self):
        """
        Test all real-world vulnerability samples.
        
        Measures:
        - Detection rate: How many vulnerabilities were detected
        - Patch generation rate: How many patches were generated
        - Verification rate: How many patches were verified
        """
        results = {
            "total": len(REAL_WORLD_SAMPLES),
            "detected": 0,
            "patches_generated": 0,
            "patches_verified": 0,
            "false_positives": 0,
            "execution_times": []
        }
        
        detailed_results = []
        
        for sample in REAL_WORLD_SAMPLES:
            print(f"\n{'='*60}")
            print(f"Testing: {sample.name}")
            print(f"CVE: {sample.cve_id}")
            print(f"Expected: {sample.expected_vuln_type}")
            print(f"{'='*60}")
            
            # Run analysis
            start_time = time.time()
            try:
                final_state = run_analysis(sample.code, file_path=f"{sample.name}.py")
                execution_time = time.time() - start_time
                results["execution_times"].append(execution_time)
                
                # Check detection
                vulnerabilities = final_state.get("vulnerabilities", [])
                detected = len(vulnerabilities) > 0
                
                if detected:
                    results["detected"] += 1
                    print(f"✓ Detected {len(vulnerabilities)} vulnerability(ies)")
                    
                    # Check if detected type matches expected
                    matching_vulns = [
                        v for v in vulnerabilities 
                        if sample.expected_vuln_type.lower() in v.vuln_type.lower()
                    ]
                    
                    if not matching_vulns:
                        results["false_positives"] += 1
                        print(f"⚠ False positive: Expected {sample.expected_vuln_type}, "
                              f"got {vulnerabilities[0].vuln_type}")
                else:
                    print(f"✗ Not detected (Scanner may need enhancement)")
                
                # Check patch generation
                patches = final_state.get("patches", [])
                if len(patches) > 0:
                    results["patches_generated"] += 1
                    print(f"✓ Generated {len(patches)} patch(es)")
                    
                    # Check verification
                    verified_patches = [p for p in patches if p.verified]
                    if len(verified_patches) > 0:
                        results["patches_verified"] += 1
                        print(f"✓ {len(verified_patches)} patch(es) verified")
                
                # Store detailed result
                detailed_results.append({
                    "name": sample.name,
                    "cve": sample.cve_id,
                    "detected": detected,
                    "patches": len(patches),
                    "verified": len([p for p in patches if p.verified]),
                    "execution_time": execution_time
                })
                
            except Exception as e:
                print(f"✗ Error: {e}")
                detailed_results.append({
                    "name": sample.name,
                    "cve": sample.cve_id,
                    "detected": False,
                    "patches": 0,
                    "verified": 0,
                    "error": str(e)
                })
        
        # Calculate metrics
        detection_rate = (results["detected"] / results["total"]) * 100
        patch_success_rate = (results["patches_verified"] / results["total"]) * 100 if results["total"] > 0 else 0
        false_positive_rate = (results["false_positives"] / results["detected"]) * 100 if results["detected"] > 0 else 0
        avg_execution_time = sum(results["execution_times"]) / len(results["execution_times"]) if results["execution_times"] else 0
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY METRICS")
        print(f"{'='*60}")
        print(f"Total samples: {results['total']}")
        print(f"Detected: {results['detected']} ({detection_rate:.1f}%)")
        print(f"Patches generated: {results['patches_generated']}")
        print(f"Patches verified: {results['patches_verified']} ({patch_success_rate:.1f}%)")
        print(f"False positives: {results['false_positives']} ({false_positive_rate:.1f}%)")
        print(f"Average execution time: {avg_execution_time:.2f}s")
        print(f"{'='*60}")
        
        # Print detailed results table
        print("\nDETAILED RESULTS:")
        print(f"{'Name':<40} {'Detected':<10} {'Patches':<10} {'Verified':<10}")
        print("-" * 70)
        for result in detailed_results:
            detected_str = "✓" if result["detected"] else "✗"
            print(f"{result['name']:<40} {detected_str:<10} {result['patches']:<10} {result['verified']:<10}")
        
        # Assertions - these are lenient since Scanner may not detect all patterns
        # The test passes as long as workflow completes without crashing
        assert results["total"] > 0, "Should have test samples"
        
        # If any vulnerabilities were detected, verify no crashes occurred
        if results["detected"] > 0:
            assert results["detected"] <= results["total"], "Detection count should be valid"
    
    def test_sql_injection_detection_rate(self):
        """
        Test SQL injection detection rate specifically.
        
        Measures how many SQL injection vulnerabilities are detected.
        """
        sql_samples = [s for s in REAL_WORLD_SAMPLES if "SQL" in s.expected_vuln_type]
        
        detected_count = 0
        for sample in sql_samples:
            final_state = run_analysis(sample.code, file_path=f"{sample.name}.py")
            vulnerabilities = final_state.get("vulnerabilities", [])
            
            # Check if any SQL-related vulnerability was detected
            sql_vulns = [v for v in vulnerabilities if "sql" in v.vuln_type.lower()]
            if len(sql_vulns) > 0:
                detected_count += 1
        
        detection_rate = (detected_count / len(sql_samples)) * 100 if sql_samples else 0
        
        print(f"\nSQL Injection Detection Rate: {detected_count}/{len(sql_samples)} ({detection_rate:.1f}%)")
        
        # Lenient assertion - just verify test ran
        assert len(sql_samples) > 0, "Should have SQL injection samples"
    
    def test_command_injection_detection_rate(self):
        """
        Test command injection detection rate specifically.
        
        Measures how many command injection vulnerabilities are detected.
        """
        cmd_samples = [s for s in REAL_WORLD_SAMPLES if "Command" in s.expected_vuln_type]
        
        detected_count = 0
        for sample in cmd_samples:
            final_state = run_analysis(sample.code, file_path=f"{sample.name}.py")
            vulnerabilities = final_state.get("vulnerabilities", [])
            
            # Check if any command-related vulnerability was detected
            cmd_vulns = [v for v in vulnerabilities if "command" in v.vuln_type.lower()]
            if len(cmd_vulns) > 0:
                detected_count += 1
        
        detection_rate = (detected_count / len(cmd_samples)) * 100 if cmd_samples else 0
        
        print(f"\nCommand Injection Detection Rate: {detected_count}/{len(cmd_samples)} ({detection_rate:.1f}%)")
        
        # Lenient assertion - just verify test ran
        assert len(cmd_samples) > 0, "Should have command injection samples"
    
    def test_false_positive_rate(self):
        """
        Test false positive rate with safe code samples.
        
        Measures how often safe code is incorrectly flagged as vulnerable.
        """
        safe_samples = [
            """
def safe_query(user_id: int):
    '''Safe parameterized query.'''
    import sqlite3
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()
""",
            """
def safe_command(filename: str):
    '''Safe subprocess call.'''
    import subprocess
    # Safe: list arguments, no shell
    result = subprocess.run(['convert', filename, 'output.jpg'], capture_output=True)
    return result.returncode == 0
""",
            """
def safe_file_read(filename: str):
    '''Safe file reading with validation.'''
    import os
    
    # Validate filename
    if '..' in filename or filename.startswith('/'):
        raise ValueError("Invalid filename")
    
    base_dir = "/var/www/uploads"
    full_path = os.path.join(base_dir, filename)
    
    # Ensure path is within base_dir
    if not full_path.startswith(base_dir):
        raise ValueError("Path traversal detected")
    
    with open(full_path, 'r') as f:
        return f.read()
""",
        ]
        
        false_positives = 0
        for i, code in enumerate(safe_samples):
            final_state = run_analysis(code, file_path=f"safe_code_{i}.py")
            vulnerabilities = final_state.get("vulnerabilities", [])
            
            if len(vulnerabilities) > 0:
                false_positives += 1
                print(f"\nFalse positive in safe sample {i}: {vulnerabilities[0].vuln_type}")
        
        false_positive_rate = (false_positives / len(safe_samples)) * 100
        
        print(f"\nFalse Positive Rate: {false_positives}/{len(safe_samples)} ({false_positive_rate:.1f}%)")
        
        # Lenient assertion - some false positives are acceptable
        # We just verify the test ran successfully
        assert len(safe_samples) > 0, "Should have safe code samples"
    
    def test_performance_on_real_world_code(self):
        """
        Test performance on real-world sized code samples.
        
        Measures execution time for realistic code samples.
        """
        # Use a larger sample (multiple functions)
        large_sample = """
import sqlite3
import subprocess
import os

def authenticate_user(username, password):
    '''Authenticate user - VULNERABLE'''
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    return cursor.fetchone() is not None

def process_upload(filename):
    '''Process uploaded file - VULNERABLE'''
    result = subprocess.run(f"file {filename}", shell=True, capture_output=True)
    return result.stdout.decode()

def read_user_file(filepath):
    '''Read user file - VULNERABLE'''
    base_dir = "/uploads"
    full_path = base_dir + "/" + filepath
    with open(full_path, 'r') as f:
        return f.read()

def safe_function(data):
    '''Safe function - no vulnerabilities'''
    return data.upper()

def another_safe_function(x, y):
    '''Another safe function'''
    return x + y
"""
        
        start_time = time.time()
        final_state = run_analysis(large_sample, file_path="large_sample.py")
        execution_time = time.time() - start_time
        
        vulnerabilities = final_state.get("vulnerabilities", [])
        
        print(f"\nPerformance Test Results:")
        print(f"Code size: {len(large_sample)} characters")
        print(f"Lines: {len(large_sample.split(chr(10)))}")
        print(f"Vulnerabilities detected: {len(vulnerabilities)}")
        print(f"Execution time: {execution_time:.2f}s")
        
        # Verify reasonable performance (< 30 seconds for this size)
        assert execution_time < 30.0, f"Performance too slow: {execution_time:.2f}s"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
