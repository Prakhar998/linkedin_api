# Troubleshooting Guide

## Quick Diagnosis Flowchart

```
Profile request returns error?
├─ 401 (Credentials expired)
│  └─ Run: python3 extract_credentials.py
├─ 403 (IP blocked)
│  └─ Wait 24h or use different IP/VPN
├─ 404 (Profile not found)
│  └─ Add ?debug=true to see which endpoints failed
└─ 500 (Server error)
   └─ Check logs, see "Debugging Tips" below
```

---

## Common Issues & Fixes

### Issue 1: "credentials_expired" or 401 Error

**Symptoms**:
```json
{
  "error": "Invalid or expired credentials",
  "reason": "Credentials expired (401)",
  "status": "credentials_expired",
  "hint": "Run python3 extract_credentials.py to get fresh credentials"
}
```

**Root Cause**: LinkedIn session token (`li_at`) expired

**Fix** (2 minutes):
```bash
# 1. Check current status
curl http://localhost:5000/api/v1/validate

# 2. If invalid, refresh
python3 extract_credentials.py

# 3. Follow prompts to extract new credentials
# 4. Test again
curl http://localhost:5000/api/v1/validate
```

**How to Prevent**:
- Check `/validate` before running large batch operations
- Set up a daily cron job to refresh credentials
- Check credentials if API fails suddenly

---

### Issue 2: "Profile Not Found" or 404

**Symptoms**:
```json
{
  "error": "Failed to fetch profile",
  "public_id": "username",
  "status": "profile_not_found"
}
```

**Root Cause**: Could be credentials, private profile, or endpoint issue

**Fix (Step 1)**: Validate credentials first
```bash
curl http://localhost:5000/api/v1/validate

# If invalid, run:
python3 extract_credentials.py
```

**Fix (Step 2)**: Debug with `?debug=true`
```bash
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&debug=true"
```

**Look for in debug output**:
```json
{
  "debug": {
    "attempts": [
      {
        "endpoint": "meProfessionalProfile",
        "status": 404  // All 404? Likely private profile
      },
      {
        "endpoint": "identityDashProfilesByMemberId",
        "status": 404
      },
      {
        "endpoint": "profilesByPublicIdentifier",
        "status": 404
      }
    ]
  }
}
```

**Interpretation**:
- **All endpoints return 404**: Profile is private or doesn't exist
- **Some endpoints return 404, others different**: Mixed endpoint support
- **All endpoints return 401**: Credentials expired
- **All endpoints return 403**: IP blocked

**Fix (Step 3)**: Check profile visibility
1. Log into LinkedIn with the account that set up credentials
2. Visit the profile URL directly
3. Can you see the profile? If no, it's private/restricted
4. If yes, the profile exists but isn't fetched by API yet

---

### Issue 3: "Access Forbidden" or 403

**Symptoms**:
```json
{
  "error": "Invalid or expired credentials",
  "reason": "Access forbidden (403) - IP may be blocked"
}
```

**Root Cause**: LinkedIn blocked your IP for too many requests

**Why it happens**:
- Made too many requests too quickly
- LinkedIn identified bot behavior
- Your IP is marked as suspicious

**Fixes**:
1. **Wait 24 hours** - LinkedIn automatically unblocks IPs
2. **Use a VPN** - Switch to different IP (be careful with LinkedIn ToS)
3. **Reduce request rate** - Space out requests by 2-5 seconds
4. **Check batch size** - Don't exceed 10 profiles per request

**Prevention**:
- Use caching (default: 1 hour)
- Space requests 2-5 seconds apart
- Don't exceed 10 profiles per batch
- Check rate limits: 10 req/min for single, 5 req/min for batch

---

### Issue 4: Connection Timeout

**Symptoms**:
```json
{
  "error": "Internal server error",
  "details": "timeout"
}
```

**Root Cause**: LinkedIn server slow or unreachable

**Fixes**:
1. **Wait a minute** - LinkedIn might be temporarily slow
2. **Check internet** - Verify your connection
3. **Try again** - API retries automatically (3 times)
4. **Check LinkedIn status** - Visit linkedin.com manually

**Prevention**:
- LinkedIn is usually fast (100-500ms)
- If timeouts persist, it's likely your connection

---

### Issue 5: Empty Profile Data

**Symptoms**:
```json
{
  "success": true,
  "data": {
    "firstName": null,
    "lastName": null,
    "headline": null,
    "experience": [],
    "education": []
  }
}
```

**Root Cause**: Profile is public but empty, or LinkedIn API structure changed

**Checks**:
1. Is the profile actually empty on LinkedIn? (Yes = normal)
2. Did it work before? (No = API might have changed)
3. Are credentials definitely valid? (Use `/validate` to check)

**Debugging**:
```bash
# Get raw API response
curl "http://localhost:5000/api/v1/profile?url=...&include_raw=true"

# Look at the raw JSON structure
# It should contain profile data with keys like:
# - firstName, lastName, headline
# - experience, education, skills
# - If all are null, profile data wasn't in response
```

---

### Issue 6: Batch Operations Partially Failing

**Symptoms**:
```json
{
  "data": [
    {
      "url": "https://linkedin.com/in/user1",
      "success": true,
      "data": {...}
    },
    {
      "url": "https://linkedin.com/in/user2",
      "success": false,
      "error": "Profile not found"
    }
  ],
  "metadata": {
    "totalRequested": 2,
    "successfulCount": 1
  }
}
```

**Possible Causes**:
1. Some profiles are private/don't exist
2. Some URLs are malformed
3. API rate limited during batch (returned 429)

**Fixes**:
1. **Check individual profiles**: Test each URL with debug mode
2. **Space out requests**: Reduce batch size from 10 to 5
3. **Wait between batches**: 30+ seconds between batch calls
4. **Check `/validate`**: Ensure credentials still valid mid-batch

---

## Debugging Tips

### Enable Debug Mode
Add `debug=true` to see endpoint attempts:
```bash
curl "http://localhost:5000/api/v1/profile?url=...&debug=true"
```

### Check Server Logs
```bash
# Terminal 1: Start API with visible logs
FLASK_ENV=development python3 app.py

# Terminal 2: Make request
curl "http://localhost:5000/api/v1/profile?url=..."

# Look at Terminal 1 for detailed logs including:
# - Endpoint URLs being called
# - HTTP status codes
# - Response times
# - Error details
```

### Validate Credentials
Always start here:
```bash
curl http://localhost:5000/api/v1/validate

# Response shows if credentials are valid
# If not, tells you exactly why
```

### Test with curl
```bash
# Single profile with debug
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&debug=true"

# With raw response
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&include_raw=true"

# Check health
curl http://localhost:5000/health

# Check docs
curl http://localhost:5000/api/v1/docs
```

### Extract Profile ID
When reporting issues, include the extracted profile ID:
```bash
# From this URL:
https://www.linkedin.com/in/john-doe-123abc/

# The profile ID extracted is:
john-doe-123abc
```

---

## Common URL Issues

### Wrong Format
```
❌ linkedin.com/in/username      # Missing https://www
❌ www.linkedin.com/in/username  # Missing https://
✅ https://www.linkedin.com/in/username
✅ https://linkedin.com/in/username
```

### URL Parameters
LinkedIn URLs often have tracking parameters:
```
❌ https://www.linkedin.com/in/username?locale=...&lipi=...
✅ https://www.linkedin.com/in/username  # Just copy the base URL
```

The API strips parameters automatically, so both work, but cleaner to provide base URL.

---

## Performance Issues

### Slow Responses (>3 seconds)

**Possible Causes**:
1. LinkedIn server slow
2. Your internet connection slow
3. Retry attempts (API retries 3 times by default)

**Fixes**:
1. Try again (LinkedIn sometimes slow)
2. Check your internet speed
3. Check LinkedIn.com loading speed manually

### Slow Batch Operations

**Possible Causes**:
1. Too many profiles in one batch
2. Waiting for rate limits
3. Some profiles taking longer

**Fixes**:
1. Reduce batch size to 5 profiles
2. Space batches 30+ seconds apart
3. Check individual profiles for slow ones

---

## Testing Checklist

Before reporting an issue, verify:

```bash
# 1. API is running
curl http://localhost:5000/health
# Should return 200 with status: healthy

# 2. Credentials are valid
curl http://localhost:5000/api/v1/validate
# Should return valid: true

# 3. Single profile works with debug
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/test&debug=true"
# Should show attempts and why it succeeded/failed

# 4. Batch works
curl -X POST http://localhost:5000/api/v1/profile/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://www.linkedin.com/in/test"]}'
# Should return array of results

# 5. Check logs
# Run API in development mode:
FLASK_ENV=development python3 app.py
```

---

## Still Stuck?

### Gather Debug Info

Run this and share output:
```bash
# Check API version and endpoints
curl http://localhost:5000/api/v1/docs

# Check credentials status
curl http://localhost:5000/api/v1/validate

# Try a test profile with debug
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/satya-nadella&debug=true" 2>&1

# Show Python version
python3 --version

# Show requirements
pip list | grep -E "Flask|requests|linkedin"
```

### Get Help

Include:
1. The error message (full JSON)
2. Debug output from above
3. Steps to reproduce
4. Credential status (from `/validate`)
5. Whether it worked before

---

## Advanced Troubleshooting

### Check Session Headers
The API sends specific headers for LinkedIn compatibility. If endpoints fail:
```bash
# Check headers being sent (add verbose)
curl -v "http://localhost:5000/api/v1/profile?url=..." 2>&1 | grep -i "^>"
```

### Check Retry Logic
API automatically retries failed requests 3 times for status codes: 429, 500, 502, 503, 504

To see retry attempts:
```bash
FLASK_ENV=development python3 app.py
# Makes request, watch logs for retries
```

### Check Cache
API caches responses for 1 hour per URL. To bypass:
```bash
# Add random parameter to bust cache
curl "http://localhost:5000/api/v1/profile?url=...&bust=$(date +%s)"
```

---

## Known Limitations (Not Bugs)

These are limitations of the LinkedIn reverse-engineering approach, not bugs:

1. **Private profiles** - Only public profiles accessible
2. **Rate limits** - LinkedIn limits to ~50-200 requests/day per session
3. **IP blocking** - LinkedIn blocks aggressive scrapers
4. **Credential expiry** - Session tokens expire (usually 24 hours)
5. **Profile images** - LinkedIn CDN URLs expire after ~24 hours
6. **No private messages** - Private profile sections not accessible

---

## For Developers

### Adding Logging
Edit `app.py` to add more logging:
```python
import logging
logger = logging.getLogger(__name__)

# In functions:
logger.debug(f"Debug message: {variable}")
logger.info(f"Info: {message}")
logger.warning(f"Warning: {issue}")
logger.error(f"Error: {error}", exc_info=True)
```

### Debugging Endpoint Changes
If LinkedIn changes endpoints:
1. Capture HAR file of LinkedIn login
2. Extract endpoint URLs
3. Add to `app.py` fallback strategy
4. Test with `debug=true`

### Testing New Endpoints
```python
# In LinkedInProfileScraper
def get_profile_by_public_id(self, public_id):
    url = "https://www.linkedin.com/voyager/api/NEW_ENDPOINT?q=memberIdentity&memberIdentity={public_id}"
    response = self.session.get(url, timeout=10)
    return response.json()
```

---

**Last Updated**: v2.0
**Status**: Production Ready
