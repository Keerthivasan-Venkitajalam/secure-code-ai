# RunPod Serverless Account Setup Guide

This guide walks you through setting up a RunPod Serverless account for deploying SecureCodeAI.

## Prerequisites

- Valid email address
- Credit card for billing setup
- GitHub account (optional, for OAuth login)

## Step 1: Create RunPod Account

1. **Visit RunPod Website**
   - Go to https://www.runpod.io/
   - Click "Sign Up" or "Get Started"

2. **Choose Sign-Up Method**
   - Option A: Sign up with email and password
   - Option B: Sign up with GitHub OAuth (recommended for developers)

3. **Verify Email**
   - Check your email for verification link
   - Click the link to verify your account
   - Log in to your new RunPod account

## Step 2: Configure API Keys

1. **Navigate to API Keys Section**
   - Log in to RunPod dashboard
   - Click on your profile icon (top right)
   - Select "Settings" or "API Keys"

2. **Create New API Key**
   - Click "Create API Key" or "+ New API Key"
   - Give it a descriptive name: `SecureCodeAI-Production`
   - Set permissions: `Read` and `Write` (required for deployment)
   - Click "Create"

3. **Save API Key Securely**
   - Copy the API key immediately (it won't be shown again)
   - Store it in a secure location (password manager recommended)
   - **NEVER commit API keys to version control**

4. **Configure Environment Variable**
   ```bash
   # Add to your .env file (DO NOT commit this file)
   RUNPOD_API_KEY=your_api_key_here
   ```

5. **Test API Key**
   ```bash
   # Test the API key with a simple request
   curl -X GET "https://api.runpod.io/v2/user" \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

## Step 3: Set Up Billing

1. **Navigate to Billing Section**
   - From dashboard, click "Billing" or "Payment Methods"
   - Click "Add Payment Method"

2. **Add Credit Card**
   - Enter credit card details
   - Billing address
   - Click "Save" or "Add Card"

3. **Set Spending Limits (Recommended)**
   - Navigate to "Spending Limits" or "Budget Alerts"
   - Set daily/monthly spending limits to avoid unexpected charges
   - Recommended starting limit: $50/month
   - Enable email alerts for spending thresholds

4. **Review Pricing**
   - Serverless pricing: Pay per second of GPU usage
   - Typical costs for SecureCodeAI:
     - Cold start: ~$0.01-0.02 per request
     - Warm request: ~$0.005-0.01 per request
     - Idle time: $0 (scales to zero)
   - Estimated monthly cost: $20-100 depending on usage

5. **Enable Auto-Recharge (Optional)**
   - Set minimum balance threshold
   - Auto-recharge amount
   - This prevents service interruption

## Step 4: Verify Account Setup

1. **Check Account Status**
   - Ensure account is "Active"
   - Verify payment method is added
   - Confirm API key is created

2. **Review Quotas and Limits**
   - Check your account tier (Free/Paid)
   - Review GPU availability
   - Note any rate limits

3. **Test Serverless Endpoint Creation**
   ```bash
   # Test creating a simple endpoint (we'll delete it after)
   curl -X POST "https://api.runpod.io/v2/endpoints" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "test-endpoint",
       "image": "runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel",
       "gpu_type": "NVIDIA RTX A4000",
       "min_workers": 0,
       "max_workers": 1
     }'
   ```

## Configuration Files

### .env File Template

Create `deployment/.env` (DO NOT commit):

```bash
# RunPod Configuration
RUNPOD_API_KEY=your_api_key_here
RUNPOD_ENDPOINT_ID=  # Will be populated after deployment

# Deployment Settings
MIN_WORKERS=0
MAX_WORKERS=3
GPU_TYPE=NVIDIA RTX A4000
SCALE_TO_ZERO_TIMEOUT=300  # 5 minutes

# API Configuration
API_KEY_SECRET=your_secure_api_key_for_clients
RATE_LIMIT_PER_MINUTE=60

# Monitoring
SENTRY_DSN=  # Optional, for error tracking
```

### Save API Key to Environment

**For Linux/Mac:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export RUNPOD_API_KEY="your_api_key_here"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

**For Windows (PowerShell):**
```powershell
# Add to PowerShell profile
$env:RUNPOD_API_KEY = "your_api_key_here"

# Or set permanently
[System.Environment]::SetEnvironmentVariable('RUNPOD_API_KEY', 'your_api_key_here', 'User')
```

## Security Best Practices

1. **API Key Security**
   - Never commit API keys to Git
   - Use environment variables or secret managers
   - Rotate keys periodically (every 90 days)
   - Use separate keys for dev/staging/production

2. **Access Control**
   - Limit API key permissions to minimum required
   - Use separate keys for different services
   - Monitor API key usage regularly

3. **Billing Protection**
   - Set spending limits
   - Enable budget alerts
   - Review usage weekly
   - Set up auto-scaling limits

4. **Monitoring**
   - Enable logging for all API calls
   - Set up alerts for unusual activity
   - Monitor deployment health

## Troubleshooting

### Issue: API Key Not Working

**Solution:**
- Verify key was copied correctly (no extra spaces)
- Check key permissions include Read and Write
- Ensure key hasn't been revoked
- Try creating a new key

### Issue: Payment Method Declined

**Solution:**
- Verify card details are correct
- Check with your bank for international transactions
- Try a different payment method
- Contact RunPod support

### Issue: Cannot Create Endpoint

**Solution:**
- Verify account is fully activated
- Check billing is set up correctly
- Ensure you have available quota
- Try a different GPU type

### Issue: Spending Limit Reached

**Solution:**
- Review current usage in dashboard
- Adjust spending limits if needed
- Optimize deployment to reduce costs
- Consider upgrading account tier

## Next Steps

After completing this setup:

1. ✅ Account created and verified
2. ✅ API key generated and saved securely
3. ✅ Billing configured with spending limits
4. ✅ Environment variables configured

You're now ready to proceed to:
- **Task 3.2**: Deploy Docker image to RunPod
- **Task 3.3**: Configure auto-scaling

## Support Resources

- **RunPod Documentation**: https://docs.runpod.io/
- **RunPod Discord**: https://discord.gg/runpod
- **RunPod Support**: support@runpod.io
- **API Reference**: https://docs.runpod.io/reference/api

## Cost Estimation Tool

Use this to estimate your monthly costs:

```python
# deployment/estimate_costs.py
def estimate_monthly_cost(
    avg_requests_per_day: int,
    avg_processing_time_seconds: float,
    cost_per_second: float = 0.0002  # RTX A4000 rate
):
    """Estimate monthly RunPod costs."""
    daily_cost = avg_requests_per_day * avg_processing_time_seconds * cost_per_second
    monthly_cost = daily_cost * 30
    
    print(f"Estimated Daily Cost: ${daily_cost:.2f}")
    print(f"Estimated Monthly Cost: ${monthly_cost:.2f}")
    
    return monthly_cost

# Example usage
estimate_monthly_cost(
    avg_requests_per_day=100,
    avg_processing_time_seconds=30
)
```

## Checklist

Before proceeding to deployment, verify:

- [ ] RunPod account created and email verified
- [ ] API key generated and saved securely
- [ ] API key added to environment variables
- [ ] Payment method added and verified
- [ ] Spending limits configured
- [ ] Budget alerts enabled
- [ ] API key tested with simple request
- [ ] `.env` file created (and added to `.gitignore`)
- [ ] Security best practices reviewed

---

**Status**: Ready for deployment once all checklist items are complete.
