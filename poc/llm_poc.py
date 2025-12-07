#!/usr/bin/env python3
"""
SecureCodeAI - Proof of Concept: LLM Inference
Tests DeepSeek-Coder-V2-Lite local inference for vulnerability hypothesis generation.
"""

import argparse
import os
import json
import requests


class DeepSeekInference:
    """Wrapper that calls local Ollama instead of loading transformers weights."""

    def __init__(self, model_name: str = "deepseek-coder-v2-lite-instruct", **_: object):
        self.model_name = model_name
        self.api_url = os.environ.get("OLLAMA_API", "http://localhost:11434/api/generate")
        print(f"🔧 Using Ollama model: {self.model_name}")
        print(f"🔧 Endpoint: {self.api_url}")

    def generate_vulnerability_hypothesis(self, code: str, max_tokens: int = 512) -> str:
        prompt = f"""You are a Formal Methods Engineer and Security Researcher. Analyze the following code for security vulnerabilities.

For each potential vulnerability:
1. Identify the specific line(s) of code
2. Describe the vulnerability type (e.g., SQL Injection, XSS, Buffer Overflow)
3. Explain the exploit scenario
4. Suggest a formal precondition that would prevent the vulnerability

Code to analyze:
```python
{code}
```

Analysis:"""

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 1024,
                "num_gpu": 0,
                "num_thread": 4,
            },
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=300)
            if resp.status_code != 200:
                return f"Ollama error {resp.status_code}: {resp.text}"
            data = resp.json()
            return data.get("response", "")
        except Exception as exc:
            return f"Error contacting Ollama: {exc}"


def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - LLM PoC")
    parser.add_argument("--code", type=str, help="Code snippet to analyze (inline)")
    parser.add_argument("--file", type=str, help="Path to Python file to analyze")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate")
    
    args = parser.parse_args()
    
    # Get code from file or inline argument
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ Error: File not found: {args.file}")
            return
        with open(args.file, 'r') as f:
            code = f.read()
    elif args.code:
        code = args.code
    else:
        # Default example: SQL injection vulnerability
        code = '''def login_user(username, password):
    """Authenticate user with database."""
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Vulnerable SQL query
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None
'''
        print("📝 Using default example (SQL injection vulnerability)")
    
    print("\n" + "="*70)
    print("CODE TO ANALYZE:")
    print("="*70)
    print(code)
    print("="*70 + "\n")
    
    # Initialize model client (Ollama)
    print("🚨 Using local Ollama model (no transformers load)...")
    llm = DeepSeekInference()
    print("✅ Client ready, sending request...\n")
    
    # Generate vulnerability analysis
    print("🔍 Analyzing code for vulnerabilities...\n")
    analysis = llm.generate_vulnerability_hypothesis(code, max_tokens=args.max_tokens)
    
    print("="*70)
    print("VULNERABILITY ANALYSIS:")
    print("="*70)
    print(analysis)
    print("="*70)


if __name__ == "__main__":
    main()
