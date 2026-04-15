"""
Main benchmark evaluator.

This module provides the main BenchmarkEvaluator class that orchestrates
all benchmark evaluations and comparisons.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from .cyberseceval import CyberSecEvalRunner
from .pysecdb import PySecDBRunner
from .baselines import BaselineComparator
from .metrics import MetricsCollector, BenchmarkMetrics
from .reporting import ReportGenerator

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResults:
    """Complete evaluation results."""
    benchmark_name: str
    securecodai_results: List[Any]
    baseline_results: Optional[Dict[str, List[Any]]]
    metrics: BenchmarkMetrics
    comparison_data: Optional[Dict[str, Any]]
    timestamp: str


class BenchmarkEvaluator:
    """
    Main evaluator for running benchmarks and generating reports.
    
    This class orchestrates:
    - Running CyberSecEval 3 and PySecDB benchmarks
    - Comparing against baselines (DeepSeek, Bandit, Semgrep)
    - Collecting comprehensive metrics
    - Generating reports and visualizations
    """
    
    def __init__(
        self,
        api_client,
        llm_client=None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize benchmark evaluator.
        
        Args:
            api_client: Client for SecureCodeAI API
            llm_client: Optional LLM client for baseline comparisons
            output_dir: Base directory for all outputs
        """
        self.api_client = api_client
        self.llm_client = llm_client
        self.output_dir = output_dir or Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.cyberseceval_runner = CyberSecEvalRunner(
            api_client,
            output_dir=self.output_dir / "cyberseceval3"
        )
        self.pysecdb_runner = PySecDBRunner(
            api_client,
            output_dir=self.output_dir / "pysecdb"
        )
        self.baseline_comparator = BaselineComparator(
            llm_client,
            output_dir=self.output_dir / "baselines"
        )
        self.metrics_collector = MetricsCollector(
            output_dir=self.output_dir / "metrics"
        )
        self.report_generator = ReportGenerator(
            output_dir=self.output_dir / "reports"
        )
    
    def run_full_evaluation(
        self,
        benchmarks: Optional[List[str]] = None,
        include_baselines: bool = True,
        max_samples: Optional[int] = None
    ) -> Dict[str, EvaluationResults]:
        """
        Run full evaluation on all benchmarks.
        
        Args:
            benchmarks: List of benchmark names to run (None for all)
            include_baselines: Whether to run baseline comparisons
            max_samples: Maximum samples per benchmark (None for all)
            
        Returns:
            Dictionary of benchmark_name -> EvaluationResults
        """
        logger.info("Starting full benchmark evaluation")
        
        if benchmarks is None:
            benchmarks = ['cyberseceval3', 'pysecdb']
        
        results = {}
        
        for benchmark in benchmarks:
            logger.info(f"Running {benchmark} benchmark")
            
            if benchmark == 'cyberseceval3':
                result = self.run_cyberseceval(
                    include_baselines=include_baselines,
                    max_samples=max_samples
                )
                results['cyberseceval3'] = result
            
            elif benchmark == 'pysecdb':
                result = self.run_pysecdb(
                    include_baselines=include_baselines,
                    max_samples=max_samples
                )
                results['pysecdb'] = result
        
        # Generate combined report
        self._generate_combined_report(results)
        
        logger.info("Full evaluation complete")
        return results
    
    def run_cyberseceval(
        self,
        include_baselines: bool = True,
        max_samples: Optional[int] = None
    ) -> EvaluationResults:
        """
        Run CyberSecEval 3 benchmark.
        
        Args:
            include_baselines: Whether to run baseline comparisons
            max_samples: Maximum samples to evaluate
            
        Returns:
            EvaluationResults object
        """
        logger.info("Running CyberSecEval 3 benchmark")
        
        # Run main benchmark
        benchmark_results = self.cyberseceval_runner.run_autocomplete_benchmark(
            max_samples=max_samples
        )
        
        securecodai_results = benchmark_results['results']
        
        # Run baseline comparisons
        baseline_results = None
        comparison_data = None
        
        if include_baselines:
            samples = self.cyberseceval_runner.load_dataset()
            if max_samples:
                samples = samples[:max_samples]
            
            comparison_data = self.baseline_comparator.run_comparisons(
                samples,
                securecodai_results
            )
            baseline_results = comparison_data.get('results', {})
        
        # Collect metrics
        metrics = self.metrics_collector.collect_metrics(securecodai_results)
        
        # Export metrics
        self.metrics_collector.export_to_csv(metrics, "cyberseceval3_metrics.csv")
        self.metrics_collector.export_to_json(metrics, "cyberseceval3_metrics.json")
        self.metrics_collector.export_summary(metrics, "cyberseceval3_summary.txt")
        
        # Generate reports
        self.report_generator.generate_markdown_report(
            asdict(metrics),
            comparison_data,
            "CYBERSECEVAL3_RESULTS.md"
        )
        
        if comparison_data:
            self.report_generator.generate_comparison_plots(
                comparison_data,
                "cyberseceval3"
            )
            self.report_generator.generate_latex_table(
                comparison_data,
                "cyberseceval3_table.tex"
            )
        
        # Create evaluation results
        from datetime import datetime
        result = EvaluationResults(
            benchmark_name="CyberSecEval 3",
            securecodai_results=securecodai_results,
            baseline_results=baseline_results,
            metrics=metrics,
            comparison_data=comparison_data,
            timestamp=datetime.now().isoformat()
        )
        
        # Save complete results
        self._save_evaluation_results(result, "cyberseceval3")
        
        return result
    
    def run_pysecdb(
        self,
        include_baselines: bool = True,
        max_samples: Optional[int] = None
    ) -> EvaluationResults:
        """
        Run PySecDB benchmark.
        
        Args:
            include_baselines: Whether to run baseline comparisons
            max_samples: Maximum samples to evaluate
            
        Returns:
            EvaluationResults object
        """
        logger.info("Running PySecDB benchmark")
        
        # Run main benchmark
        benchmark_results = self.pysecdb_runner.run_cve_benchmark(
            max_samples=max_samples
        )
        
        securecodai_results = benchmark_results['results']
        
        # Run baseline comparisons
        baseline_results = None
        comparison_data = None
        
        if include_baselines:
            samples = self.pysecdb_runner.load_dataset()
            if max_samples:
                samples = samples[:max_samples]
            
            comparison_data = self.baseline_comparator.run_comparisons(
                samples,
                securecodai_results
            )
            baseline_results = comparison_data.get('results', {})
        
        # Collect metrics
        metrics = self.metrics_collector.collect_metrics(securecodai_results)
        
        # Export metrics
        self.metrics_collector.export_to_csv(metrics, "pysecdb_metrics.csv")
        self.metrics_collector.export_to_json(metrics, "pysecdb_metrics.json")
        self.metrics_collector.export_summary(metrics, "pysecdb_summary.txt")
        
        # Generate reports
        self.report_generator.generate_markdown_report(
            asdict(metrics),
            comparison_data,
            "PYSECDB_RESULTS.md"
        )
        
        if comparison_data:
            self.report_generator.generate_comparison_plots(
                comparison_data,
                "pysecdb"
            )
            self.report_generator.generate_latex_table(
                comparison_data,
                "pysecdb_table.tex"
            )
        
        # Create evaluation results
        from datetime import datetime
        result = EvaluationResults(
            benchmark_name="PySecDB",
            securecodai_results=securecodai_results,
            baseline_results=baseline_results,
            metrics=metrics,
            comparison_data=comparison_data,
            timestamp=datetime.now().isoformat()
        )
        
        # Save complete results
        self._save_evaluation_results(result, "pysecdb")
        
        return result
    
    def _save_evaluation_results(
        self,
        results: EvaluationResults,
        benchmark_name: str
    ):
        """
        Save complete evaluation results.
        
        Args:
            results: EvaluationResults object
            benchmark_name: Name of benchmark
        """
        output_file = self.output_dir / f"{benchmark_name}_complete_results.json"
        
        # Convert to dict (handle dataclasses)
        results_dict = {
            'benchmark_name': results.benchmark_name,
            'securecodai_results': [
                vars(r) if hasattr(r, '__dict__') else r
                for r in results.securecodai_results
            ],
            'baseline_results': results.baseline_results,
            'metrics': asdict(results.metrics),
            'comparison_data': results.comparison_data,
            'timestamp': results.timestamp
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"Saved complete results to {output_file}")
    
    def _generate_combined_report(
        self,
        all_results: Dict[str, EvaluationResults]
    ):
        """
        Generate combined report across all benchmarks.
        
        Args:
            all_results: Dictionary of benchmark results
        """
        logger.info("Generating combined report")
        
        report = "# Combined Benchmark Results\n\n"
        report += "## Summary\n\n"
        
        for benchmark_name, results in all_results.items():
            report += f"### {results.benchmark_name}\n\n"
            report += f"- Total Samples: {results.metrics.total_samples}\n"
            report += f"- Detection Rate: {results.metrics.detection_rate:.2%}\n"
            report += f"- Precision: {results.metrics.precision:.2%}\n"
            report += f"- F1 Score: {results.metrics.f1_score:.2%}\n"
            report += f"- Patch Validity Rate: {results.metrics.patch_validity_rate:.2%}\n"
            report += f"- Avg Execution Time: {results.metrics.avg_execution_time:.2f}s\n\n"
        
        report += "## Detailed Results\n\n"
        report += "See individual benchmark reports in the `results/reports/` directory.\n"
        
        output_file = self.output_dir / "reports" / "COMBINED_RESULTS.md"
        with open(output_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Saved combined report to {output_file}")
