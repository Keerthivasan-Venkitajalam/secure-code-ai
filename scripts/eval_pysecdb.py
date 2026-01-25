#!/usr/bin/env python3
"""
Evaluate SecureCodeAI on local PySecDB files.
"""

import argparse
import glob
import os
import json
import re
import requests
from tqdm import tqdm

from huggingface_hub import InferenceClient

class QwenInference:
    """Wrapper for Qwen model via Hugging Face Inference API."""

    def __init__(self, token: str = "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", model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"):
        self.model_name = model_name
        self.client = InferenceClient(token=token)
        print(f"🔧 Using Hugging Face Inference: {self.model_name}")

    def analyze_vulnerability(self, code: str) -> str:
        prompt = f"""You are a Security Researcher. Analyze the following code for vulnerabilities.

Code:
```python
{code}
```

List any vulnerabilities found. Be concise.
"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat_completion(
                model=self.model_name,
                messages=messages,
                max_tokens=2048,
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as exc:
            return ""

def extract_vulnerability_label(content: str) -> str:
    """Extract vulnerability type from comments like '# VULNERABLE: OS Command Injection'"""
    match = re.search(r"#\s*VULNERABLE:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return "Unknown"

def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - PySecDB Evaluation")
    parser.add_argument("--dir", type=str, default="toy_seccode", help="Directory containing verify_PySecDB-*.py files")
    parser.add_argument("--output", type=str, default="pysecdb_predictions.jsonl", help="Output file")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files")

    args = parser.parse_args()
    
    # Find files in the downloaded PySecDB directory
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "toy_seccode", "secure_code_data", "PySecDB-main")
    
    files = []
    print(f"🔍 Scanning {dataset_dir} for vulnerabilities...")
    
    if os.path.exists(dataset_dir):
        for root, _, filenames in os.walk(dataset_dir):
            for filename in filenames:
                # PySecDB often organizes by CVE/vuln type
                # We want to process python files or specific metadata
                # For this script, we'll look for .py files that aren't tests/setup
                if filename.endswith(".py") and "test" not in filename and "setup" not in filename:
                    files.append(os.path.join(root, filename))
    else:
        print(f"⚠️  Dataset directory not found: {dataset_dir}")
        # Fallback to local toy files
        pattern = os.path.join(args.dir, "verify_PySecDB-*.py")
        files = glob.glob(pattern)
        if not files:
            files = glob.glob("verify_PySecDB-*.py")

    print(f"found {len(files)} files to scan.")
    
    if args.limit:
        files = files[:args.limit]
        
    llm = QwenInference()
    results = []
    
    for file_path in tqdm(files, desc="Evaluating"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        ground_truth_vuln = extract_vulnerability_label(content)
        
        # Simple extraction of the function or code block
        # We'll just pass the whole file content for now as context is small
        
        analysis = llm.analyze_vulnerability(content)
        
        results.append({
            "file": os.path.basename(file_path),
            "ground_truth": ground_truth_vuln,
            "model_analysis": analysis,
            "model": "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        })
        
    print(f"💾 Saving results to {args.output}")
    with open(args.output, "w") as f:
        for res in results:
            f.write(json.dumps(res) + "\n")
            
    print("✅ Done!")

if __name__ == "__main__":
    main()
