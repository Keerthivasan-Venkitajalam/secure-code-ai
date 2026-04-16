# Published Benchmark Snapshot

This file publishes the latest reproducible benchmark snapshot for the repository.

## Run Metadata

- Date: 2026-04-16
- Command: `./.venv/bin/python benchmarks/example_usage.py`
- Dataset mode: mock fallback samples (dataset directories were not present)
- Samples per benchmark: 3

## CyberSecEval 3 (Mock Sample)

- Detection Rate (Recall): 100.00%
- Precision: 100.00%
- F1 Score: 100.00%
- Patch Generation Rate: 66.67%
- Patch Validity Rate: 0.00%
- Average Execution Time: 0.00s

## PySecDB (Mock Sample)

- Detection Rate (Recall): 100.00%
- Precision: 100.00%
- F1 Score: 100.00%
- Patch Generation Rate: 66.67%
- Patch Validity Rate: 50.00%
- Average Execution Time: 0.00s

## Caveats

- These values come from mock fallback data, not full benchmark corpora.
- During the run, Bandit CLI was not installed in PATH, so static-analysis augmentation was skipped.
- For production-quality benchmark claims, run with real datasets under `data/cyberseceval3` and `data/pysecdb` and publish those outputs.
