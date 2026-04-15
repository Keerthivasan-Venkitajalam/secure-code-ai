"""
Report generation with plots and tables.

This module generates comparison plots (bar charts, line graphs),
LaTeX tables for papers, and markdown reports for GitHub.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates evaluation reports with plots and tables.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir or Path("results/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comparison_plots(
        self,
        comparison_data: Dict[str, Any],
        filename_prefix: str = "comparison"
    ):
        """
        Generate comparison plots.
        
        Args:
            comparison_data: Dictionary with comparison results
            filename_prefix: Prefix for output files
        """
        logger.info("Generating comparison plots")
        
        # Detection rate comparison
        self._plot_detection_rates(
            comparison_data.get('detection_rates', {}),
            f"{filename_prefix}_detection_rates.png"
        )
        
        # Execution time comparison
        self._plot_execution_times(
            comparison_data.get('avg_execution_times', {}),
            f"{filename_prefix}_execution_times.png"
        )
        
        # Combined metrics comparison
        self._plot_combined_metrics(
            comparison_data,
            f"{filename_prefix}_combined.png"
        )
    
    def _plot_detection_rates(
        self,
        detection_rates: Dict[str, float],
        filename: str
    ):
        """
        Plot detection rate comparison.
        
        Args:
            detection_rates: Dictionary of system -> detection rate
            filename: Output filename
        """
        if not detection_rates:
            logger.warning("No detection rates to plot")
            return
        
        systems = list(detection_rates.keys())
        rates = [detection_rates[s] * 100 for s in systems]
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(systems, rates, color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12'])
        
        # Customize
        ax.set_ylabel('Detection Rate (%)', fontsize=12)
        ax.set_title('Vulnerability Detection Rate Comparison', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{height:.1f}%',
                ha='center',
                va='bottom',
                fontsize=10
            )
        
        plt.tight_layout()
        output_file = self.output_dir / filename
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved detection rate plot to {output_file}")
    
    def _plot_execution_times(
        self,
        execution_times: Dict[str, float],
        filename: str
    ):
        """
        Plot execution time comparison.
        
        Args:
            execution_times: Dictionary of system -> execution time
            filename: Output filename
        """
        if not execution_times:
            logger.warning("No execution times to plot")
            return
        
        systems = list(execution_times.keys())
        times = [execution_times[s] for s in systems]
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(systems, times, color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12'])
        
        # Customize
        ax.set_ylabel('Average Execution Time (seconds)', fontsize=12)
        ax.set_title('Execution Time Comparison', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{height:.2f}s',
                ha='center',
                va='bottom',
                fontsize=10
            )
        
        plt.tight_layout()
        output_file = self.output_dir / filename
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved execution time plot to {output_file}")
    
    def _plot_combined_metrics(
        self,
        comparison_data: Dict[str, Any],
        filename: str
    ):
        """
        Plot combined metrics comparison.
        
        Args:
            comparison_data: Dictionary with comparison results
            filename: Output filename
        """
        detection_rates = comparison_data.get('detection_rates', {})
        if not detection_rates:
            logger.warning("No data for combined metrics plot")
            return
        
        systems = list(detection_rates.keys())
        detection = [detection_rates[s] * 100 for s in systems]
        
        # Create grouped bar chart
        x = np.arange(len(systems))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars1 = ax.bar(x - width/2, detection, width, label='Detection Rate', color='#2ecc71')
        
        # Add execution times if available (normalized to 0-100 scale)
        execution_times = comparison_data.get('avg_execution_times', {})
        if execution_times:
            max_time = max(execution_times.values())
            normalized_times = [
                (execution_times.get(s, 0) / max_time) * 100
                for s in systems
            ]
            bars2 = ax.bar(x + width/2, normalized_times, width, label='Speed (normalized)', color='#3498db')
        
        # Customize
        ax.set_ylabel('Percentage', fontsize=12)
        ax.set_title('System Comparison: Detection Rate and Speed', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(systems)
        ax.legend()
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_file = self.output_dir / filename
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved combined metrics plot to {output_file}")
    
    def generate_latex_table(
        self,
        metrics: Dict[str, Any],
        filename: str = "results_table.tex"
    ):
        """
        Generate LaTeX table for research paper.
        
        Args:
            metrics: Dictionary of metrics
            filename: Output filename
        """
        logger.info("Generating LaTeX table")
        
        # Create LaTeX table
        latex = r"""\begin{table}[h]
\centering
\caption{Benchmark Results Comparison}
\label{tab:results}
\begin{tabular}{lcccc}
\toprule
\textbf{System} & \textbf{Detection Rate} & \textbf{Precision} & \textbf{F1 Score} & \textbf{Exec. Time (s)} \\
\midrule
"""
        
        # Add rows for each system
        if 'detection_rates' in metrics:
            for system, rate in metrics['detection_rates'].items():
                precision = metrics.get('precision', {}).get(system, 0.0)
                f1 = metrics.get('f1_score', {}).get(system, 0.0)
                time = metrics.get('avg_execution_times', {}).get(system, 0.0)
                
                latex += f"{system.replace('_', ' ').title()} & {rate:.2%} & {precision:.2%} & {f1:.2%} & {time:.2f} \\\\\n"
        
        latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
        
        # Save to file
        output_file = self.output_dir / filename
        with open(output_file, 'w') as f:
            f.write(latex)
        
        logger.info(f"Saved LaTeX table to {output_file}")
    
    def generate_markdown_report(
        self,
        metrics: Dict[str, Any],
        comparison_data: Optional[Dict[str, Any]] = None,
        filename: str = "BENCHMARK_RESULTS.md"
    ):
        """
        Generate markdown report for GitHub.
        
        Args:
            metrics: Dictionary of metrics
            comparison_data: Optional comparison data
            filename: Output filename
        """
        logger.info("Generating markdown report")
        
        report = "# Benchmark Results\n\n"
        report += "## Overview\n\n"
        report += f"Total samples evaluated: {metrics.get('total_samples', 0)}\n\n"
        
        # Detection metrics
        report += "## Detection Metrics\n\n"
        report += "| Metric | Value |\n"
        report += "|--------|-------|\n"
        report += f"| Detection Rate (Recall) | {metrics.get('detection_rate', 0):.2%} |\n"
        report += f"| Precision | {metrics.get('precision', 0):.2%} |\n"
        report += f"| F1 Score | {metrics.get('f1_score', 0):.2%} |\n"
        report += f"| False Positive Rate | {metrics.get('false_positive_rate', 0):.2%} |\n"
        report += f"| False Negative Rate | {metrics.get('false_negative_rate', 0):.2%} |\n\n"
        
        # Patch metrics
        report += "## Patch Metrics\n\n"
        report += "| Metric | Value |\n"
        report += "|--------|-------|\n"
        report += f"| Patch Generation Rate | {metrics.get('patch_generation_rate', 0):.2%} |\n"
        report += f"| Patch Validity Rate | {metrics.get('patch_validity_rate', 0):.2%} |\n"
        report += f"| Patch Correctness Rate | {metrics.get('patch_correctness_rate', 0):.2%} |\n\n"
        
        # Code quality metrics
        report += "## Code Quality Metrics\n\n"
        report += "| Metric | Value |\n"
        report += "|--------|-------|\n"
        report += f"| Average Code Churn | {metrics.get('avg_code_churn', 0):.1f} lines |\n"
        report += f"| Average Patch Size | {metrics.get('avg_patch_size', 0):.0f} characters |\n\n"
        
        # Performance metrics
        report += "## Performance Metrics\n\n"
        report += "| Metric | Value |\n"
        report += "|--------|-------|\n"
        report += f"| Average Execution Time | {metrics.get('avg_execution_time', 0):.2f} seconds |\n\n"
        
        # Baseline comparison
        if comparison_data and 'detection_rates' in comparison_data:
            report += "## Baseline Comparison\n\n"
            report += "| System | Detection Rate | Execution Time |\n"
            report += "|--------|----------------|----------------|\n"
            
            for system in comparison_data['detection_rates'].keys():
                rate = comparison_data['detection_rates'][system]
                time = comparison_data.get('avg_execution_times', {}).get(system, 0)
                report += f"| {system.replace('_', ' ').title()} | {rate:.2%} | {time:.2f}s |\n"
            
            report += "\n"
        
        # Confusion matrix
        report += "## Confusion Matrix\n\n"
        report += "| | Predicted Positive | Predicted Negative |\n"
        report += "|---|--------------------|--------------------||\n"
        report += f"| **Actual Positive** | {metrics.get('true_positives', 0)} (TP) | {metrics.get('false_negatives', 0)} (FN) |\n"
        report += f"| **Actual Negative** | {metrics.get('false_positives', 0)} (FP) | {metrics.get('true_negatives', 0)} (TN) |\n\n"
        
        # Add plots section
        report += "## Visualizations\n\n"
        report += "See the `results/reports/` directory for detailed plots and charts.\n\n"
        
        # Save to file
        output_file = self.output_dir / filename
        with open(output_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Saved markdown report to {output_file}")
    
    def generate_full_report(
        self,
        metrics: Dict[str, Any],
        comparison_data: Optional[Dict[str, Any]] = None
    ):
        """
        Generate all report formats.
        
        Args:
            metrics: Dictionary of metrics
            comparison_data: Optional comparison data
        """
        logger.info("Generating full report suite")
        
        # Generate plots
        if comparison_data:
            self.generate_comparison_plots(comparison_data)
        
        # Generate LaTeX table
        if comparison_data:
            self.generate_latex_table(comparison_data)
        
        # Generate markdown report
        self.generate_markdown_report(metrics, comparison_data)
        
        logger.info("Full report generation complete")
