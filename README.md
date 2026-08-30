# LinkedIn Profile API

A reverse-engineered API that scrapes LinkedIn profile information without browser automation. Uses direct endpoint calls to LinkedIn's internal Voyager API.

**Disclaimer**: This project is for educational purposes. Use at your own risk and comply with LinkedIn's Terms of Service.

## Features

- ✅ No browser automation (Selenium, Puppeteer, etc.)
- ✅ Fast responses (100-500ms per profile)
- ✅ Structured JSON output
- ✅ Batch processing support
- ✅ Built-in caching (1 hour)
- ✅ Rate limiting (10 req/min per IP)
- ✅ Production-ready deployment
- ✨ **NEW v2.0**: Credential validation endpoint
- ✨ **NEW v2.0**: Multiple endpoint fallback strategy (3 endpoints attempted)
- ✨ **NEW v2.0**: Debug mode for troubleshooting
- ✨ **NEW v2.0**: Detailed error messages with actionable hints

## Quick Start (v2.0)

### Check Credentials Validity
```bash
curl http://localhost:5000/api/v1/validate
```

### Get Profile with Debug Info
```bash
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&debug=true"
```

### Batch Process Multiple Profiles
```bash
curl -X POST http://localhost:5000/api/v1/profile/batch \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://www.linkedin.com/in/user1", "https://www.linkedin.com/in/user2"]}'
```

**See [IMPROVEMENTS.md](IMPROVEMENTS.md) for complete v2.0 features and troubleshooting guide.**

## Response Format

```json
{
  "success": true,
  "data": {
    "id": "string",
    "firstName": "string",
    "lastName": "string",
    "headline": "string",
    "location": {
      "name": "string",
      "country": "string"
    },
    "about": "string",
    "profileImage": "string or null",
    "experience": [
      {
        "title": "string",
        "company": "string",
        "location": "string",
        "startDate": "string",
        "endDate": "string or null",
        "duration": "string",
        "description": "string",
        "isCurrent": "boolean"
      }
    ],
    "education": [
      {
        "schoolName": "string",
        "degree": "string",
        "fieldOfStudy": "string",
        "startDate": "string",
        "endDate": "string"
      }
    ],
    "skills": [
      {
        "name": "string",
        "endorsements": "number"
      }
    ],
    "certifications": [
      {
        "name": "string",
        "issuer": "string",
        "issueDate": "string",
        "expirationDate": "string or null",
        "credentialUrl": "string"
      }
    ],
    "languages": [
      {
        "name": "string",
        "proficiency": "string"
      }
    ]
  },
  "metadata": {
    "fetchedAt": "2024-01-15T10:30:00",
    "profileUrl": "https://linkedin.com/in/username",
    "cached": false
  }
}
```

## API Endpoints

### GET /health
Returns API status.

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "version": "2.0.0"
}
```

### GET /api/v1/validate
**NEW in v2.0** - Validate if stored credentials are still active.

Response (valid credentials):
```json
{
  "valid": true,
  "reason": "Credentials valid",
  "timestamp": "2024-01-15T10:30:00",
  "hint": null
}
```

Response (expired credentials):
```json
{
  "valid": false,
  "reason": "Credentials expired (401)",
  "timestamp": "2024-01-15T10:30:00",
  "hint": "Run python3 extract_credentials.py to update credentials"
}
```

Use before batch operations to fail fast if credentials are invalid.

### GET /api/v1/profile?url=<linkedin-url>&include_raw=false&debug=false
Returns profile data for a single LinkedIn URL.

Parameters:
- url (required): LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)
- include_raw (optional): Include raw API response (default: false)
- debug (optional): **NEW in v2.0** - Show which endpoints were attempted and responses (default: false)

**Debug mode example**:
```bash
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username&debug=true"
```

Shows which of the 3 fallback endpoints were tried and their results, helpful for diagnosing "profile not found" errors.

### POST /api/v1/profile/batch
Fetch multiple profiles in one request.

Body:
```json
{
  "urls": [
    "https://www.linkedin.com/in/profile1",
    "https://www.linkedin.com/in/profile2"
  ]
}
```

Maximum 10 profiles per request.

### GET /api/v1/docs
Returns API documentation.

## Setup

### Prerequisites
- Python 3.8+
- LinkedIn account with active session

### Local Setup

1. Clone repository:
```bash
git clone <repo-url>
cd linkedin-profile-api
```

2. Run setup script:
```bash
bash setup.sh
```

3. Extract LinkedIn credentials:
```bash
python3 extract_credentials.py
```

Follow the prompts to extract:
- li_at cookie: Go to LinkedIn.com, open DevTools, Application > Cookies > linkedin.com, find 'li_at'
- CSRF token: Go to Network tab, reload LinkedIn, find any request, look for 'x-csrf-token' in Request Headers

4. Run API:
```bash
python3 app.py
```

5. Test:
```bash
curl http://localhost:5000/health
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username"
```

### Docker Setup

```bash
docker-compose up
```

### Cloud Deployment

#### Heroku
```bash
heroku create app-name
heroku config:set LINKEDIN_CSRF_TOKEN=token LINKEDIN_LI_AT_COOKIE=cookie
git push heroku main
```

#### Google Cloud Run
```bash
gcloud run deploy linkedin-api --source . \
  --set-env-vars LINKEDIN_CSRF_TOKEN=...,LINKEDIN_LI_AT_COOKIE=...
```

#### Docker
```bash
docker build -t linkedin-api .
docker run \
  -e LINKEDIN_CSRF_TOKEN=token \
  -e LINKEDIN_LI_AT_COOKIE=cookie \
  -p 5000:5000 \
  linkedin-api
```

## How It Works

### Architecture

The API uses direct endpoint calls to LinkedIn's internal Voyager API instead of browser automation:

1. Extract LinkedIn credentials (li_at cookie + CSRF token) from browser
2. Create authenticated session with credentials
3. Call Voyager API endpoint for profile data
4. Parse response into structured JSON
5. Cache result for 1 hour
6. Return to client

### Why No Browser Automation?

Browser automation (Selenium, Puppeteer):
- 5-30 seconds per profile
- High resource usage
- Prone to crashes
- Breaks when LinkedIn UI changes

Direct endpoints:
- 100-500ms per profile
- Minimal resource usage
- Stable and reliable
- API endpoints rarely change

### Rate Limiting

LinkedIn enforces strict rate limits:
- Per session: 50-200 requests/day
- Per IP: May get blocked for aggressive scraping

API rate limiting:
- 10 requests/minute per IP (single profile)
- 5 requests/minute per IP (batch)
- 1-hour caching reduces redundant calls
- Automatic exponential backoff on 429 errors

Recommended usage:
- 1-2 requests per profile per day
- Wait 2-5 seconds between requests
- Use batch endpoint for multiple profiles
- Respect 429 (Too Many Requests) responses

## Testing

Run test suite:
```bash
python3 test_api.py http://localhost:5000
```

Tests included:
- Health check
- API docs endpoint
- Parameter validation
- Batch processing
- Rate limiting
- CORS headers

## Known Limitations

### LinkedIn-Side
- Session tokens expire (usually 24 hours)
- Rate limiting per session
- IP-based blocking for aggressive scraping
- Only public profile data accessible

### API-Side
- No private profile information
- Some fields may be null if user didn't fill LinkedIn
- No recommendation text or connection status
- Profile image URLs are time-limited (LinkedIn CDN)

### Technical
- Requires manual credential extraction
- LinkedIn may change API endpoints

## Error Codes

200 - Success
400 - Bad request (invalid or missing parameter)
401 - Authentication failed (credentials expired)
403 - Forbidden (IP blocked by LinkedIn)
404 - Profile not found
429 - Rate limit exceeded
503 - Service unavailable (credentials invalid)
500 - Internal server error

## Examples

### Python
```python
import requests

response = requests.get(
    "http://localhost:5000/api/v1/profile",
    params={"url": "https://www.linkedin.com/in/username"}
)
profile = response.json()
print(profile['data']['firstName'])
```

### JavaScript
```javascript
const response = await fetch(
  "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username"
);
const profile = await response.json();
console.log(profile.data.firstName);
```

### cURL
```bash
curl "http://localhost:5000/api/v1/profile?url=https://www.linkedin.com/in/username"
```

## Files

- app.py - Main Flask application
- extract_credentials.py - Credential extraction tool
- test_api.py - Test suite
- setup.sh - Setup automation
- requirements.txt - Python dependencies
- Dockerfile - Container setup
- docker-compose.yml - Local dev setup
- Procfile - Heroku deployment
- .env.example - Configuration template
- .gitignore - Git ignore rules
- LICENSE - MIT License

## Security

Credentials are stored in .env file (not committed to git):
- LINKEDIN_CSRF_TOKEN
- LINKEDIN_LI_AT_COOKIE

.env is in .gitignore to prevent accidental leaks.

Never share your .env file or credentials.

## Support

For setup help, see README.md (this file)
For technical details, see APPROACH.md

## License

MIT License