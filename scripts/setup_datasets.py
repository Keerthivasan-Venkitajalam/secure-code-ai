#!/usr/bin/env python3
"""
Download/Setup datasets for full evaluation.
1. PySecDB from GitHub.
2. CyberSecEval 3 from Hugging Face (saved locally).
"""

import os
import requests
import zipfile
import io
import json
from datasets import load_dataset
import shutil

# Configuration
PYSECDB_URL = "https://github.com/SunLab-GMU/PySecDB/archive/refs/heads/main.zip"
TARGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "toy_seccode", "secure_code_data")
HF_TOKEN = "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" # From user's notebook

def setup_dirs():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"✅ Created directory: {TARGET_DIR}")

def download_pysecdb():
    print(f"⬇️  Downloading PySecDB from {PYSECDB_URL}...")
    try:
        r = requests.get(PYSECDB_URL)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        # Extract to TARGET_DIR
        z.extractall(TARGET_DIR)
        print("✅ PySecDB Download and extraction complete.")
        
        # Rename/Move if needed to have a clean path
        extracted_folder = os.path.join(TARGET_DIR, "PySecDB-main")
        if os.path.exists(extracted_folder):
            print(f"   Located at: {extracted_folder}")
    except Exception as e:
        print(f"❌ Error downloading PySecDB: {e}")

def download_cse3():
    print("⬇️  Downloading CyberSecEval (walledai) using pandas...")
    try:
        import pandas as pd
        splits = {'python': 'autocomplete/python-00000-of-00001.parquet'}
        
        # Load directly from HF via pandas
        df = pd.read_parquet("hf://datasets/walledai/CyberSecEval/" + splits["python"])
        
        output_path = os.path.join(TARGET_DIR, "cse3_full.jsonl")
        print(f"   Saving {len(df)} examples to {output_path}...")
        df.to_json(output_path, orient="records", lines=True)
        print("✅ CSE3 Download complete.")
        
    except Exception as e:
        print(f"❌ Error downloading/saving CSE3: {e}")

if __name__ == "__main__":
    setup_dirs()
    download_pysecdb()
    download_cse3()
