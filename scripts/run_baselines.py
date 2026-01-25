#!/usr/bin/env python3
"""
Run baselines (Bandit, Semgrep) on the dataset.
"""

import argparse
import subprocess
import json
import os
import sys

def run_bandit(target_dir: str, output_file: str):
    print(f"🚀 Running Bandit on {target_dir}...")
    cmd = [
        "bandit",
        "-r", target_dir,
        "-f", "json",
        "-o", output_file,
        "-q"  # quiet
    ]
    try:
        subprocess.run(cmd, check=False) # Bandit returns exit code 1 if issues found
        print(f"✅ Bandit finished. Results in {output_file}")
    except FileNotFoundError:
        print("❌ Bandit not found in path.")

def run_semgrep(target_dir: str, output_file: str):
    print(f"🚀 Running Semgrep on {target_dir}...")
    cmd = [
        "semgrep",
        "--config=p/security-audit",
        target_dir,
        "--json",
        "-o", output_file,
        "--quiet"
    ]
    try:
        subprocess.run(cmd, check=False)
        print(f"✅ Semgrep finished. Results in {output_file}")
    except FileNotFoundError:
        print("❌ Semgrep not found in path.")

def parse_bandit_results(file_path: str):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        # Bandit structure: 'results': [{'issue_severity': 'HIGH', ...}]
        high = sum(1 for r in data.get("results", []) if r["issue_severity"] == "HIGH")
        medium = sum(1 for r in data.get("results", []) if r["issue_severity"] == "MEDIUM")
        print(f"Bandit Findings: {high} High, {medium} Medium")
    except Exception as e:
        print(f"Error parsing Bandit results: {e}")

def parse_semgrep_results(file_path: str):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        # Semgrep structure: 'results': [{'extra': {'severity': 'ERROR', ...}}]
        # Severity mapping might be needed.
        count = len(data.get("results", []))
        print(f"Semgrep Findings: {count} issues")
    except Exception as e:
        print(f"Error parsing Semgrep results: {e}")

def main():
    parser = argparse.ArgumentParser(description="SecureCodeAI - Baselines")
    parser.add_argument("--dir", type=str, default="toy_seccode", help="Directory to scan")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.dir):
        print(f"Directory {args.dir} not found.")
        sys.exit(1)
        
    run_bandit(args.dir, "bandit_results.json")
    parse_bandit_results("bandit_results.json")
    
    print("-" * 30)
    
    run_semgrep(args.dir, "semgrep_results.json")
    parse_semgrep_results("semgrep_results.json")

if __name__ == "__main__":
    main()
