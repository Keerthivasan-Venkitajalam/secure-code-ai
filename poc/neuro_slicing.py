#!/usr/bin/env python3
"""
SecureCodeAI - Proof of Concept: Neuro-Slicing
Demonstrates LLM-guided code slicing to mitigate symbolic execution path explosion.
This is the core innovation of the neuro-symbolic approach.
"""

import argparse
import os
import re
from typing import Dict, Optional, Tuple

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
except ImportError:
    print("Error: Missing dependencies. Install with: pip install transformers torch accelerate bitsandbytes")
    exit(1)

from crosshair_poc import CrossHairVerifier, VerificationResult


class NeuroSlicingEngine:
    """LLM-guided code slicing and contract generation for symbolic execution."""
    
    def __init__(self, model_name: str = "deepseek-coder-v2-lite-instruct", use_4bit: bool = True, use_ollama: bool = True):
        """Initialize with DeepSeek model (Ollama or Transformers)."""
        print(f"🔧 Initializing Neuro-Slicing Engine...")
        
        self.use_ollama = use_ollama
        self.model_name = model_name
        
        if self.use_ollama:
            self.api_url = os.environ.get("OLLAMA_API", "http://localhost:11434/api/generate")
            print(f"🔧 Using Ollama backend: {self.model_name}")
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            
            if use_4bit:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                )
            print(f"✅ Model loaded (Transformers)")
        
        # Initialize CrossHair verifier
        self.verifier = CrossHairVerifier(timeout=30)
    
    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate LLM response."""
        if self.use_ollama:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096,
                },
            }
            try:
                import requests
                resp = requests.post(self.api_url, json=payload, timeout=300)
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
                return f"Error: {resp.text}"
            except Exception as e:
                return f"Error contacting Ollama: {e}"
        
        # Fallback to transformers
        messages = [{"role": "user", "content": prompt}]
        
        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.2,  # Low temperature for precise code generation
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        return response.strip()
    
    def extract_vulnerability_slice(self, full_code: str, vulnerability_type: str = "SQL Injection") -> str:
        """
        Step 1: Extract relevant code slice for the vulnerability.
        This reduces symbolic execution search space.
        """
        prompt = f"""You are a security engineer. Extract ONLY the minimal code slice relevant to detecting {vulnerability_type}.

Rules:
1. Include only the vulnerable function and its direct dependencies
2. Remove unrelated functions, imports, and logic
3. Keep variable names and function signatures intact
4. Output ONLY the code, no explanations

Full Code:
```python
{full_code}
```

Minimal Vulnerability Slice:"""

        response = self._generate(prompt, max_tokens=512)
        
        # Extract code from response
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        else:
            # If no code block found, return the response as-is
            return response.strip()
    
    def generate_security_contract(self, code_slice: str, vulnerability_type: str = "SQL Injection") -> str:
        """
        Step 2: Generate formal icontract contract for the vulnerability.
        This provides the specification for symbolic execution.
        """
        prompt = f"""You are a Formal Methods Engineer. Generate a Python icontract decorator to detect {vulnerability_type}.

Requirements:
1. Use @icontract.ensure() for postconditions (check function output)
2. Use @icontract.require() for preconditions (check function input)
3. Contract should catch malicious inputs that exploit the vulnerability
4. Output ONLY the decorator code, no explanations

Code to protect:
```python
{code_slice}
```

icontract Contract:"""

        response = self._generate(prompt, max_tokens=256)
        
        # Extract contract code
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            contract = code_match.group(1).strip()
        else:
            contract = response.strip()
        
        # Ensure contract has @icontract decorator
        if '@icontract' not in contract:
            # Fallback: basic SQL injection contract
            if 'SQL' in vulnerability_type:
                contract = """@icontract.ensure(lambda result: "'" not in str(result) or str(result).count("'") <= 2)
@icontract.ensure(lambda result: "--" not in str(result))"""
            else:
                contract = "@icontract.ensure(lambda result: result is not None)"
        
        return contract
    
    def generate_patch(self, code_slice: str, counterexample: str, vulnerability_type: str) -> str:
        """
        Step 3: Generate a security patch based on the counterexample.
        """
        prompt = f"""You are a security engineer. Fix the {vulnerability_type} vulnerability in this code.

Vulnerable Code:
```python
{code_slice}
```

Exploit Found by Symbolic Execution:
{counterexample}

Generate a SECURE version of the code that prevents this exploit.
Output ONLY the fixed code, no explanations.

Fixed Code:"""

        response = self._generate(prompt, max_tokens=512)
        
        # Extract code
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        else:
            return response.strip()
    
    def analyze_and_patch(self, full_code: str, vulnerability_type: str = "SQL Injection") -> Dict:
        """
        Complete neuro-symbolic pipeline:
        1. LLM extracts vulnerability slice (Neuro-Slicing)
        2. LLM generates formal contract (Hypothesis Generation)
        3. CrossHair verifies code (Symbolic Execution)
        4. If vulnerable, LLM generates patch (Patching)
        5. CrossHair verifies patch (Verification Loop)
        """
        print(f"\n{'='*70}")
        print(f"NEURO-SYMBOLIC PIPELINE: {vulnerability_type}")
        print(f"{'='*70}\n")
        
        # Step 1: Extract vulnerability slice
        print("📍 Step 1: LLM-Guided Code Slicing...")
        code_slice = self.extract_vulnerability_slice(full_code, vulnerability_type)
        print(f"✅ Extracted slice ({len(code_slice)} chars, reduced from {len(full_code)} chars)")
        print(f"\nCode Slice:\n{code_slice}\n")
        
        # Step 2: Generate security contract
        print("📍 Step 2: LLM Contract Generation...")
        contract = self.generate_security_contract(code_slice, vulnerability_type)
        print(f"✅ Generated contract")
        print(f"\nContract:\n{contract}\n")
        
        # Step 3: Verify with CrossHair
        print("📍 Step 3: Symbolic Execution (Pre-Patch)...")
        pre_patch_result = self.verifier.verify_code_with_contract(code_slice, contract)
        print(f"✅ Verification complete ({pre_patch_result.execution_time:.2f}s)")
        
        if not pre_patch_result.verified and pre_patch_result.counterexample:
            print(f"\n⚠️  VULNERABILITY CONFIRMED!")
            print(f"Counterexample:\n{pre_patch_result.counterexample}\n")
            
            # Step 4: Generate patch
            print("📍 Step 4: LLM Patch Generation...")
            patched_code = self.generate_patch(code_slice, pre_patch_result.counterexample, vulnerability_type)
            print(f"✅ Patch generated")
            print(f"\nPatched Code:\n{patched_code}\n")
            
            # Step 5: Verify patch
            print("📍 Step 5: Symbolic Execution (Post-Patch)...")
            post_patch_result = self.verifier.verify_code_with_contract(patched_code, contract)
            print(f"✅ Verification complete ({post_patch_result.execution_time:.2f}s)")
            
            if post_patch_result.verified:
                print(f"\n✅ PATCH VERIFIED! Vulnerability eliminated.")
            else:
                print(f"\n⚠️  Patch verification failed. Iterative refinement needed.")
            
            return {
                "vulnerable": True,
                "code_slice": code_slice,
                "contract": contract,
                "counterexample": pre_patch_result.counterexample,
                "patch": patched_code,
                "patch_verified": post_patch_result.verified,
                "total_time": pre_patch_result.execution_time + post_patch_result.execution_time
            }
        else:
            print(f"\n✅ No vulnerability detected (or verification error)")
            return {
                "vulnerable": False,
                "code_slice": code_slice,
                "contract": contract,
                "error": pre_patch_result.error_message
            }


def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - Neuro-Slicing PoC")
    parser.add_argument("--file", type=str, help="Path to Python file to analyze")
    parser.add_argument("--vuln-type", type=str, default="SQL Injection", help="Vulnerability type to detect")
    parser.add_argument("--no-quantization", action="store_true", help="Disable 4-bit quantization")
    
    args = parser.parse_args()
    
    # Load code
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r') as f:
            code = f.read()
    else:
        # Default example: SQL injection in a Flask app
        code = '''import sqlite3
from flask import Flask, request

app = Flask(__name__)

def get_user_by_name(username):
    """Fetch user from database by username."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: SQL injection via string concatenation
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

@app.route('/user/<username>')
def user_profile(username):
    user = get_user_by_name(username)
    if user:
        return f"User: {user[1]}, Email: {user[2]}"
    return "User not found"

def create_user(username, email, password):
    """Create new user in database."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Also vulnerable
    query = f"INSERT INTO users (username, email, password) VALUES ('{username}', '{email}', '{password}')"
    cursor.execute(query)
    
    conn.commit()
    conn.close()
'''
        print("📝 Using default example (Flask SQL injection vulnerability)")
    
    print("\n" + "="*70)
    print("FULL CODE:")
    print("="*70)
    print(code)
    print("="*70)
    
    # Initialize neuro-slicing engine
    engine = NeuroSlicingEngine(use_4bit=not args.no_quantization, use_ollama=True)
    
    # Run analysis
    result = engine.analyze_and_patch(code, vulnerability_type=args.vuln_type)
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Vulnerability Type: {args.vuln_type}")
    print(f"Vulnerable: {result.get('vulnerable', False)}")
    if result.get('vulnerable'):
        print(f"Patch Generated: Yes")
        print(f"Patch Verified: {result.get('patch_verified', False)}")
        print(f"Total Execution Time: {result.get('total_time', 0):.2f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
