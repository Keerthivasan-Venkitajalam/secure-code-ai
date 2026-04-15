"""
Baseline comparison system.

This module implements baseline comparisons against pure LLM (DeepSeek zero-shot)
and static analysis tools (Bandit, Semgrep).
"""

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
from tqdm import tqdm
import time

logger = logging.getLogger(__name__)


@dataclass
class BaselineResult:
    """Result from a baseline system."""
    sample_id: str
    detected: bool
    vulnerability_types: List[str]
    confidence: float
    execution_time: float
    error: Optional[str] = None


class BaselineComparator:
    """
    Compares SecureCodeAI against baseline systems.
    
    Baselines include:
    - Pure DeepSeek (zero-shot LLM)
    - Bandit (static analysis)
    - Semgrep (static analysis)
    """
    
    def __init__(
        self,
        llm_client=None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize baseline comparator.
        
        Args:
            llm_client: LLM client for zero-shot baseline
            output_dir: Directory for output files
        """
        self.llm_client = llm_client
        self.output_dir = output_dir or Path("results/baselines")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run_comparisons(
        self,
        samples: List[Any],
        securecodai_results: List[Any]
    ) -> Dict[str, Any]:
        """
        Run all baseline comparisons.
        
        Args:
            samples: List of benchmark samples
            securecodai_results: Results from SecureCodeAI
            
        Returns:
            Dictionary containing comparison results
        """
        logger.info("Running baseline comparisons")
        
        # Run each baseline
        deepseek_results = self._run_deepseek_baseline(samples)
        bandit_results = self._run_bandit_baseline(samples)
        semgrep_results = self._run_semgrep_baseline(samples)
        
        # Calculate comparative metrics
        comparison = self._compare_results(
            securecodai_results,
            deepseek_results,
            bandit_results,
            semgrep_results
        )
        
        # Save results
        self._save_comparison(comparison)
        
        return comparison
    
    def _run_deepseek_baseline(self, samples: List[Any]) -> List[BaselineResult]:
        """
        Run pure DeepSeek zero-shot baseline.
        
        Args:
            samples: List of benchmark samples
            
        Returns:
            List of BaselineResult objects
        """
        logger.info("Running DeepSeek zero-shot baseline")
        
        results = []
        for sample in tqdm(samples, desc="DeepSeek baseline"):
            start_time = time.time()
            
            try:
                if self.llm_client is None:
                    # Mock result if no LLM client
                    result = BaselineResult(
                        sample_id=sample.id,
                        detected=False,
                        vulnerability_types=[],
                        confidence=0.0,
                        execution_time=0.0,
                        error="No LLM client configured"
                    )
                else:
                    # Zero-shot prompt
                    prompt = f"""Analyze the following code for security vulnerabilities:

```python
{sample.code}
```

List any security vulnerabilities found. Be concise."""
                    
                    response = self.llm_client.generate(prompt)
                    
                    # Parse response (simple heuristic)
                    detected = any(
                        keyword in response.lower()
                        for keyword in ['vulnerability', 'vulnerable', 'security issue', 'risk']
                    )
                    
                    result = BaselineResult(
                        sample_id=sample.id,
                        detected=detected,
                        vulnerability_types=[],
                        confidence=0.5 if detected else 0.0,
                        execution_time=time.time() - start_time
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error in DeepSeek baseline for {sample.id}: {e}")
                results.append(BaselineResult(
                    sample_id=sample.id,
                    detected=False,
                    vulnerability_types=[],
                    confidence=0.0,
                    execution_time=time.time() - start_time,
                    error=str(e)
                ))
        
        return results
    
    def _run_bandit_baseline(self, samples: List[Any]) -> List[BaselineResult]:
        """
        Run Bandit static analysis baseline.
        
        Args:
            samples: List of benchmark samples
            
        Returns:
            List of BaselineResult objects
        """
        logger.info("Running Bandit baseline")
        
        results = []
        for sample in tqdm(samples, desc="Bandit baseline"):
            start_time = time.time()
            
            try:
                # Write code to temporary file
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False
                ) as f:
                    f.write(sample.code)
                    temp_file = f.name
                
                # Run Bandit
                result = subprocess.run(
                    ['bandit', '-f', 'json', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse results
                if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                    output = json.loads(result.stdout)
                    issues = output.get('results', [])
                    
                    detected = len(issues) > 0
                    vulnerability_types = [
                        issue.get('test_id', '')
                        for issue in issues
                    ]
                    
                    # Calculate confidence based on severity
                    if issues:
                        severities = [i.get('issue_severity', 'LOW') for i in issues]
                        confidence = sum(
                            1.0 if s == 'HIGH' else 0.7 if s == 'MEDIUM' else 0.3
                            for s in severities
                        ) / len(severities)
                    else:
                        confidence = 0.0
                    
                    results.append(BaselineResult(
                        sample_id=sample.id,
                        detected=detected,
                        vulnerability_types=vulnerability_types,
                        confidence=confidence,
                        execution_time=time.time() - start_time
                    ))
                else:
                    results.append(BaselineResult(
                        sample_id=sample.id,
                        detected=False,
                        vulnerability_types=[],
                        confidence=0.0,
                        execution_time=time.time() - start_time,
                        error=f"Bandit failed with code {result.returncode}"
                    ))
                
                # Clean up temp file
                Path(temp_file).unlink()
                
            except Exception as e:
                logger.error(f"Error in Bandit baseline for {sample.id}: {e}")
                results.append(BaselineResult(
                    sample_id=sample.id,
                    detected=False,
                    vulnerability_types=[],
                    confidence=0.0,
                    execution_time=time.time() - start_time,
                    error=str(e)
                ))
        
        return results
    
    def _run_semgrep_baseline(self, samples: List[Any]) -> List[BaselineResult]:
        """
        Run Semgrep static analysis baseline.
        
        Args:
            samples: List of benchmark samples
            
        Returns:
            List of BaselineResult objects
        """
        logger.info("Running Semgrep baseline")
        
        results = []
        for sample in tqdm(samples, desc="Semgrep baseline"):
            start_time = time.time()
            
            try:
                # Write code to temporary file
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.py',
                    delete=False
                ) as f:
                    f.write(sample.code)
                    temp_file = f.name
                
                # Run Semgrep with security rules
                result = subprocess.run(
                    [
                        'semgrep',
                        '--config', 'auto',
                        '--json',
                        temp_file
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Parse results
                if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                    output = json.loads(result.stdout)
                    issues = output.get('results', [])
                    
                    detected = len(issues) > 0
                    vulnerability_types = [
                        issue.get('check_id', '')
                        for issue in issues
                    ]
                    
                    # Calculate confidence based on severity
                    if issues:
                        severities = [
                            i.get('extra', {}).get('severity', 'INFO')
                            for i in issues
                        ]
                        confidence = sum(
                            1.0 if s == 'ERROR' else 0.7 if s == 'WARNING' else 0.3
                            for s in severities
                        ) / len(severities)
                    else:
                        confidence = 0.0
                    
                    results.append(BaselineResult(
                        sample_id=sample.id,
                        detected=detected,
                        vulnerability_types=vulnerability_types,
                        confidence=confidence,
                        execution_time=time.time() - start_time
                    ))
                else:
                    results.append(BaselineResult(
                        sample_id=sample.id,
                        detected=False,
                        vulnerability_types=[],
                        confidence=0.0,
                        execution_time=time.time() - start_time,
                        error=f"Semgrep failed with code {result.returncode}"
                    ))
                
                # Clean up temp file
                Path(temp_file).unlink()
                
            except Exception as e:
                logger.error(f"Error in Semgrep baseline for {sample.id}: {e}")
                results.append(BaselineResult(
                    sample_id=sample.id,
                    detected=False,
                    vulnerability_types=[],
                    confidence=0.0,
                    execution_time=time.time() - start_time,
                    error=str(e)
                ))
        
        return results
    
    def _compare_results(
        self,
        securecodai: List[Any],
        deepseek: List[BaselineResult],
        bandit: List[BaselineResult],
        semgrep: List[BaselineResult]
    ) -> Dict[str, Any]:
        """
        Compare results across all systems.
        
        Args:
            securecodai: SecureCodeAI results
            deepseek: DeepSeek baseline results
            bandit: Bandit baseline results
            semgrep: Semgrep baseline results
            
        Returns:
            Dictionary of comparison metrics
        """
        total = len(securecodai)
        
        # Calculate detection rates
        securecodai_detected = sum(1 for r in securecodai if r.detected)
        deepseek_detected = sum(1 for r in deepseek if r.detected)
        bandit_detected = sum(1 for r in bandit if r.detected)
        semgrep_detected = sum(1 for r in semgrep if r.detected)
        
        # Calculate average execution times
        securecodai_time = sum(r.execution_time for r in securecodai) / total
        deepseek_time = sum(r.execution_time for r in deepseek) / total
        bandit_time = sum(r.execution_time for r in bandit) / total
        semgrep_time = sum(r.execution_time for r in semgrep) / total
        
        return {
            "detection_rates": {
                "securecodai": securecodai_detected / total,
                "deepseek_zeroshot": deepseek_detected / total,
                "bandit": bandit_detected / total,
                "semgrep": semgrep_detected / total
            },
            "avg_execution_times": {
                "securecodai": securecodai_time,
                "deepseek_zeroshot": deepseek_time,
                "bandit": bandit_time,
                "semgrep": semgrep_time
            },
            "total_samples": total,
            "results": {
                "securecodai": [vars(r) for r in securecodai],
                "deepseek": [vars(r) for r in deepseek],
                "bandit": [vars(r) for r in bandit],
                "semgrep": [vars(r) for r in semgrep]
            }
        }
    
    def _save_comparison(self, comparison: Dict[str, Any]):
        """
        Save comparison results.
        
        Args:
            comparison: Comparison dictionary
        """
        output_file = self.output_dir / "baseline_comparison.json"
        with open(output_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        logger.info(f"Saved baseline comparison to {output_file}")
