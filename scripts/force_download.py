#!/usr/bin/env python3
"""Force download DeepSeek model with verification."""

from huggingface_hub import snapshot_download
import os

print("🔧 Force downloading DeepSeek-Coder-V2-Lite-Instruct...")
print("⚠️  This will download ~32 GB of model weights")
print("⏳ Expected time: 10-30 minutes depending on internet speed\n")

model_id = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"

try:
    # Force re-download with verification
    cache_dir = snapshot_download(
        repo_id=model_id,
        resume_download=True,
        force_download=False,  # Don't re-download if already complete
        local_files_only=False,
    )
    
    print(f"\n✅ Model downloaded successfully!")
    print(f"📁 Location: {cache_dir}")
    
    # Verify files exist
    import glob
    safetensors_files = glob.glob(os.path.join(cache_dir, "*.safetensors"))
    print(f"\n📦 Found {len(safetensors_files)} safetensors files:")
    
    total_size = 0
    for f in safetensors_files:
        size_gb = os.path.getsize(f) / (1024**3)
        total_size += size_gb
        print(f"  - {os.path.basename(f)}: {size_gb:.2f} GB")
    
    print(f"\n📊 Total size: {total_size:.2f} GB")
    
    if total_size < 1.0:
        print("\n⚠️  WARNING: Model files are too small - download may have failed!")
    else:
        print("\n✅ Model files verified - ready to use!")

except Exception as e:
    print(f"\n❌ Error downloading model: {e}")
    print("\nTroubleshooting:")
    print("1. Check internet connection")
    print("2. Verify ~50 GB free disk space")
    print("3. Try running with: python scripts/force_download.py")
