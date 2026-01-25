#!/usr/bin/env python3
"""
Evaluate SecureCodeAI on CyberSecEval 3 dataset.
"""

import argparse
import os
import json
import requests
from datasets import load_dataset
from tqdm import tqdm

from huggingface_hub import InferenceClient

class QwenInference:
    """Wrapper for Qwen model via Hugging Face Inference API."""

    def __init__(self, token: str = "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", model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"):
        self.model_name = model_name
        self.client = InferenceClient(token=token)
        print(f"🔧 Using Hugging Face Inference: {self.model_name}")

    def generate_completion(self, prompt: str, max_tokens: int = 512) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat_completion(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as exc:
            return ""

def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - CyberSecEval 3 Evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of examples")
    parser.add_argument("--output", type=str, default="cse3_predictions.jsonl", help="Output file")
    
    args = parser.parse_args()
    
    # Load dataset
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "toy_seccode", "secure_code_data", "cse3_full.jsonl")
    
    print(f"🚀 Loading CyberSecEval dataset...")
    if os.path.exists(local_path):
        print(f"   📂 Found local file: {local_path}")
        dataset = load_dataset("json", data_files=local_path, split="train")
        print(f"   ✅ Loaded {len(dataset)} examples.")
    else:
        print("   ⚠️ Local file not found. Trying Hugging Face...")
        try:
             dataset = load_dataset("facebook/cyber-seceval-3", split="test")
        except:
             dataset = load_dataset("facebook/cyber-seceval-2", split="test")

    if args.limit:
        dataset = dataset.select(range(args.limit))
        print(f"⚠️ Limiting to first {args.limit} examples")

    llm = QwenInference()
    
    results = []
    
    for example in tqdm(dataset, desc="Evaluating"):
        # Field names depend on the dataset structure. 
        # CyberSecEval usually has 'prompt' or 'test_case_prompt'
        prompt = example.get("prompt") or example.get("test_case_prompt") or example.get("input")
        if not prompt:
            continue
            
        completion = llm.generate_completion(prompt)
        
        results.append({
            "prompt": prompt,
            "completion": completion,
            "model": "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        })
        
    print(f"💾 Saving results to {args.output}")
    with open(args.output, "w") as f:
        for res in results:
            f.write(json.dumps(res) + "\n")
            
    print("✅ Done!")

if __name__ == "__main__":
    main()
