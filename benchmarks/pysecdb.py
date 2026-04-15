"""
PySecDB benchmark integration.

This module implements PySecDB evaluation for real-world CVE-mapped vulnerabilities.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from tqdm import tqdm
import time

logger = logging.getLogger(__name__)


@dataclass
class PySecDBSample:
    """A single sample from PySecDB dataset."""
    id: str
    cve_id: str
    code: str
    vulnerability_type: str
    language: str
    severity: str
    description: str
    expected_patch: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class PySecDBResult:
    """Result for a single PySecDB sample."""
    sample_id: str
    cve_id: str
    detected: bool
    vulnerability_type: Optional[str]
    patch_generated: bool
    patch_valid: bool
    patch_matches_expected: bool
    execution_time: float
    error: Optional[str] = None


class PySecDBRunner:
    """
    Runner for PySecDB benchmark.
    
    This benchmark evaluates the system on real-world CVE-mapped vulnerabilities
    from the Python Security Database.
    """
    
    def __init__(
        self,
        api_client,
        dataset_path: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize PySecDB runner.
        
        Args:
            api_client: Client for SecureCodeAI API
            dataset_path: Path to PySecDB dataset
            output_dir: Directory for output files
        """
        self.api_client = api_client
        self.dataset_path = dataset_path or Path("data/pysecdb")
        self.output_dir = output_dir or Path("results/pysecdb")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_dataset(self) -> List[PySecDBSample]:
        """
        Load PySecDB dataset.
        
        Returns:
            List of PySecDBSample objects
        """
        logger.info(f"Loading PySecDB dataset from {self.dataset_path}")
        
        if not self.dataset_path.exists():
            logger.warning(f"Dataset path {self.dataset_path} does not exist")
            return self._load_mock_dataset()
        
        samples = []
        dataset_file = self.dataset_path / "vulnerabilities.json"
        
        if dataset_file.exists():
            with open(dataset_file, 'r') as f:
                data = json.load(f)
                for item in data:
                    samples.append(PySecDBSample(
                        id=item.get('id', ''),
                        cve_id=item.get('cve_id', ''),
                        code=item.get('vulnerable_code', ''),
                        vulnerability_type=item.get('vulnerability_type', ''),
                        language=item.get('language', 'python'),
                        severity=item.get('severity', 'medium'),
                        description=item.get('description', ''),
                        expected_patch=item.get('patched_code'),
                        metadata=item.get('metadata', {})
                    ))
        else:
            logger.warning(f"Dataset file {dataset_file} not found, using mock data")
            samples = self._load_mock_dataset()
        
        logger.info(f"Loaded {len(samples)} samples")
        return samples
    
    def _load_mock_dataset(self) -> List[PySecDBSample]:
        """Load mock dataset for testing when real dataset is unavailable."""
        return [
            PySecDBSample(
                id="pysec_001",
                cve_id="CVE-2023-XXXX",
                code="import yaml\nconfig = yaml.load(user_input)",
                vulnerability_type="unsafe_deserialization",
                language="python",
                severity="high",
                description="Unsafe YAML deserialization",
                expected_patch="import yaml\nconfig = yaml.safe_load(user_input)",
                metadata={"package": "pyyaml"}
            ),
            PySecDBSample(
                id="pysec_002",
                cve_id="CVE-2023-YYYY",
                code="import subprocess\nsubprocess.call(user_command, shell=True)",
                vulnerability_type="command_injection",
                language="python",
                severity="critical",
                description="Command injection via shell=True",
                expected_patch="import subprocess\nsubprocess.call(user_command.split(), shell=False)",
                metadata={"package": "subprocess"}
            ),
            PySecDBSample(
                id="pysec_003",
                cve_id="CVE-2023-ZZZZ",
                code="import os\nfilename = os.path.join(base_dir, user_path)",
                vulnerability_type="path_traversal",
                language="python",
                severity="high",
                description="Path traversal vulnerability",
                expected_patch="import os\nfilename = os.path.normpath(os.path.join(base_dir, user_path))\nif not filename.startswith(base_dir):\n    raise ValueError('Invalid path')",
                metadata={"package": "os"}
            ),
        ]
    
    def run_cve_benchmark(
        self,
        max_samples: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run PySecDB CVE-mapped vulnerability benchmark.
        
        Args:
            max_samples: Maximum number of samples to evaluate (None for all)
            
        Returns:
            Dictionary containing benchmark results
        """
        logger.info("Starting PySecDB CVE benchmark")
        
        samples = self.load_dataset()
        if max_samples:
            samples = samples[:max_samples]
        
        results = []
        for sample in tqdm(samples, desc="Evaluating CVE samples"):
            result = self._evaluate_sample(sample)
            results.append(result)
        
        # Calculate metrics
        metrics = self._calculate_metrics(results)
        
        # Save results
        self._save_results(results, metrics)
        
        return {
            "results": results,
            "metrics": metrics,
            "total_samples": len(samples)
        }
    
    def _evaluate_sample(self, sample: PySecDBSample) -> PySecDBResult:
        """
        Evaluate a single sample.
        
        Args:
            sample: PySecDBSample to evaluate
            
        Returns:
            PySecDBResult
        """
        start_time = time.time()
        
        try:
            # Call API to analyze code
            response = self.api_client.analyze(
                code=sample.code,
                language=sample.language
            )
            
            detected = len(response.get('vulnerabilities', [])) > 0
            vulnerability_type = None
            patch_generated = False
            patch_valid = False
            patch_matches_expected = False
            
            if detected:
                vuln = response['vulnerabilities'][0]
                vulnerability_type = vuln.get('type')
                
                # Check if patch was generated
                if 'patch' in vuln:
                    patch_generated = True
                    patch_code = vuln['patch']
                    
                    # Validate patch
                    patch_valid = self._validate_patch(patch_code, sample)
                    
                    # Check if patch matches expected
                    if sample.expected_patch:
                        patch_matches_expected = self._compare_patches(
                            patch_code,
                            sample.expected_patch
                        )
            
            execution_time = time.time() - start_time
            
            return PySecDBResult(
                sample_id=sample.id,
                cve_id=sample.cve_id,
                detected=detected,
                vulnerability_type=vulnerability_type,
                patch_generated=patch_generated,
                patch_valid=patch_valid,
                patch_matches_expected=patch_matches_expected,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error evaluating sample {sample.id}: {e}")
            return PySecDBResult(
                sample_id=sample.id,
                cve_id=sample.cve_id,
                detected=False,
                vulnerability_type=None,
                patch_generated=False,
                patch_valid=False,
                patch_matches_expected=False,
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    def _validate_patch(self, patch_code: str, sample: PySecDBSample) -> bool:
        """
        Validate that patch fixes the vulnerability.
        
        Args:
            patch_code: Generated patch code
            sample: Original sample
            
        Returns:
            True if patch is valid, False otherwise
        """
        try:
            # Basic validation: check that patch is different from original
            if patch_code.strip() == sample.code.strip():
                return False
            
            # Check that patch is syntactically valid Python
            try:
                compile(patch_code, '<string>', 'exec')
            except SyntaxError:
                return False
            
            # Additional validation could include:
            # - Running static analysis on patched code
            # - Checking that vulnerability is no longer present
            # - Running test cases
            
            return True
            
        except Exception as e:
            logger.warning(f"Patch validation failed: {e}")
            return False
    
    def _compare_patches(self, generated: str, expected: str) -> bool:
        """
        Compare generated patch with expected patch.
        
        Args:
            generated: Generated patch code
            expected: Expected patch code
            
        Returns:
            True if patches are similar, False otherwise
        """
        # Normalize whitespace and compare
        gen_normalized = ' '.join(generated.split())
        exp_normalized = ' '.join(expected.split())
        
        # Simple string similarity check
        # In production, could use more sophisticated comparison
        return gen_normalized == exp_normalized
    
    def calculate_patch_validity(self, results: List[PySecDBResult]) -> float:
        """
        Calculate patch validity rate.
        
        Args:
            results: List of PySecDBResult objects
            
        Returns:
            Patch validity rate as a float between 0 and 1
        """
        if not results:
            return 0.0
        
        patches_generated = [r for r in results if r.patch_generated]
        if not patches_generated:
            return 0.0
        
        valid_patches = sum(1 for r in patches_generated if r.patch_valid)
        return valid_patches / len(patches_generated)
    
    def _calculate_metrics(self, results: List[PySecDBResult]) -> Dict[str, float]:
        """
        Calculate benchmark metrics.
        
        Args:
            results: List of PySecDBResult objects
            
        Returns:
            Dictionary of metrics
        """
        total = len(results)
        if total == 0:
            return {}
        
        detected_count = sum(1 for r in results if r.detected)
        patch_generated_count = sum(1 for r in results if r.patch_generated)
        patch_valid_count = sum(1 for r in results if r.patch_valid)
        patch_matches_count = sum(1 for r in results if r.patch_matches_expected)
        error_count = sum(1 for r in results if r.error is not None)
        
        avg_execution_time = sum(r.execution_time for r in results) / total
        
        return {
            "detection_rate": detected_count / total,
            "patch_generation_rate": patch_generated_count / total,
            "patch_validity_rate": patch_valid_count / patch_generated_count if patch_generated_count > 0 else 0.0,
            "patch_match_rate": patch_matches_count / patch_generated_count if patch_generated_count > 0 else 0.0,
            "error_rate": error_count / total,
            "avg_execution_time": avg_execution_time,
            "total_samples": total,
            "detected_count": detected_count,
            "patch_generated_count": patch_generated_count,
            "patch_valid_count": patch_valid_count,
            "patch_matches_count": patch_matches_count,
        }
    
    def _save_results(
        self,
        results: List[PySecDBResult],
        metrics: Dict[str, float]
    ):
        """
        Save results to files.
        
        Args:
            results: List of results
            metrics: Dictionary of metrics
        """
        # Save detailed results as JSON
        results_file = self.output_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump(
                [vars(r) for r in results],
                f,
                indent=2
            )
        logger.info(f"Saved detailed results to {results_file}")
        
        # Save metrics as JSON
        metrics_file = self.output_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Saved metrics to {metrics_file}")
