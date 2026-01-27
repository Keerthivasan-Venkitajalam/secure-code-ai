#!/usr/bin/env python3
"""
Example usage of the benchmark evaluation infrastructure.

This script demonstrates how to run benchmarks and generate reports.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks import BenchmarkEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class MockAPIClient:
    """Mock API client for demonstration."""
    
    def analyze(self, code: str, language: str = "python"):
        """Mock analyze method."""
        # Simple heuristic: detect common vulnerability patterns
        vulnerabilities = []
        
        if "pickle.loads" in code or "yaml.load" in code:
            vulnerabilities.append({
                'type': 'insecure_deserialization',
                'severity': 'high',
                'line': 1,
                'patch': code.replace('pickle.loads', 'pickle.loads  # TODO: Use safe deserialization')
            })
        
        if "shell=True" in code:
            vulnerabilities.append({
                'type': 'command_injection',
                'severity': 'critical',
                'line': 1,
                'patch': code.replace('shell=True', 'shell=False')
            })
        
        if "md5" in code or "sha1" in code:
            vulnerabilities.append({
                'type': 'weak_crypto',
                'severity': 'medium',
                'line': 1,
                'patch': code.replace('md5', 'sha256')
            })
        
        return {'vulnerabilities': vulnerabilities}


def main():
    """Run example benchmark evaluation."""
    logger.info("Starting benchmark evaluation example")
    
    # Create mock API client
    api_client = MockAPIClient()
    
    # Initialize evaluator
    evaluator = BenchmarkEvaluator(
        api_client=api_client,
        llm_client=None,  # No LLM client for this example
        output_dir=Path("results_example")
    )
    
    # Run CyberSecEval 3 benchmark (with mock data)
    logger.info("Running CyberSecEval 3 benchmark...")
    cybersec_result = evaluator.run_cyberseceval(
        include_baselines=False,  # Skip baselines for quick demo
        max_samples=3  # Only run 3 samples
    )
    
    # Print results
    print("\n" + "="*60)
    print("CyberSecEval 3 Results")
    print("="*60)
    print(f"Total Samples: {cybersec_result.metrics.total_samples}")
    print(f"Detection Rate: {cybersec_result.metrics.detection_rate:.2%}")
    print(f"Precision: {cybersec_result.metrics.precision:.2%}")
    print(f"F1 Score: {cybersec_result.metrics.f1_score:.2%}")
    print(f"Patch Generation Rate: {cybersec_result.metrics.patch_generation_rate:.2%}")
    print(f"Avg Execution Time: {cybersec_result.metrics.avg_execution_time:.2f}s")
    print("="*60 + "\n")
    
    # Run PySecDB benchmark (with mock data)
    logger.info("Running PySecDB benchmark...")
    pysecdb_result = evaluator.run_pysecdb(
        include_baselines=False,
        max_samples=3
    )
    
    # Print results
    print("\n" + "="*60)
    print("PySecDB Results")
    print("="*60)
    print(f"Total Samples: {pysecdb_result.metrics.total_samples}")
    print(f"Detection Rate: {pysecdb_result.metrics.detection_rate:.2%}")
    print(f"Precision: {pysecdb_result.metrics.precision:.2%}")
    print(f"F1 Score: {pysecdb_result.metrics.f1_score:.2%}")
    print(f"Patch Validity Rate: {pysecdb_result.metrics.patch_validity_rate:.2%}")
    print(f"Avg Execution Time: {pysecdb_result.metrics.avg_execution_time:.2f}s")
    print("="*60 + "\n")
    
    logger.info(f"Results saved to: {evaluator.output_dir}")
    logger.info("Check the following directories:")
    logger.info(f"  - Metrics: {evaluator.output_dir / 'metrics'}")
    logger.info(f"  - Reports: {evaluator.output_dir / 'reports'}")
    logger.info(f"  - Raw results: {evaluator.output_dir / 'cyberseceval3'} and {evaluator.output_dir / 'pysecdb'}")


if __name__ == "__main__":
    main()
