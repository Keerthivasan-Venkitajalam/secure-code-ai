#!/usr/bin/env python3
"""
Validate RunPod account setup and configuration.

This script checks:
1. API key is configured
2. API key is valid
3. Account has billing set up
4. Can access RunPod API
"""

import os
import sys
import requests
from typing import Dict, Tuple


def check_api_key_env() -> Tuple[bool, str]:
    """Check if RUNPOD_API_KEY environment variable is set."""
    api_key = os.getenv("RUNPOD_API_KEY")
    if not api_key:
        return False, " RUNPOD_API_KEY environment variable not set"
    if len(api_key) < 20:
        return False, " RUNPOD_API_KEY appears to be invalid (too short)"
    return True, f" RUNPOD_API_KEY is set ({api_key[:8]}...)"


def validate_api_key(api_key: str) -> Tuple[bool, str, Dict]:
    """Validate API key by making a test request to RunPod API."""
    try:
        response = requests.get(
            "https://api.runpod.io/v2/user",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return True, " API key is valid", user_data
        elif response.status_code == 401:
            return False, " API key is invalid or expired", {}
        else:
            return False, f" Unexpected response: {response.status_code}", {}
    except requests.exceptions.RequestException as e:
        return False, f" Network error: {str(e)}", {}


def check_billing_status(api_key: str) -> Tuple[bool, str]:
    """Check if billing is configured."""
    try:
        response = requests.get(
            "https://api.runpod.io/v2/user/billing",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        if response.status_code == 200:
            billing_data = response.json()
            has_payment = billing_data.get("hasPaymentMethod", False)
            if has_payment:
                return True, " Billing is configured"
            else:
                return False, "  No payment method found"
        else:
            return False, f"  Could not verify billing status (status: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, f"  Could not check billing: {str(e)}"


def check_gpu_availability(api_key: str) -> Tuple[bool, str]:
    """Check available GPU types."""
    try:
        response = requests.get(
            "https://api.runpod.io/v2/gpus",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        
        if response.status_code == 200:
            gpus = response.json()
            if gpus:
                gpu_names = [gpu.get("name", "Unknown") for gpu in gpus[:3]]
                return True, f" Available GPUs: {', '.join(gpu_names)}"
            else:
                return False, "  No GPUs available"
        else:
            return False, f"  Could not check GPU availability (status: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, f"  Could not check GPUs: {str(e)}"


def check_env_file() -> Tuple[bool, str]:
    """Check if .env file exists in deployment directory."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        return True, f" .env file exists at {env_path}"
    else:
        return False, f"  .env file not found at {env_path}"


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("RunPod Account Setup Validation")
    print("=" * 60)
    print()
    
    all_passed = True
    
    # Check 1: Environment variable
    print("1. Checking environment variable...")
    passed, message = check_api_key_env()
    print(f"   {message}")
    if not passed:
        print()
        print("   To fix: Set RUNPOD_API_KEY environment variable")
        print("   export RUNPOD_API_KEY='your_api_key_here'")
        all_passed = False
        # Can't continue without API key
        print()
        print("=" * 60)
        print(" Validation failed. Please set up API key first.")
        print("=" * 60)
        sys.exit(1)
    print()
    
    api_key = os.getenv("RUNPOD_API_KEY")
    
    # Check 2: API key validity
    print("2. Validating API key...")
    passed, message, user_data = validate_api_key(api_key)
    print(f"   {message}")
    if passed and user_data:
        print(f"   User ID: {user_data.get('id', 'N/A')}")
        print(f"   Email: {user_data.get('email', 'N/A')}")
    if not passed:
        all_passed = False
        print()
        print("   To fix: Generate a new API key in RunPod dashboard")
        print("   https://www.runpod.io/console/user/settings")
    print()
    
    # Check 3: Billing status
    print("3. Checking billing configuration...")
    passed, message = check_billing_status(api_key)
    print(f"   {message}")
    if not passed:
        all_passed = False
        print()
        print("   To fix: Add payment method in RunPod dashboard")
        print("   https://www.runpod.io/console/user/billing")
    print()
    
    # Check 4: GPU availability
    print("4. Checking GPU availability...")
    passed, message = check_gpu_availability(api_key)
    print(f"   {message}")
    if not passed:
        print()
        print("   Note: This may be temporary. Check RunPod status page.")
    print()
    
    # Check 5: .env file
    print("5. Checking .env file...")
    passed, message = check_env_file()
    print(f"   {message}")
    if not passed:
        print()
        print("   To fix: Create .env file from .env.example")
        print("   cp deployment/.env.example deployment/.env")
    print()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print(" All checks passed! RunPod setup is complete.")
        print()
        print("Next steps:")
        print("  1. Review deployment/RUNPOD_ACCOUNT_SETUP.md")
        print("  2. Proceed to Task 3.2: Deploy Docker image to RunPod")
    else:
        print("  Some checks failed. Please review the messages above.")
        print()
        print("For help, see: deployment/RUNPOD_ACCOUNT_SETUP.md")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
