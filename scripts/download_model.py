#!/usr/bin/env python3
"""
Download and cache DeepSeek-Coder-V2-Lite model weights.
Run this once to pre-download the model (saves time on first inference).
"""

import sys
import os
from pathlib import Path

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
except ImportError:
    print("Error: transformers not installed. Run: pip install transformers torch")
    sys.exit(1)


def download_model(model_name: str = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"):
    """
    Download DeepSeek model weights to Hugging Face cache.
    
    Args:
        model_name: Model identifier on Hugging Face Hub
    """
    print(f"🚀 Downloading model: {model_name}")
    print(f"📦 This will download ~32GB of model weights")
    print(f"💾 Cache location: {Path.home() / '.cache' / 'huggingface'}")
    print()
    
    # Check available disk space
    cache_dir = Path.home() / ".cache" / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download tokenizer (small, ~5MB)
        print("📥 Step 1/2: Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        print("✅ Tokenizer downloaded successfully")
        print()
        
        # Download model weights (large, ~32GB)
        print("📥 Step 2/2: Downloading model weights...")
        print("⏳ This may take 10-30 minutes depending on your internet speed...")
        
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,  # Use FP16 to save space
            low_cpu_mem_usage=True,  # Optimize memory during download
        )
        
        print("✅ Model weights downloaded successfully")
        print()
        print(f"🎉 All done! Model cached at: {cache_dir}")
        print()
        print("Next steps:")
        print("  1. Run: python poc/llm_poc.py")
        print("  2. Or: python poc/neuro_slicing.py")
        
        # Clean up model from memory
        del model
        del tokenizer
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        print()
        print("Troubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Ensure you have ~50GB free disk space")
        print("  3. Try again - downloads are resumable")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download DeepSeek model weights")
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        help="Model name on Hugging Face Hub"
    )
    
    args = parser.parse_args()
    
    success = download_model(args.model)
    sys.exit(0 if success else 1)
