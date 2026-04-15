#!/usr/bin/env python3
"""
RunPod Cost Estimation Tool

Estimate monthly costs for SecureCodeAI deployment on RunPod Serverless.
"""

from typing import Dict


# GPU pricing (per second) - as of 2026
GPU_PRICING = {
    "NVIDIA RTX A4000": 0.00020,
    "NVIDIA RTX A5000": 0.00025,
    "NVIDIA RTX A6000": 0.00030,
    "NVIDIA A40": 0.00035,
    "NVIDIA A100 40GB": 0.00050,
    "NVIDIA A100 80GB": 0.00070,
}


def estimate_monthly_cost(
    avg_requests_per_day: int,
    avg_processing_time_seconds: float,
    gpu_type: str = "NVIDIA RTX A4000",
    cold_start_percentage: float = 0.1,
    cold_start_time_seconds: float = 30,
) -> Dict[str, float]:
    """
    Estimate monthly RunPod costs.
    
    Args:
        avg_requests_per_day: Average number of requests per day
        avg_processing_time_seconds: Average processing time per request
        gpu_type: GPU type to use
        cold_start_percentage: Percentage of requests that are cold starts (0.0-1.0)
        cold_start_time_seconds: Time for cold start initialization
    
    Returns:
        Dictionary with cost breakdown
    """
    if gpu_type not in GPU_PRICING:
        raise ValueError(f"Unknown GPU type: {gpu_type}. Available: {list(GPU_PRICING.keys())}")
    
    cost_per_second = GPU_PRICING[gpu_type]
    
    # Calculate warm requests
    warm_requests = avg_requests_per_day * (1 - cold_start_percentage)
    warm_cost_per_request = avg_processing_time_seconds * cost_per_second
    warm_daily_cost = warm_requests * warm_cost_per_request
    
    # Calculate cold start requests
    cold_requests = avg_requests_per_day * cold_start_percentage
    cold_cost_per_request = (cold_start_time_seconds + avg_processing_time_seconds) * cost_per_second
    cold_daily_cost = cold_requests * cold_cost_per_request
    
    # Total costs
    daily_cost = warm_daily_cost + cold_daily_cost
    monthly_cost = daily_cost * 30
    yearly_cost = daily_cost * 365
    
    # Cost per request
    avg_cost_per_request = daily_cost / avg_requests_per_day if avg_requests_per_day > 0 else 0
    
    return {
        "gpu_type": gpu_type,
        "cost_per_second": cost_per_second,
        "avg_requests_per_day": avg_requests_per_day,
        "avg_processing_time": avg_processing_time_seconds,
        "warm_requests_per_day": warm_requests,
        "cold_requests_per_day": cold_requests,
        "warm_daily_cost": warm_daily_cost,
        "cold_daily_cost": cold_daily_cost,
        "daily_cost": daily_cost,
        "monthly_cost": monthly_cost,
        "yearly_cost": yearly_cost,
        "cost_per_request": avg_cost_per_request,
    }


def print_cost_estimate(results: Dict[str, float]):
    """Print cost estimate in a readable format."""
    print("=" * 60)
    print("RunPod Cost Estimation")
    print("=" * 60)
    print()
    print(f"GPU Type: {results['gpu_type']}")
    print(f"Cost per second: ${results['cost_per_second']:.5f}")
    print()
    print("Usage Assumptions:")
    print(f"  Average requests per day: {results['avg_requests_per_day']:.0f}")
    print(f"  Average processing time: {results['avg_processing_time']:.1f}s")
    print(f"  Warm requests per day: {results['warm_requests_per_day']:.0f}")
    print(f"  Cold start requests per day: {results['cold_requests_per_day']:.0f}")
    print()
    print("Cost Breakdown:")
    print(f"  Warm requests daily cost: ${results['warm_daily_cost']:.2f}")
    print(f"  Cold start daily cost: ${results['cold_daily_cost']:.2f}")
    print()
    print("Estimated Costs:")
    print(f"  Daily: ${results['daily_cost']:.2f}")
    print(f"  Monthly: ${results['monthly_cost']:.2f}")
    print(f"  Yearly: ${results['yearly_cost']:.2f}")
    print()
    print(f"Cost per request: ${results['cost_per_request']:.4f}")
    print("=" * 60)


def compare_gpu_types(
    avg_requests_per_day: int,
    avg_processing_time_seconds: float,
):
    """Compare costs across different GPU types."""
    print("=" * 60)
    print("GPU Type Comparison")
    print("=" * 60)
    print()
    
    results = []
    for gpu_type in GPU_PRICING.keys():
        estimate = estimate_monthly_cost(
            avg_requests_per_day,
            avg_processing_time_seconds,
            gpu_type
        )
        results.append(estimate)
    
    # Sort by monthly cost
    results.sort(key=lambda x: x['monthly_cost'])
    
    print(f"{'GPU Type':<25} {'Monthly Cost':<15} {'Per Request':<15}")
    print("-" * 60)
    for result in results:
        print(f"{result['gpu_type']:<25} ${result['monthly_cost']:<14.2f} ${result['cost_per_request']:<14.4f}")
    print()


def main():
    """Run example cost estimations."""
    print("\n")
    
    # Example 1: Low usage (development/testing)
    print("Example 1: Low Usage (Development/Testing)")
    results = estimate_monthly_cost(
        avg_requests_per_day=50,
        avg_processing_time_seconds=30,
        gpu_type="NVIDIA RTX A4000",
        cold_start_percentage=0.3,  # 30% cold starts
    )
    print_cost_estimate(results)
    print("\n")
    
    # Example 2: Medium usage (small production)
    print("Example 2: Medium Usage (Small Production)")
    results = estimate_monthly_cost(
        avg_requests_per_day=200,
        avg_processing_time_seconds=30,
        gpu_type="NVIDIA RTX A4000",
        cold_start_percentage=0.1,  # 10% cold starts
    )
    print_cost_estimate(results)
    print("\n")
    
    # Example 3: High usage (production)
    print("Example 3: High Usage (Production)")
    results = estimate_monthly_cost(
        avg_requests_per_day=1000,
        avg_processing_time_seconds=30,
        gpu_type="NVIDIA RTX A5000",
        cold_start_percentage=0.05,  # 5% cold starts
    )
    print_cost_estimate(results)
    print("\n")
    
    # GPU comparison
    print("GPU Type Comparison (200 requests/day, 30s processing)")
    compare_gpu_types(
        avg_requests_per_day=200,
        avg_processing_time_seconds=30,
    )
    print("\n")
    
    # Tips
    print("=" * 60)
    print("Cost Optimization Tips")
    print("=" * 60)
    print()
    print("1. Scale to Zero: Set MIN_WORKERS=0 to avoid idle costs")
    print("2. Optimize Processing: Reduce avg_processing_time with:")
    print("   - Model quantization (AWQ/GPTQ)")
    print("   - Smaller context windows")
    print("   - Batch processing")
    print("3. Reduce Cold Starts:")
    print("   - Increase SCALE_TO_ZERO_TIMEOUT")
    print("   - Use health check pings during peak hours")
    print("4. Choose Right GPU:")
    print("   - RTX A4000: Best for development/low usage")
    print("   - RTX A5000: Good balance for production")
    print("   - A100: Only if you need maximum performance")
    print("5. Monitor Usage:")
    print("   - Set spending alerts")
    print("   - Review usage weekly")
    print("   - Adjust limits as needed")
    print("=" * 60)


if __name__ == "__main__":
    main()
