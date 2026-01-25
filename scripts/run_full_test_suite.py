#!/usr/bin/env python3
"""
Full Test Suite Runner
Runs all tests and generates a comprehensive report.
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}\n")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result


def main():
    """Run full test suite."""
    project_root = Path(__file__).parent.parent
    
    print(f"SecureCodeAI - Full Test Suite")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Project root: {project_root}")
    
    results = {}
    
    # 1. Run all unit tests (excluding Docker integration and load tests)
    print("\n" + "="*80)
    print("RUNNING UNIT TESTS")
    print("="*80)
    
    unit_test_cmd = (
        "python -m pytest secure-code-ai/tests/ "
        "-v "
        "--ignore=secure-code-ai/tests/test_docker_integration.py "
        "--ignore=secure-code-ai/tests/test_docker_compose_config.py "
        "--ignore=secure-code-ai/tests/load_test.py "
        "--ignore=secure-code-ai/tests/test_e2e_workflow.py "
        "--ignore=secure-code-ai/tests/test_real_world_vulnerabilities.py "
        "--ignore=secure-code-ai/tests/test_self_correction_e2e.py "
        "--ignore=secure-code-ai/tests/test_neuro_slicing_effectiveness.py "
        "--ignore=secure-code-ai/tests/test_scanner_performance.py "
        "--ignore=secure-code-ai/tests/test_patcher_performance.py "
        "--ignore=secure-code-ai/tests/test_output_validation.py "
        "--ignore=secure-code-ai/tests/test_scanner_llm.py "
        "--ignore=secure-code-ai/tests/test_speculator_llm.py "
        "--ignore=secure-code-ai/tests/test_patcher_llm.py "
        "--tb=short"
    )
    
    unit_result = run_command(unit_test_cmd, "Unit Tests")
    results['unit_tests'] = {
        'returncode': unit_result.returncode,
        'passed': unit_result.returncode == 0
    }
    
    # 2. Run all property-based tests
    print("\n" + "="*80)
    print("RUNNING PROPERTY-BASED TESTS")
    print("="*80)
    
    property_test_cmd = (
        "python -m pytest "
        "secure-code-ai/tests/test_scanner_llm.py "
        "secure-code-ai/tests/test_speculator_llm.py "
        "secure-code-ai/tests/test_patcher_llm.py "
        "secure-code-ai/tests/test_output_validation.py "
        "secure-code-ai/tests/test_scanner_performance.py "
        "secure-code-ai/tests/test_patcher_performance.py "
        "-v "
        "--tb=short"
    )
    
    property_result = run_command(property_test_cmd, "Property-Based Tests")
    results['property_tests'] = {
        'returncode': property_result.returncode,
        'passed': property_result.returncode == 0
    }
    
    # 3. Run integration tests (E2E workflows)
    print("\n" + "="*80)
    print("RUNNING INTEGRATION TESTS")
    print("="*80)
    
    integration_test_cmd = (
        "python -m pytest "
        "secure-code-ai/tests/test_analyze_integration.py "
        "secure-code-ai/tests/test_e2e_workflow.py "
        "secure-code-ai/tests/test_self_correction_e2e.py "
        "secure-code-ai/tests/test_neuro_slicing_effectiveness.py "
        "-v "
        "--tb=short"
    )
    
    integration_result = run_command(integration_test_cmd, "Integration Tests")
    results['integration_tests'] = {
        'returncode': integration_result.returncode,
        'passed': integration_result.returncode == 0
    }
    
    # 4. Generate coverage report
    print("\n" + "="*80)
    print("GENERATING COVERAGE REPORT")
    print("="*80)
    
    coverage_cmd = (
        "python -m pytest secure-code-ai/tests/ "
        "--ignore=secure-code-ai/tests/test_docker_integration.py "
        "--ignore=secure-code-ai/tests/test_docker_compose_config.py "
        "--ignore=secure-code-ai/tests/load_test.py "
        "--cov=secure-code-ai/api "
        "--cov=secure-code-ai/agent "
        "--cov-report=term-missing "
        "--cov-report=html "
        "--cov-report=json "
        "-q"
    )
    
    coverage_result = run_command(coverage_cmd, "Coverage Report")
    results['coverage'] = {
        'returncode': coverage_result.returncode,
        'passed': coverage_result.returncode == 0
    }
    
    # Try to read coverage percentage from JSON
    try:
        coverage_json_path = project_root / "coverage.json"
        if coverage_json_path.exists():
            with open(coverage_json_path) as f:
                coverage_data = json.load(f)
                total_coverage = coverage_data['totals']['percent_covered']
                results['coverage']['percentage'] = total_coverage
                print(f"\nTotal Coverage: {total_coverage:.2f}%")
    except Exception as e:
        print(f"Could not read coverage data: {e}")
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    
    for test_type, result in results.items():
        status = "✓ PASSED" if result['passed'] else "✗ FAILED"
        print(f"{test_type.upper()}: {status}")
        if 'percentage' in result:
            print(f"  Coverage: {result['percentage']:.2f}%")
    
    print(f"\nCompleted at: {datetime.now().isoformat()}")
    
    # Return exit code based on results
    all_passed = all(r['passed'] for r in results.values())
    
    # Check coverage threshold
    coverage_ok = True
    if 'percentage' in results.get('coverage', {}):
        coverage_ok = results['coverage']['percentage'] >= 80.0
        if not coverage_ok:
            print(f"\n⚠ WARNING: Coverage ({results['coverage']['percentage']:.2f}%) is below 80% threshold")
    
    if all_passed and coverage_ok:
        print("\n✓ All tests passed and coverage threshold met!")
        return 0
    else:
        print("\n✗ Some tests failed or coverage threshold not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
