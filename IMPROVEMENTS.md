# API Improvements v2.0

## Problem Solved: Credentials Expiring Daily

### Issue
LinkedIn session tokens (`li_at`) expire frequently (typically 24 hours), requiring manual credential extraction every day.

### Solution
The improved API now:
1. **Validates credentials before each request** - Returns clear error if credentials expired
2. **Tries multiple LinkedIn endpoints** - Falls back to alternate endpoints if primary fails
3. **Provides debug information** - Shows which endpoints were attempted and why they failed

---

## New Features

### 1. Credential Validation Endpoint
```bash
curl http://localhost:5000/api/v1/validate
```

Response:
```json
{
  "valid": true,
  "reason": "Credentials valid",
  "timestamp": "2024-01-15T10:30:00",
  "hint": null
}
```

Or if expired:
```json
{
  "valid": false,
  "reason": "Credentials expired (401)",
  "timestamp": "2024-01-15T10:30:00",
  "hint": "Run python3 extract_credentials.py to update credentials"
}
```

**Use this to check credentials before running batch operations.**

### 2. Debug Mode for Profile Requests
Add `?debug=true` to see which endpoints were attempted:

```bash
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&debug=true"
```

Response includes `debug` section showing all attempts:
```json
{
  "success": false,
  "error": "Failed to fetch profile",
  "public_id": "username",
  "debug": {
    "public_id": "username",
    "attempts": [
      {
        "endpoint": "meProfessionalProfile",
        "status": 404,
        "success": false
      },
      {
        "endpoint": "identityDashProfilesByMemberId",
        "status": 404,
        "success": false
      },
      {
        "endpoint": "profilesByPublicIdentifier",
        "status": 404,
        "success": false
      }
    ]
  }
}
```

### 3. Multiple Endpoint Strategy
The scraper now tries these endpoints in order:
1. `/voyager/api/meProfessionalProfile` - Primary endpoint
2. `/voyager/api/identityDashProfilesByMemberId` - Secondary fallback
3. `/voyager/api/profilesByPublicIdentifier` - Tertiary fallback

If one fails, it automatically tries the next. This increases success rate significantly.

### 4. Better Error Messages
Each error now includes:
- **error**: What went wrong
- **reason**: Why it failed (for auth errors)
- **status**: Machine-readable status code
- **hint**: How to fix it

Example:
```json
{
  "error": "Invalid or expired credentials",
  "reason": "Credentials expired (401)",
  "status": "credentials_expired",
  "hint": "Run python3 extract_credentials.py to get fresh credentials"
}
```

---

## Recommended Workflow

### Setup (One-time)
```bash
bash setup.sh
python3 extract_credentials.py  # Get fresh credentials
```

### Daily Usage

1. **Before batch operations**, validate credentials:
   ```bash
   curl http://localhost:5000/api/v1/validate
   ```

2. **If credentials are expired**, refresh them:
   ```bash
   python3 extract_credentials.py
   ```

3. **If profiles show "not found"**, debug with:
   ```bash
   curl "http://localhost:5000/api/v1/profile?url=YOUR_URL&debug=true"
   ```

---

## Fixing "Profile Not Found" Errors

### Scenario 1: Credentials Expired
**Symptom**: `401 Unauthorized` or `credentials_expired` status

**Fix**:
```bash
curl http://localhost:5000/api/v1/validate
python3 extract_credentials.py  # If validate returns false
```

### Scenario 2: IP Blocked
**Symptom**: `403 Forbidden` or "IP blocked by LinkedIn"

**Fix**:
- Wait 24 hours, or
- Switch to a different IP/network
- Use a VPN (be careful about LinkedIn's terms)

### Scenario 3: Profile is Private
**Symptom**: Returns profile not found but credentials are valid

**Fix**:
- Only public profiles are accessible
- The profile's privacy settings may restrict visibility
- Check if the profile is visible when logged in as your LinkedIn account

### Scenario 4: LinkedIn API Changed
**Symptom**: Multiple endpoints fail consistently

**Fix**:
- Check the LinkedIn HAR file for new endpoint patterns
- Update the endpoint URLs in `app.py`
- Run with `debug=true` to see exact error responses

---

## Implementation Details

### Credential Validation
```python
scraper.validate_credentials()  # Returns (bool, str)
```
- Hits `/voyager/api/me` endpoint
- Returns `True` if valid, `False` with reason if expired
- Called automatically before every profile fetch

### Debug Information Structure
When `debug=true` is added, response includes:
```json
{
  "debug": {
    "public_id": "extracted-id",
    "attempts": [
      {
        "endpoint": "endpoint-name",
        "status": 200,  // HTTP status or error message
        "success": true/false
      }
    ]
  }
}
```

### Rate Limiting
- Single profile: 10 requests/minute per IP
- Batch: 5 requests/minute per IP
- Use caching to reduce requests (1 hour default)

---

## Environment Variables

Required:
```bash
LINKEDIN_CSRF_TOKEN=your_csrf_token
LINKEDIN_LI_AT_COOKIE=your_li_at_cookie
```

Optional:
```bash
FLASK_ENV=production      # Default: development
FLASK_DEBUG=False         # Default: False
PORT=5000                 # Default: 5000
HOST=0.0.0.0             # Default: 0.0.0.0
```

---

## Testing Improvements

Test credentials validation:
```bash
curl http://localhost:5000/api/v1/validate
```

Test with debug info:
```bash
curl "http://localhost:5000/api/v1/profile?url=https://linkedin.com/in/test&debug=true"
```

Test batch with validation:
```bash
curl -X POST http://localhost:5000/api/v1/profile/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://linkedin.com/in/user1", "https://linkedin.com/in/user2"]}'
```

---

## Architecture Changes

### Before (v1.0)
- Single endpoint attempt
- No credential validation
- Generic "not found" errors
- No debug information

### After (v2.0)
- 3 endpoint fallback strategy
- Auto-validates credentials before each request
- Detailed error messages with hints
- Optional debug mode showing endpoint attempts
- Better logging for troubleshooting

---

## Known Limitations

1. **Credentials still expire** - But now you get clear error + hint to refresh
2. **LinkedIn API rate limits** - API still has strict rate limits (50-200 req/day per session)
3. **Profile privacy** - Private profiles remain inaccessible
4. **LinkedIn can change endpoints** - If LinkedIn changes their API significantly

---

## Next Steps

To use the improved API:

1. Start the API:
   ```bash
   python3 app.py
   ```

2. Validate credentials:
   ```bash
   curl http://localhost:5000/api/v1/validate
   ```

3. Test a profile with debug:
   ```bash
   curl "http://localhost:5000/api/v1/profile?url=https://linkedin.com/in/username&debug=true"
   ```

4. If "not found", check debug output for which endpoints were attempted

5. If credentials expired, run:
   ```bash
   python3 extract_credentials.py
   ```

That's it! No more daily `.env` changes - just refresh credentials when the API tells you to.
