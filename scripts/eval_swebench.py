#!/usr/bin/env python3
"""
Evaluate SecureCodeAI on SWE-bench dataset.
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

    def generate_patch(self, problem_statement: str, codebase_context: str = "", max_tokens: int = 1024) -> str:
        prompt = f"""You are an Expert Software Engineer and Security Researcher. You are given a problem description and a codebase context.
        
Your task is to generate a patch to resolve the issue described.

Problem Description:
{problem_statement}

Codebase Context:
{codebase_context}

Please provide the patch in unified diff format.
"""

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
            return f"Error contacting Hugging Face: {exc}"

def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - SWE-bench Evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of problems to evaluate")
    parser.add_argument("--output", type=str, default="swebench_predictions.jsonl", help="Output file for predictions")
    parser.add_argument("--split", type=str, default="dev", help="Dataset split to use (dev/test)")
    
    args = parser.parse_args()
    
    print(f"🚀 Loading SWE-bench dataset (split={args.split})...")
    dataset = load_dataset("princeton-nlp/SWE-bench", split=args.split)
    
    if args.limit:
        dataset = dataset.select(range(args.limit))
        print(f"⚠️ Limiting to first {args.limit} examples")

    llm = QwenInference()
    
    predictions = []
    
    for example in tqdm(dataset, desc="Generating patches"):
        instance_id = example["instance_id"]
        problem_statement = example["problem_statement"]
        
        # In a real scenario, we might retrieve relevant files. 
        # For this baseline, we'll try to use the provided 'text' or just the problem statement
        # SWE-bench typically requires retrieval. Here is a simplified 0-shot pass.
        
        patch_prediction = llm.generate_patch(problem_statement)
        
        predictions.append({
            "instance_id": instance_id,
            "model_patch": patch_prediction,
            "model_name_or_path": "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        })
        
    print(f"💾 Saving predictions to {args.output}")
    with open(args.output, "w") as f:
        for pred in predictions:
            f.write(json.dumps(pred) + "\n")
            
    print("✅ Done!")

if __name__ == "__main__":
    main()
