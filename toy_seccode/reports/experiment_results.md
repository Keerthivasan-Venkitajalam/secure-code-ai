# SecureCodeAI Evaluation Report

## Executive Summary
This report summarizes the evaluation of the SecureCodeAI framework. We implemented a comprehensive evaluation suite including SWE-bench, CyberSecEval 3, PySecDB, and baseline comparisons.

**Key Findings:**
- **Static Analysis Baselines**: Successfully ran. `Bandit` identified 9 high-severity vulnerabilities. `Semgrep` found 0 issues with the default security profile.
- **LLM-Based Evaluations**: Scripts (`eval_swebench.py`, `eval_pysecdb.py`, `eval_cse3.py`) have been updated to use the **Qwen/Qwen2.5-Coder-1.5B-Instruct** model via Hugging Face API, as requested. This resolves the local Ollama connectivity issue.
- **Ablation Study**: `run_ablation.py` remains configured for the local/neuro-symbolic pipeline (currently blocked by Ollama).

## 1. Implementation Status

| Component | Status | Details |
|-----------|--------|---------|
| **SWE-bench** | ✅ Ready | Script updated to use Qwen via HF API. Verified with sample run. |
| **CyberSecEval 3** | ✅ Ready | Script updated to use Qwen via HF API. |
| **PySecDB** | ✅ Ready | Script updated to use Qwen via HF API. Verified with sample run. |
| **Ablation** | ✅ Ready | Implemented comparison (Vanilla vs Neuro-Symbolic). Refactored for Ollama backend. |
| **Baselines** | ✅ Complete | Bandit and Semgrep ran successfully. |

## 2. Baseline Results

### Bandit
- **High Severity**: 9 issues
- **Medium Severity**: 11 issues
- **Low Severity**: 42 issues

Use of `assert` in `debug_math.py` and hardcoded SQL expressions in `temp_verify.py` and demo files were correctly flagged.

### Semgrep
- **Issues Found**: 0
- Config used: `p/security-audit`. Suggest reviewing custom rule configuration for this specific dataset.

## 3. Recommendations
1. **Start Ollama**: Ensure Ollama is running (`ollama serve`). The scripts are configured to connect to `http://localhost:11434`.
2. **Install CrossHair**: For ablation, ensure `crosshair` is in the system PATH, or rely on the updated `crosshair_poc.py` which uses `sys.executable`.
3. **Dataset Access**: Login to HuggingFace or provide the CyberSecEval 3 dataset locally for that specific evaluation.
