# Scripts Reference

This reference describes operational scripts in `scripts/`.

## Startup Scripts

- `scripts/start_api_local.ps1`: Start API on Windows with standard flow
- `scripts/start_api_no_angr.ps1`: Start API on Windows with `SKIP_ANGR=true`
- `scripts/start_local.ps1`: Start local stack on Windows
- `scripts/start_local.sh`: Start local stack on Linux/macOS
- `scripts/start_ollama.bat`: Start Ollama service on Windows

## Semantic Stack Scripts

- `scripts/migrate_knowledge_base.py`: Import/validate bug-pattern CSV into repo format
- `scripts/rebuild_vector_store.py`: Rebuild vector store from knowledge base
- `scripts/validate_integration.py`: Validate semantic components and validators end-to-end

## Testing and Verification

- `scripts/run_full_test_suite.py`: Run consolidated test workflow
- `scripts/test_local_setup.ps1`: Validate local setup endpoints and extension prerequisites
- `scripts/test_runpod_deployment.sh`: Deployment checks for RunPod flow
- `scripts/run_load_test.ps1`: Load test helper (Windows)
- `scripts/run_load_test.sh`: Load test helper (Linux/macOS)
- `scripts/run_performance_benchmark.py`: Benchmark runtime performance

## Evaluation and Baselines

- `scripts/run_baselines.py`: Run baseline scanners
- `scripts/run_ablation.py`: Run ablation experiments
- `scripts/eval_cse3.py`: Evaluate on CSE3 dataset
- `scripts/eval_pysecdb.py`: Evaluate on PySecDB dataset
- `scripts/eval_swebench.py`: Evaluate on SWE-bench subset

## Environment and Data Setup

- `scripts/setup_conda.ps1`: Conda setup (Windows)
- `scripts/setup_conda.sh`: Conda setup (Linux/macOS)
- `scripts/setup_datasets.py`: Download and prepare datasets
- `scripts/download_model.py`: Download model assets
- `scripts/force_download.py`: Force model re-download and verification
- `scripts/cleanup_envs.ps1`: Clean up local conda environments

## Quick Command Set

Windows semantic setup:

```powershell
python scripts\migrate_knowledge_base.py --source ..\Agentic-Bug-Hunter\samples.csv --dest data\knowledge_base\samples.csv --validate
python scripts\rebuild_vector_store.py --knowledge-base data\knowledge_base\samples.csv --vector-store data\vector_store --embedding-model BAAI/bge-base-en-v1.5
python scripts\validate_integration.py --knowledge-base data\knowledge_base\samples.csv --vector-store data\vector_store --embedding-model BAAI/bge-base-en-v1.5
```

Linux/macOS semantic setup:

```bash
python scripts/migrate_knowledge_base.py --source ../Agentic-Bug-Hunter/samples.csv --dest data/knowledge_base/samples.csv --validate
python scripts/rebuild_vector_store.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
python scripts/validate_integration.py --knowledge-base data/knowledge_base/samples.csv --vector-store data/vector_store --embedding-model BAAI/bge-base-en-v1.5
```
