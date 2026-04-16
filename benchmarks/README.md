# Benchmark Evaluation Infrastructure

This module provides comprehensive benchmark evaluation for SecureCodeAI, including:

- **CyberSecEval 3**: Autocomplete benchmark for vulnerability detection
- **PySecDB**: Real-world CVE-mapped vulnerability evaluation
- **Baseline Comparisons**: Compare against DeepSeek (zero-shot), Bandit, and Semgrep
- **Metrics Collection**: Detection rate, precision, F1, patch validity, code churn
- **Report Generation**: Plots, LaTeX tables, and markdown reports

Latest published snapshot: [PUBLISHED_RESULTS.md](PUBLISHED_RESULTS.md)

## Quick Start

```python
from benchmarks import BenchmarkEvaluator
from api.client import SecureCodeAIClient

# Initialize client
client = SecureCodeAIClient(base_url="http://localhost:8000")

# Create evaluator
evaluator = BenchmarkEvaluator(
    api_client=client,
    output_dir="results"
)

# Run full evaluation
results = evaluator.run_full_evaluation(
    benchmarks=['cyberseceval3', 'pysecdb'],
    include_baselines=True,
    max_samples=100  # Limit for testing
)
```

## Running Individual Benchmarks

### CyberSecEval 3

```python
result = evaluator.run_cyberseceval(
    include_baselines=True,
    max_samples=50
)

print(f"Detection Rate: {result.metrics.detection_rate:.2%}")
print(f"Patch Validity: {result.metrics.patch_validity_rate:.2%}")
```

### PySecDB

```python
result = evaluator.run_pysecdb(
    include_baselines=True,
    max_samples=50
)

print(f"CVE Detection Rate: {result.metrics.detection_rate:.2%}")
```

## Output Structure

```
results/
├── cyberseceval3/
│   ├── results.json
│   └── metrics.json
├── pysecdb/
│   ├── results.json
│   └── metrics.json
├── baselines/
│   └── baseline_comparison.json
├── metrics/
│   ├── cyberseceval3_metrics.csv
│   ├── cyberseceval3_metrics.json
│   ├── cyberseceval3_summary.txt
│   ├── pysecdb_metrics.csv
│   ├── pysecdb_metrics.json
│   └── pysecdb_summary.txt
└── reports/
    ├── CYBERSECEVAL3_RESULTS.md
    ├── PYSECDB_RESULTS.md
    ├── COMBINED_RESULTS.md
    ├── cyberseceval3_detection_rates.png
    ├── cyberseceval3_execution_times.png
    ├── cyberseceval3_combined.png
    ├── cyberseceval3_table.tex
    └── ...
```

## Metrics Collected

### Detection Metrics
- Detection Rate (Recall)
- Precision
- F1 Score
- False Positive Rate
- False Negative Rate

### Patch Metrics
- Patch Generation Rate
- Patch Validity Rate
- Patch Correctness Rate

### Code Quality Metrics
- Average Code Churn (lines changed)
- Average Patch Size (characters)

### Performance Metrics
- Average Execution Time
- Total Samples Evaluated

## Baseline Systems

1. **DeepSeek Zero-Shot**: Pure LLM without symbolic execution
2. **Bandit**: Python static analysis tool
3. **Semgrep**: Multi-language static analysis

## Dataset Setup

### CyberSecEval 3

Place the dataset in `data/cyberseceval3/autocomplete_benchmark.json`:

```json
[
  {
    "id": "sample_001",
    "code": "import pickle\ndata = pickle.loads(user_input)",
    "vulnerability_type": "insecure_deserialization",
    "language": "python",
    "expected_vulnerability": true,
    "metadata": {"severity": "high"}
  }
]
```

### PySecDB

Place the dataset in `data/pysecdb/vulnerabilities.json`:

```json
[
  {
    "id": "pysec_001",
    "cve_id": "CVE-2023-XXXX",
    "vulnerable_code": "import yaml\nconfig = yaml.load(user_input)",
    "vulnerability_type": "unsafe_deserialization",
    "language": "python",
    "severity": "high",
    "description": "Unsafe YAML deserialization",
    "patched_code": "import yaml\nconfig = yaml.safe_load(user_input)",
    "metadata": {"package": "pyyaml"}
  }
]
```

## Mock Data

If datasets are not available, the system will automatically use mock data for testing.

## Requirements

- `matplotlib>=3.5.0` - For plot generation
- `numpy>=1.21.0` - For numerical operations
- `tqdm>=4.66.0` - For progress bars
- `bandit>=1.7.5` - For static analysis baseline
- `semgrep>=1.50.0` - For static analysis baseline

## Example: Running from Command Line

Create a script `run_benchmarks.py`:

```python
#!/usr/bin/env python3
import logging
from benchmarks import BenchmarkEvaluator
from api.client import SecureCodeAIClient

logging.basicConfig(level=logging.INFO)

# Initialize
client = SecureCodeAIClient(base_url="http://localhost:8000")
evaluator = BenchmarkEvaluator(client)

# Run evaluation
results = evaluator.run_full_evaluation(
    benchmarks=['cyberseceval3'],
    include_baselines=True
)

print("Evaluation complete! Check results/ directory for outputs.")
```

Run with:
```bash
python run_benchmarks.py
```

## Troubleshooting

### Bandit/Semgrep Not Found

Install static analysis tools:
```bash
pip install bandit semgrep
```

### Dataset Not Found

The system will use mock data automatically. To use real datasets, place them in the `data/` directory as described above.

### API Connection Error

Ensure the SecureCodeAI API is running:
```bash
cd api
uvicorn server:app --reload
```

## Contributing

To add a new benchmark:

1. Create a new runner class in `benchmarks/your_benchmark.py`
2. Implement `load_dataset()` and `run_benchmark()` methods
3. Add integration to `BenchmarkEvaluator`
4. Update this README

## License

See main project LICENSE file.
