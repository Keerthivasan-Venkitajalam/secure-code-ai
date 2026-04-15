# RunPod Account Setup Checklist

Use this checklist to track your progress through Task 3.1.

## Pre-Setup

- [ ] Read `RUNPOD_ACCOUNT_SETUP.md` guide
- [ ] Have credit card ready for billing
- [ ] Have secure password manager ready for API key storage

## Account Creation

- [ ] Visit https://www.runpod.io/
- [ ] Click "Sign Up" or "Get Started"
- [ ] Choose sign-up method (email or GitHub OAuth)
- [ ] Complete registration form
- [ ] Verify email address
- [ ] Log in to RunPod dashboard

## API Key Configuration

- [ ] Navigate to Settings → API Keys
- [ ] Click "Create API Key"
- [ ] Name: `SecureCodeAI-Production`
- [ ] Set permissions: Read + Write
- [ ] Copy API key immediately
- [ ] Save API key in password manager
- [ ] Add API key to environment variable:
  ```bash
  export RUNPOD_API_KEY="your_api_key_here"
  ```
- [ ] Create `deployment/.env` from `deployment/.env.example`
- [ ] Add API key to `deployment/.env` file
- [ ] Verify `.env` is in `.gitignore`

## Billing Setup

- [ ] Navigate to Billing → Payment Methods
- [ ] Click "Add Payment Method"
- [ ] Enter credit card details
- [ ] Enter billing address
- [ ] Save payment method
- [ ] Set spending limit: $50/month (recommended)
- [ ] Enable budget alerts
- [ ] Configure alert thresholds:
  - [ ] 50% of budget
  - [ ] 80% of budget
  - [ ] 100% of budget

## Validation

- [ ] Run validation script:
  ```bash
  cd secure-code-ai/deployment
  python validate_runpod_setup.py
  ```
- [ ] All checks pass ✅
- [ ] API key is valid
- [ ] Billing is configured
- [ ] GPUs are available

## Security

- [ ] API key stored securely (not in code)
- [ ] `.env` file added to `.gitignore`
- [ ] Spending limits configured
- [ ] Budget alerts enabled
- [ ] Reviewed security best practices

## Documentation

- [ ] Documented API key location (for team)
- [ ] Shared spending limit policy (if team project)
- [ ] Noted GPU type preferences
- [ ] Recorded account owner/admin

## Next Steps

Once all items are checked:

- [ ] Mark Task 3.1 as complete
- [ ] Proceed to Task 3.2: Deploy Docker image to RunPod
- [ ] Review `RUNPOD_DEPLOYMENT.md` for deployment steps

## Troubleshooting

If you encounter issues:

1. **API Key Not Working**
   - Verify no extra spaces when copying
   - Check permissions include Read + Write
   - Try creating a new key

2. **Payment Declined**
   - Verify card details
   - Check for international transaction blocks
   - Contact your bank
   - Try alternative payment method

3. **Cannot Access Dashboard**
   - Clear browser cache
   - Try incognito/private mode
   - Try different browser
   - Contact RunPod support

## Support

- **Documentation**: https://docs.runpod.io/
- **Discord**: https://discord.gg/runpod
- **Email**: support@runpod.io

## Estimated Time

- Account creation: 5 minutes
- API key setup: 5 minutes
- Billing setup: 10 minutes
- Validation: 5 minutes
- **Total**: ~25 minutes

---

**Status**: ⬜ Not Started | 🔄 In Progress | ✅ Complete

Current Status: 🔄 In Progress
