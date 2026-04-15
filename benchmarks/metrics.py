"""
Metrics collection and reporting.

This module collects and exports benchmark metrics including Detection Rate,
False Positive Rate, Patch Validity Rate, and Code Churn.
"""

import csv
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import difflib

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Comprehensive benchmark metrics."""
    # Detection metrics
    detection_rate: float  # Recall: TP / (TP + FN)
    precision: float  # TP / (TP + FP)
    false_positive_rate: float  # FP / (FP + TN)
    false_negative_rate: float  # FN / (FN + TP)
    f1_score: float  # 2 * (precision * recall) / (precision + recall)
    
    # Patch metrics
    patch_generation_rate: float
    patch_validity_rate: float
    patch_correctness_rate: float
    
    # Code quality metrics
    avg_code_churn: float  # Average lines changed per patch
    avg_patch_size: float  # Average patch size in characters
    
    # Performance metrics
    avg_execution_time: float
    total_samples: int
    
    # Counts
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int


class MetricsCollector:
    """
    Collects and aggregates metrics from benchmark results.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir or Path("results/metrics")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_metrics(
        self,
        results: List[Any],
        ground_truth: Optional[List[bool]] = None
    ) -> BenchmarkMetrics:
        """
        Collect comprehensive metrics from results.
        
        Args:
            results: List of benchmark results
            ground_truth: Optional list of ground truth labels
            
        Returns:
            BenchmarkMetrics object
        """
        logger.info("Collecting metrics")
        
        total = len(results)
        if total == 0:
            return self._empty_metrics()
        
        # Calculate detection metrics
        if ground_truth:
            tp, fp, tn, fn = self._calculate_confusion_matrix(results, ground_truth)
        else:
            # If no ground truth, assume all detections are correct
            tp = sum(1 for r in results if r.detected)
            fp = 0
            tn = sum(1 for r in results if not r.detected)
            fn = 0
        
        detection_rate = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        f1 = 2 * (precision * detection_rate) / (precision + detection_rate) if (precision + detection_rate) > 0 else 0.0
        
        # Calculate patch metrics
        patch_generated = [r for r in results if hasattr(r, 'patch_generated') and r.patch_generated]
        patch_generation_rate = len(patch_generated) / total
        
        if patch_generated:
            patch_validity_rate = sum(
                1 for r in patch_generated
                if hasattr(r, 'patch_valid') and r.patch_valid
            ) / len(patch_generated)
            
            patch_correctness_rate = sum(
                1 for r in patch_generated
                if hasattr(r, 'patch_matches_expected') and r.patch_matches_expected
            ) / len(patch_generated)
        else:
            patch_validity_rate = 0.0
            patch_correctness_rate = 0.0
        
        # Calculate code quality metrics
        avg_code_churn = self._calculate_avg_code_churn(results)
        avg_patch_size = self._calculate_avg_patch_size(results)
        
        # Calculate performance metrics
        avg_execution_time = sum(r.execution_time for r in results) / total
        
        metrics = BenchmarkMetrics(
            detection_rate=detection_rate,
            precision=precision,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            f1_score=f1,
            patch_generation_rate=patch_generation_rate,
            patch_validity_rate=patch_validity_rate,
            patch_correctness_rate=patch_correctness_rate,
            avg_code_churn=avg_code_churn,
            avg_patch_size=avg_patch_size,
            avg_execution_time=avg_execution_time,
            total_samples=total,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn
        )
        
        return metrics
    
    def _calculate_confusion_matrix(
        self,
        results: List[Any],
        ground_truth: List[bool]
    ) -> tuple:
        """
        Calculate confusion matrix.
        
        Args:
            results: List of results
            ground_truth: List of ground truth labels
            
        Returns:
            Tuple of (TP, FP, TN, FN)
        """
        tp = fp = tn = fn = 0
        
        for result, truth in zip(results, ground_truth):
            detected = result.detected
            
            if detected and truth:
                tp += 1
            elif detected and not truth:
                fp += 1
            elif not detected and not truth:
                tn += 1
            else:  # not detected and truth
                fn += 1
        
        return tp, fp, tn, fn
    
    def _calculate_avg_code_churn(self, results: List[Any]) -> float:
        """
        Calculate average code churn (lines changed).
        
        Args:
            results: List of results
            
        Returns:
            Average code churn
        """
        churns = []
        
        for result in results:
            if hasattr(result, 'patch_generated') and result.patch_generated:
                # Try to get original and patched code
                if hasattr(result, 'original_code') and hasattr(result, 'patched_code'):
                    churn = self._calculate_code_churn(
                        result.original_code,
                        result.patched_code
                    )
                    churns.append(churn)
        
        return sum(churns) / len(churns) if churns else 0.0
    
    def _calculate_code_churn(self, original: str, patched: str) -> int:
        """
        Calculate code churn between two code snippets.
        
        Args:
            original: Original code
            patched: Patched code
            
        Returns:
            Number of lines changed
        """
        original_lines = original.splitlines()
        patched_lines = patched.splitlines()
        
        diff = difflib.unified_diff(original_lines, patched_lines)
        
        # Count lines that start with + or - (excluding +++ and ---)
        changes = sum(
            1 for line in diff
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))
        )
        
        return changes
    
    def _calculate_avg_patch_size(self, results: List[Any]) -> float:
        """
        Calculate average patch size in characters.
        
        Args:
            results: List of results
            
        Returns:
            Average patch size
        """
        sizes = []
        
        for result in results:
            if hasattr(result, 'patch_generated') and result.patch_generated:
                if hasattr(result, 'patched_code'):
                    sizes.append(len(result.patched_code))
        
        return sum(sizes) / len(sizes) if sizes else 0.0
    
    def _empty_metrics(self) -> BenchmarkMetrics:
        """Return empty metrics."""
        return BenchmarkMetrics(
            detection_rate=0.0,
            precision=0.0,
            false_positive_rate=0.0,
            false_negative_rate=0.0,
            f1_score=0.0,
            patch_generation_rate=0.0,
            patch_validity_rate=0.0,
            patch_correctness_rate=0.0,
            avg_code_churn=0.0,
            avg_patch_size=0.0,
            avg_execution_time=0.0,
            total_samples=0,
            true_positives=0,
            false_positives=0,
            true_negatives=0,
            false_negatives=0
        )
    
    def export_to_csv(
        self,
        metrics: BenchmarkMetrics,
        filename: str = "metrics.csv"
    ):
        """
        Export metrics to CSV file.
        
        Args:
            metrics: BenchmarkMetrics object
            filename: Output filename
        """
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Metric', 'Value'])
            
            # Write metrics
            for key, value in asdict(metrics).items():
                writer.writerow([key, value])
        
        logger.info(f"Exported metrics to CSV: {output_file}")
    
    def export_to_json(
        self,
        metrics: BenchmarkMetrics,
        filename: str = "metrics.json"
    ):
        """
        Export metrics to JSON file.
        
        Args:
            metrics: BenchmarkMetrics object
            filename: Output filename
        """
        output_file = self.output_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
        
        logger.info(f"Exported metrics to JSON: {output_file}")
    
    def export_summary(
        self,
        metrics: BenchmarkMetrics,
        filename: str = "summary.txt"
    ):
        """
        Export human-readable summary.
        
        Args:
            metrics: BenchmarkMetrics object
            filename: Output filename
        """
        output_file = self.output_dir / filename
        
        summary = f"""
Benchmark Metrics Summary
========================

Detection Metrics:
- Detection Rate (Recall): {metrics.detection_rate:.2%}
- Precision: {metrics.precision:.2%}
- F1 Score: {metrics.f1_score:.2%}
- False Positive Rate: {metrics.false_positive_rate:.2%}
- False Negative Rate: {metrics.false_negative_rate:.2%}

Patch Metrics:
- Patch Generation Rate: {metrics.patch_generation_rate:.2%}
- Patch Validity Rate: {metrics.patch_validity_rate:.2%}
- Patch Correctness Rate: {metrics.patch_correctness_rate:.2%}

Code Quality Metrics:
- Average Code Churn: {metrics.avg_code_churn:.1f} lines
- Average Patch Size: {metrics.avg_patch_size:.0f} characters

Performance Metrics:
- Average Execution Time: {metrics.avg_execution_time:.2f} seconds
- Total Samples: {metrics.total_samples}

Confusion Matrix:
- True Positives: {metrics.true_positives}
- False Positives: {metrics.false_positives}
- True Negatives: {metrics.true_negatives}
- False Negatives: {metrics.false_negatives}
"""
        
        with open(output_file, 'w') as f:
            f.write(summary)
        
        logger.info(f"Exported summary to: {output_file}")
        print(summary)
