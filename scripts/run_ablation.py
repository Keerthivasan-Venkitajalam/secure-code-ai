#!/usr/bin/env python3
"""
Run ablation study: With vs Without Symbolic Feedback.
"""

import argparse
import glob
import os
import sys
import time
import json
import re
from typing import Dict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "poc"))

try:
    from poc.neuro_slicing import NeuroSlicingEngine
except ImportError:
    print("Error importing NeuroSlicingEngine. Run from scripts/ directory or set PYTHONPATH.")
    sys.exit(1)

def run_vanilla_llm(engine: NeuroSlicingEngine, code: str, vuln_type: str) -> Dict:
    """Run Vanilla LLM approach (Just generate patch, no symbolic verification loop)."""
    start_time = time.time()
    
    # 1. Ask for vulnerability
    prompt_analyze = f"""You are a security engineer. Analyze this code for {vuln_type}.
Code:
```python
{code}
```
Is it vulnerable? If so, explain briefly."""
    
    analysis = engine._generate(prompt_analyze)
    
    # 2. Ask for patch
    prompt_patch = f"""You are a security engineer. Fix the {vuln_type} in this code.
Code:
```python
{code}
```
Analysis: {analysis}

Output ONLY the fixed code."""
    
    patch = engine._generate(prompt_patch)
    
    # Extract code
    code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', patch, re.DOTALL)
    if code_match:
        patch_code = code_match.group(1).strip()
    else:
        patch_code = patch.strip()
        
    execution_time = time.time() - start_time
    
    return {
        "mode": "vanilla_llm",
        "vulnerable": "Yes" in analysis or "vulnerable" in analysis.lower(), # Weak heuristic
        "patch": patch_code,
        "time": execution_time
    }

def run_neuro_symbolic(engine: NeuroSlicingEngine, code: str, vuln_type: str) -> Dict:
    """Run Neuro-Symbolic approach (Slicing + Contract + Symbolic Verify Loop)."""
    # This uses the existing analyze_and_patch method which prints a lot.
    # We capture the return dict.
    return engine.analyze_and_patch(code, vulnerability_type=vuln_type)

def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - Ablation Study")
    parser.add_argument("--dir", type=str, default="toy_seccode", help="Directory with test files")
    parser.add_argument("--limit", type=int, default=5, help="Number of files to test per mode")
    parser.add_argument("--output", type=str, default="ablation_results.json", help="Output file")
    
    args = parser.parse_args()
    
    pattern = os.path.join(args.dir, "verify_PySecDB-*.py")
    files = glob.glob(pattern)
    if not files:
        files = glob.glob("verify_PySecDB-*.py")
    
    # Filter for CMD_INJECTION or SQL_INJECTION as they are best supported by the PoC
    files = [f for f in files if "CMD_INJECTION" in f or "SQL_INJECTION" in f]
    
    if args.limit:
        files = files[:args.limit]
        
    print(f"🔬 Running ablation on {len(files)} files...")
    
    engine = NeuroSlicingEngine(use_4bit=True) 
    
    results = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"\nProcessing {filename}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            
        vuln_type = "Command Injection" if "CMD_INJECTION" in filename else "SQL Injection"
        
        # Run Vanilla
        print(">>> Mode: Vanilla LLM")
        res_vanilla = run_vanilla_llm(engine, code, vuln_type)
        res_vanilla["file"] = filename
        results.append(res_vanilla)
        
        # Run Neuro-Symbolic
        print(">>> Mode: Neuro-Symbolic")
        # Reuse engine
        res_neuro = run_neuro_symbolic(engine, code, vuln_type)
        res_neuro["mode"] = "neuro_symbolic"
        res_neuro["file"] = filename
        results.append(res_neuro)
        
    print(f"💾 Saving results to {args.output}")
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
        
    print("✅ Ablation complete!")

if __name__ == "__main__":
    main()
