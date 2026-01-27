"""
Benchmark evaluation infrastructure for SecureCodeAI.

This module provides tools for evaluating the system on standard security benchmarks
including CyberSecEval 3 and PySecDB.
"""

from .evaluator import BenchmarkEvaluator, EvaluationResults
from .cyberseceval import CyberSecEvalRunner
from .pysecdb import PySecDBRunner
from .baselines import BaselineComparator
from .metrics import MetricsCollector
from .reporting import ReportGenerator
from .ablation import (
    AblationStudy,
    measure_symbolic_feedback_impact,
    measure_neuro_slicing_impact,
    measure_self_correction_impact
)

__all__ = [
    "BenchmarkEvaluator",
    "EvaluationResults",
    "CyberSecEvalRunner",
    "PySecDBRunner",
    "BaselineComparator",
    "MetricsCollector",
    "ReportGenerator",
    "AblationStudy",
    "measure_symbolic_feedback_impact",
    "measure_neuro_slicing_impact",
    "measure_self_correction_impact",
]
