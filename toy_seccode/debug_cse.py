from datasets import get_dataset_config_names, load_dataset
import os

dataset_id = "walledai/CyberSecEval"

try:
    print(f"Inspecting configs for {dataset_id}...")
    configs = get_dataset_config_names(dataset_id)
    print(f"Configs found: {configs}")
    
    if configs:
        target_config = configs[0]
        print(f"Trying to load config: {target_config}")
        ds = load_dataset(dataset_id, target_config, split="train")
        print(f"Success! Rows: {len(ds)}")
    else:
        print("No configs found. Trying default...")
        ds = load_dataset(dataset_id, split="train")
        print(f"Success! Rows: {len(ds)}")

except Exception as e:
    print(f"Error: {e}")
