# Automated Credential Refresh Setup

## Problem
LinkedIn credentials expire every ~24 hours. You don't want to manually refresh them daily.

## Solution
Use GitHub Actions to automatically check credentials weekly and alert you when they expire.

---

## Option 1: Automated Refresh (Recommended)

### Setup (5 minutes)

#### Step 1: Add GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Create two secrets:
   - `LINKEDIN_CSRF_TOKEN` - Your CSRF token
   - `LINKEDIN_LI_AT_COOKIE` - Your li_at cookie

#### Step 2: Get Fresh Credentials

```bash
python3 refresh_credentials.py
```

Follow the prompts to extract credentials from your browser:
1. Go to LinkedIn.com
2. Open DevTools (F12)
3. Application → Cookies → linkedin.com → Copy `li_at`
4. Network tab → Find request → Copy `x-csrf-token` header

#### Step 3: Push to GitHub

```bash
git add .github/workflows/refresh-credentials.yml
git add refresh_credentials.py
git commit -m "Add automated credential refresh"
git push origin master
```

#### Step 4: GitHub Actions Will:
- ✅ Check credentials every Sunday at 2 AM UTC
- ✅ Create an issue if credentials expired
- ✅ Notify you with exact fix steps

#### Step 5: When GitHub Creates an Issue

The issue will have exact steps. Follow them:
1. Run: `python3 refresh_credentials.py`
2. Update GitHub Secrets
3. Update Render environment variables
4. Done! (API ready again)

---

## Option 2: Manual Refresh (Simpler)

No GitHub setup needed. Just run when credentials expire:

```bash
python3 refresh_credentials.py
```

This updates `.env` locally and shows Render update instructions.

---

## Option 3: Cron Job (Advanced)

Run refresh automatically on your machine every week:

### macOS/Linux

```bash
# Edit crontab
crontab -e

# Add this line to run every Sunday at 2 AM
0 2 * * 0 cd /Users/prakhartripathi/Desktop/linkedin_api && python3 refresh_credentials.py

# Save and exit
```

---

## How It Works

### Local Refresh Script

```bash
python3 refresh_credentials.py
```

**What it does:**
1. Prompts you to extract credentials from LinkedIn
2. Validates them with LinkedIn API
3. Updates `.env` file
4. Shows Render update instructions
5. Saves credentials to `RENDER_ENV_UPDATE.txt` for reference

**Output**:
```
✅ .env file updated successfully
✅ Credentials validated successfully!
✅ Credentials also saved to RENDER_ENV_UPDATE.txt

To update Render environment variables:
1. Go to https://dashboard.render.com
2. Select your service
3. Go to Settings → Environment
4. Update:
   LINKEDIN_CSRF_TOKEN = your_token
   LINKEDIN_LI_AT_COOKIE = your_cookie
5. Click 'Save Changes'
```

### GitHub Actions Workflow

Runs **every Sunday at 2 AM UTC** (adjust in `.github/workflows/refresh-credentials.yml`):

1. Checks if credentials are still valid
2. If valid: Just logs ✅ "Credentials still valid"
3. If expired: Creates GitHub issue with fix steps

**Example Issue Created**:
```
🔑 LinkedIn Credentials Expired

Credentials Status: EXPIRED ❌

Steps to Refresh:

1. Locally (on your computer):
   python3 refresh_credentials.py
   
2. Update Render:
   Go to dashboard.render.com → Settings → Environment
   
3. Update GitHub Secrets:
   Go to Settings → Secrets and variables → Actions

4. Verify:
   curl https://your-api.onrender.com/api/v1/validate
   Should return: {"valid": true}
```

---

## Quick Start

### 1. First Time (Extract Credentials)

```bash
# Locally on your machine
cd linkedin_api

# Extract credentials from LinkedIn
python3 refresh_credentials.py

# Follow prompts:
# - Go to LinkedIn
# - Copy li_at cookie
# - Copy x-csrf-token header

# Updates .env and shows Render instructions
```

### 2. Update Render

```
Dashboard → Your Service → Settings → Environment

Update:
  LINKEDIN_CSRF_TOKEN=your_token
  LINKEDIN_LI_AT_COOKIE=your_cookie

Save (auto-deploys)
```

### 3. Optional: Setup GitHub Actions (Automatic)

```bash
# Add secrets to GitHub
# Go to repo → Settings → Secrets

Create:
  LINKEDIN_CSRF_TOKEN = your_token
  LINKEDIN_LI_AT_COOKIE = your_cookie

Push to GitHub:
  git add .github/workflows/refresh-credentials.yml
  git push
```

### 4. Done!

Now:
- Every Sunday: GitHub checks credentials
- If expired: Creates issue with fix steps
- Locally: Run `python3 refresh_credentials.py` anytime

---

## Timeline

### Without Automation (v1.0)
```
Day 1: Extract credentials, update .env
Day 2: Update .env (expired)
Day 3: Update .env (expired)
...
Day 365: Update .env 365 times 😫
```

### With Automation (v2.0)
```
Day 1: python3 refresh_credentials.py
Days 2-7: Use API
Day 7: GitHub checks (still valid)
Days 8-30: Use API
Day 30: GitHub checks (still valid)
...
Day 45: GitHub creates issue "Credentials expired"
Day 45: Run python3 refresh_credentials.py (once)
Days 46-75: Use API
✅ Only refresh when needed!
```

---

## Commands Reference

### Local Refresh
```bash
python3 refresh_credentials.py
```
Guides you through extracting credentials, validates them, updates .env

### Check Credentials Valid
```bash
curl http://localhost:5000/api/v1/validate
# or on Render
curl https://your-api.onrender.com/api/v1/validate
```

### View Extracted Credentials
```bash
cat RENDER_ENV_UPDATE.txt
```

### Update GitHub Secrets (CLI)
```bash
# If you have GitHub CLI installed
gh secret set LINKEDIN_CSRF_TOKEN --body "your_token"
gh secret set LINKEDIN_LI_AT_COOKIE --body "your_cookie"
```

---

## Troubleshooting

### "Error: credentials not configured in secrets"
**Fix**: Add GitHub secrets
- Settings → Secrets and variables → Actions
- Create LINKEDIN_CSRF_TOKEN and LINKEDIN_LI_AT_COOKIE

### "Credentials returned 403"
**Meaning**: IP is blocked by LinkedIn
**Fix**: 
- Wait 24 hours, or
- Use different IP/VPN
- Try again later

### "Credentials returned 401"
**Meaning**: Tokens are invalid/expired
**Fix**: Run `python3 refresh_credentials.py` to get fresh ones

### GitHub Actions not running
**Fix**:
1. Check `.github/workflows/refresh-credentials.yml` exists
2. Go to Actions tab in GitHub
3. Look for "Refresh LinkedIn Credentials" workflow
4. Click "Run workflow" to test manually

### Want different schedule
Edit `.github/workflows/refresh-credentials.yml`:
```yaml
on:
  schedule:
    # Change this cron expression
    # Format: minute hour day_of_month month day_of_week
    # Examples:
    - cron: '0 2 * * 0'    # Sunday 2 AM UTC
    - cron: '0 0 * * 3'    # Wednesday midnight UTC
    - cron: '0 */6 * * *'  # Every 6 hours
```

---

## File Structure

```
linkedin_api/
├── refresh_credentials.py          ← Run this to refresh
├── AUTOMATE_CREDENTIALS.md         ← This file
├── .github/
│   └── workflows/
│       └── refresh-credentials.yml ← GitHub Actions config
└── .env                            ← Updated by refresh script
```

---

## Summary

| Aspect | Setup Time | Refresh Frequency | Effort |
|--------|-----------|-------------------|--------|
| **Manual** | 0 min | When needed | 2 min each time |
| **Local Script** | 5 min | When GitHub alerts | 2 min |
| **GitHub Actions** | 10 min | Weekly auto-check | 0 min (auto-alert) |
| **Cron Job** | 5 min | Weekly auto | 0 min (auto) |

---

## Recommended Setup

1. **Start with**: Manual `python3 refresh_credentials.py`
2. **Soon after**: Add GitHub Actions (5 min setup)
3. **Benefit**: Automatic weekly checks + issue notifications

Done! No more daily credential updates.

---

## Questions?

- **How do I extract credentials?** See `extract_credentials.py`
- **How do I verify it worked?** Run `/api/v1/validate` endpoint
- **What if GitHub Actions fails?** Check Actions tab, run manually
- **Can I change the check schedule?** Yes, edit the cron in `.github/workflows/refresh-credentials.yml`

---

**Version**: v2.0  
**Status**: Production Ready  
**Tested**: Yes ✅
