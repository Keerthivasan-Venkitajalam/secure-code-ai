# RunPod Quick Start Guide

## 5-Minute Setup

### 1. Create Account (2 min)
```
1. Visit: https://www.runpod.io/
2. Click "Sign Up"
3. Use email or GitHub
4. Verify email
```

### 2. Get API Key (1 min)
```
1. Dashboard → Settings → API Keys
2. Create new: "SecureCodeAI-Production"
3. Permissions: Read + Write
4. Copy key immediately
```

### 3. Configure Environment (1 min)
```bash
# Set environment variable
export RUNPOD_API_KEY="your_key_here"

# Create .env file
cp deployment/.env.example deployment/.env
# Edit and add your API key
```

### 4. Set Up Billing (1 min)
```
1. Dashboard → Billing → Payment Methods
2. Add credit card
3. Set limit: $50/month
4. Enable alerts
```

### 5. Validate (30 sec)
```bash
python deployment/validate_runpod_setup.py
```

## Expected Costs

| Usage Level | Requests/Day | Monthly Cost |
|-------------|--------------|--------------|
| Development | 50           | $11.70       |
| Small Prod  | 200          | $39.60       |
| Production  | 1000         | $236.25      |

## Security Checklist

- [ ] API key in password manager
- [ ] `.env` file created
- [ ] `.env` in `.gitignore`
- [ ] Spending limit set
- [ ] Budget alerts enabled

## Validation Output

When setup is correct:
```
✅ RUNPOD_API_KEY is set
✅ API key is valid
✅ Billing is configured
✅ GPUs are available
✅ .env file exists
```

## Next Steps

1. ✅ Complete this setup
2. ➡️ Task 3.2: Deploy Docker image
3. 📖 Read: `RUNPOD_DEPLOYMENT.md`

## Quick Commands

```bash
# Validate setup
python deployment/validate_runpod_setup.py

# Estimate costs
python deployment/estimate_costs.py

# Check environment
echo $RUNPOD_API_KEY

# View checklist
cat deployment/RUNPOD_SETUP_CHECKLIST.md
```

## Support

- 📖 Full Guide: `RUNPOD_ACCOUNT_SETUP.md`
- ✅ Checklist: `RUNPOD_SETUP_CHECKLIST.md`
- 🌐 Docs: https://docs.runpod.io/
- 💬 Discord: https://discord.gg/runpod

---

**Total Time**: ~5 minutes  
**Cost**: $12-40/month for typical usage
