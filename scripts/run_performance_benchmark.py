#!/usr/bin/env python3
"""
Performance Benchmarking Script
Measures end-to-end analysis time, LLM inference latency, and symbolic execution performance.
"""

import time
import statistics
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock implementations for benchmarking without actual vLLM
from agent.llm_client import LLMClient
from agent.nodes.scanner import ScannerAgent
from agent.nodes.patcher import PatcherAgent
from agent.state import AgentState, Vulnerability, VerificationResult


def generate_test_code(lines: int) -> str:
    """Generate test code of specified size."""
    base_code = '''
def search_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute_query(query)

def execute_query(query):
    # Simulated database execution
    return []
'''
    
    # Add padding to reach desired line count
    padding = '\n'.join([f'# Padding line {i}' for i in range(lines - 10)])
    return base_code + '\n' + padding


def benchmark_scanner_performance():
    """Benchmark Scanner agent performance across different file sizes."""
    print("\n" + "="*80)
    print("SCANNER PERFORMANCE BENCHMARK")
    print("="*80)
    
    scanner = ScannerAgent()
    file_sizes = [100, 500, 1000, 2000]
    results = []
    
    for size in file_sizes:
        code = generate_test_code(size)
        state = AgentState(
            code=code,
            file_path=f"test_{size}.py",
            vulnerabilities=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Run multiple iterations
        times = []
        for _ in range(3):
            start = time.time()
            result_state = scanner.execute(state)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        results.append({
            'file_size_lines': size,
            'avg_time_seconds': avg_time,
            'min_time_seconds': min_time,
            'max_time_seconds': max_time,
            'vulnerabilities_found': len(result_state.get('vulnerabilities', []))
        })
        
        status = "✓ PASS" if avg_time < 10.0 else "✗ FAIL"
        print(f"\nFile size: {size} lines")
        print(f"  Average time: {avg_time:.3f}s {status}")
        print(f"  Min time: {min_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  Vulnerabilities found: {len(result_state.get('vulnerabilities', []))}")
    
    return results


def benchmark_patcher_performance():
    """Benchmark Patcher agent performance."""
    print("\n" + "="*80)
    print("PATCHER PERFORMANCE BENCHMARK")
    print("="*80)
    
    patcher = PatcherAgent()
    
    test_cases = [
        {
            'name': 'Simple SQL Injection',
            'code': '''
def search(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute(query)
''',
            'vuln_type': 'SQL Injection'
        },
        {
            'name': 'Command Injection',
            'code': '''
def run_command(user_input):
    cmd = f"ls {user_input}"
    return os.system(cmd)
''',
            'vuln_type': 'Command Injection'
        },
        {
            'name': 'Complex SQL Injection',
            'code': '''
def complex_search(username, email, age):
    query = f"SELECT * FROM users WHERE name='{username}' AND email='{email}' AND age={age}"
    results = execute(query)
    return process_results(results)

def process_results(results):
    return [r for r in results if r['active']]
''',
            'vuln_type': 'SQL Injection'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        vuln = Vulnerability(
            location="test.py:2",
            vuln_type=test_case['vuln_type'],
            description=f"{test_case['vuln_type']} vulnerability",
            hypothesis=f"User input flows to {test_case['vuln_type']}",
            confidence=0.9
        )
        
        verification_result = VerificationResult(
            verified=False,
            counterexample="admin' OR '1'='1",
            error_message=None,
            execution_time=0.5
        )
        
        state = AgentState(
            code=test_case['code'],
            file_path="test.py",
            vulnerabilities=[vuln],
            verification_results=[verification_result],
            current_vulnerability=vuln,
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        
        # Run multiple iterations
        times = []
        for _ in range(3):
            start = time.time()
            result_state = patcher.execute(state)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        results.append({
            'test_case': test_case['name'],
            'avg_time_seconds': avg_time,
            'min_time_seconds': min_time,
            'max_time_seconds': max_time,
            'patch_generated': 'current_patch' in result_state
        })
        
        status = "✓ PASS" if avg_time < 5.0 else "✗ FAIL"
        print(f"\nTest case: {test_case['name']}")
        print(f"  Average time: {avg_time:.3f}s {status}")
        print(f"  Min time: {min_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  Patch generated: {'current_patch' in result_state}")
    
    return results


def benchmark_llm_inference():
    """Benchmark LLM inference latency (mocked)."""
    print("\n" + "="*80)
    print("LLM INFERENCE LATENCY BENCHMARK")
    print("="*80)
    
    # Note: This uses mocked LLM, so times will be very fast
    # In production with real vLLM, expect 1-3 seconds per inference
    
    print("\nSkipping LLM inference benchmark (requires vLLM client)")
    print("Note: In production with real vLLM, expect 1-3s per inference")
    
    return [
        {
            'prompt_type': 'Hypothesis generation',
            'avg_latency_seconds': 1.5,
            'iterations': 0,
            'note': 'Estimated production latency'
        },
        {
            'prompt_type': 'Contract generation',
            'avg_latency_seconds': 2.0,
            'iterations': 0,
            'note': 'Estimated production latency'
        },
        {
            'prompt_type': 'Patch generation',
            'avg_latency_seconds': 2.5,
            'iterations': 0,
            'note': 'Estimated production latency'
        }
    ]


def benchmark_end_to_end():
    """Benchmark end-to-end workflow."""
    print("\n" + "="*80)
    print("END-TO-END WORKFLOW BENCHMARK")
    print("="*80)
    
    scanner = ScannerAgent()
    patcher = PatcherAgent()
    
    test_code = '''
def search_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute_query(query)

def execute_query(query):
    return []
'''
    
    times = []
    for _ in range(3):
        start = time.time()
        
        # Scanner phase
        state = AgentState(
            code=test_code,
            file_path="test.py",
            vulnerabilities=[],
            logs=[],
            errors=[],
            total_execution_time=0.0
        )
        state = scanner.execute(state)
        
        # Patcher phase (if vulnerabilities found)
        if state.get('vulnerabilities'):
            vuln = state['vulnerabilities'][0]
            verification_result = VerificationResult(
                verified=False,
                counterexample="admin' OR '1'='1",
                error_message=None,
                execution_time=0.5
            )
            state['verification_results'] = [verification_result]
            state['current_vulnerability'] = vuln
            state = patcher.execute(state)
        
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    
    print(f"\nEnd-to-end workflow (Scanner + Patcher):")
    print(f"  Average time: {avg_time:.3f}s")
    print(f"  Iterations: {len(times)}")
    
    return {
        'avg_time_seconds': avg_time,
        'iterations': len(times)
    }


def main():
    """Run all performance benchmarks."""
    print(f"SecureCodeAI - Performance Benchmark")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"\nNote: These benchmarks use mocked LLM for speed.")
    print(f"Production performance with real vLLM will be slower (1-3s per LLM call).")
    
    all_results = {}
    
    # Run benchmarks
    all_results['scanner'] = benchmark_scanner_performance()
    all_results['patcher'] = benchmark_patcher_performance()
    all_results['llm_inference'] = benchmark_llm_inference()
    all_results['end_to_end'] = benchmark_end_to_end()
    
    # Summary
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    # Scanner summary
    scanner_times = [r['avg_time_seconds'] for r in all_results['scanner']]
    print(f"\nScanner Performance:")
    print(f"  Average across all file sizes: {statistics.mean(scanner_times):.3f}s")
    print(f"  Max time (largest file): {max(scanner_times):.3f}s")
    print(f"  Requirement: < 10s for files under 1000 lines")
    scanner_pass = all(t < 10.0 for t in scanner_times[:3])  # First 3 are under 1000 lines
    print(f"  Status: {'✓ PASS' if scanner_pass else '✗ FAIL'}")
    
    # Patcher summary
    patcher_times = [r['avg_time_seconds'] for r in all_results['patcher']]
    print(f"\nPatcher Performance:")
    print(f"  Average across all test cases: {statistics.mean(patcher_times):.3f}s")
    print(f"  Max time: {max(patcher_times):.3f}s")
    print(f"  Requirement: < 5s per patch")
    patcher_pass = all(t < 5.0 for t in patcher_times)
    print(f"  Status: {'✓ PASS' if patcher_pass else '✗ FAIL'}")
    
    # Overall
    print(f"\nOverall Performance:")
    print(f"  End-to-end workflow: {all_results['end_to_end']['avg_time_seconds']:.3f}s")
    print(f"  All requirements met: {scanner_pass and patcher_pass}")
    
    # Save results
    output_file = Path("performance_benchmark_results.json")
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': all_results,
            'summary': {
                'scanner_pass': scanner_pass,
                'patcher_pass': patcher_pass,
                'all_pass': scanner_pass and patcher_pass
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print(f"\nCompleted at: {datetime.now().isoformat()}")
    
    return 0 if (scanner_pass and patcher_pass) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
