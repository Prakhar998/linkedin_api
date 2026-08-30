#!/usr/bin/env python3
"""
Automated LinkedIn Credential Refresh Script
Extracts credentials from LinkedIn and updates .env file
Can be run manually or via cron/GitHub Actions
"""

import os
import json
import sys
import subprocess
from datetime import datetime
from typing import Tuple, Optional

def validate_li_at(token: str) -> bool:
    """Check if li_at token looks valid."""
    return len(token) > 100 and isinstance(token, str)

def validate_csrf(token: str) -> bool:
    """Check if CSRF token looks valid."""
    return len(token) > 10 and isinstance(token, str)

def extract_credentials_from_har(har_file: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract credentials from a captured HAR file.

    Usage:
    1. Go to linkedin.com and log in
    2. Open DevTools (F12)
    3. Right-click on Network tab → "Save all as HAR"
    4. Run: python3 refresh_credentials.py capture.har
    """
    try:
        with open(har_file, 'r') as f:
            data = json.load(f)

        li_at = None
        csrf_token = None

        # Extract li_at cookie from HAR
        for entry in data.get('log', {}).get('entries', []):
            cookies = entry.get('request', {}).get('cookies', [])
            for cookie in cookies:
                if cookie.get('name') == 'li_at':
                    li_at = cookie.get('value')

            # Extract CSRF token from headers
            headers = entry.get('request', {}).get('headers', [])
            for header in headers:
                if header.get('name').lower() == 'x-csrf-token':
                    csrf_token = header.get('value')

        return li_at, csrf_token
    except Exception as e:
        print(f"Error parsing HAR file: {e}")
        return None, None

def get_credentials_from_browser() -> Tuple[Optional[str], Optional[str]]:
    """
    Interactive method to extract credentials from browser.
    User provides them manually from DevTools.
    """
    print("="*60)
    print("LinkedIn Credential Extraction - Interactive Mode")
    print("="*60)
    print()
    print("Steps:")
    print("1. Go to https://www.linkedin.com and log in")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application → Cookies → linkedin.com")
    print("4. Find and copy the 'li_at' cookie value")
    print("5. Go to Network tab, reload page")
    print("6. Find any request to linkedin.com")
    print("7. Look for 'x-csrf-token' in Request Headers")
    print()

    li_at = input("Enter li_at cookie: ").strip()

    if not li_at:
        print("❌ Error: li_at cannot be empty")
        return None, None

    if not validate_li_at(li_at):
        print("⚠️  Warning: li_at seems short (expected >100 chars)")
        confirm = input("Continue anyway? (y/n): ").lower()
        if confirm != 'y':
            return None, None

    print(f"✅ li_at received ({len(li_at)} chars)")

    csrf_token = input("Enter x-csrf-token: ").strip()

    if not csrf_token:
        print("❌ Error: CSRF token cannot be empty")
        return None, None

    if not validate_csrf(csrf_token):
        print("⚠️  Warning: CSRF token seems short (expected >10 chars)")
        confirm = input("Continue anyway? (y/n): ").lower()
        if confirm != 'y':
            return None, None

    print(f"✅ CSRF token received ({len(csrf_token)} chars)")

    return li_at, csrf_token

def update_env_file(li_at: str, csrf_token: str) -> bool:
    """Update .env file with new credentials."""
    try:
        env_content = f"""LINKEDIN_CSRF_TOKEN={csrf_token}
LINKEDIN_LI_AT_COOKIE={li_at}
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000
HOST=0.0.0.0
"""

        with open('.env', 'w') as f:
            f.write(env_content)

        print("✅ .env file updated successfully")
        return True
    except Exception as e:
        print(f"❌ Error updating .env: {e}")
        return False

def update_render_env(li_at: str, csrf_token: str) -> bool:
    """
    Instructions for updating Render environment variables.
    """
    print()
    print("="*60)
    print("To update Render environment variables:")
    print("="*60)
    print()
    print("1. Go to https://dashboard.render.com")
    print("2. Select your service")
    print("3. Go to Settings → Environment")
    print("4. Update:")
    print()
    print(f"   LINKEDIN_CSRF_TOKEN = {csrf_token}")
    print()
    print(f"   LINKEDIN_LI_AT_COOKIE = {li_at}")
    print()
    print("5. Click 'Save Changes' (auto-deploys)")
    print()
    print("="*60)
    print()

    # Also save to a file for reference
    try:
        with open('RENDER_ENV_UPDATE.txt', 'w') as f:
            f.write(f"LINKEDIN_CSRF_TOKEN={csrf_token}\n")
            f.write(f"LINKEDIN_LI_AT_COOKIE={li_at}\n")
        print("✅ Credentials also saved to RENDER_ENV_UPDATE.txt")
    except:
        pass

    return True

def validate_new_credentials(li_at: str, csrf_token: str) -> bool:
    """
    Try to validate new credentials by calling the API.
    """
    try:
        import requests

        session = requests.Session()
        session.cookies.set('li_at', li_at)
        session.headers['X-CSRF-Token'] = csrf_token

        url = "https://www.linkedin.com/voyager/api/me"
        response = session.get(url, timeout=10)

        if response.status_code == 200:
            print("✅ Credentials validated successfully!")
            return True
        elif response.status_code == 401:
            print("⚠️  Credentials returned 401 (Unauthorized)")
            print("   They may be expired or invalid")
            return False
        elif response.status_code == 403:
            print("⚠️  Credentials returned 403 (Forbidden)")
            print("   IP may be blocked by LinkedIn")
            return False
        else:
            print(f"⚠️  Got response {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Could not validate online: {e}")
        return False

def main():
    """Main entry point."""
    print()
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  LinkedIn Credential Refresh Script v2.0".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    print()

    # Check for HAR file argument
    if len(sys.argv) > 1:
        har_file = sys.argv[1]
        print(f"Extracting from HAR file: {har_file}")
        li_at, csrf_token = extract_credentials_from_har(har_file)

        if not li_at or not csrf_token:
            print("❌ Could not extract credentials from HAR file")
            sys.exit(1)
    else:
        # Interactive mode
        li_at, csrf_token = get_credentials_from_browser()

        if not li_at or not csrf_token:
            print("❌ Failed to get credentials")
            sys.exit(1)

    print()
    print("="*60)
    print("Extracted Credentials")
    print("="*60)
    print(f"li_at:       {li_at[:20]}...{li_at[-20:]}")
    print(f"CSRF token:  {csrf_token[:20]}...{csrf_token[-20:]}")
    print()

    # Try to validate
    print("Validating credentials with LinkedIn...")
    is_valid = validate_new_credentials(li_at, csrf_token)
    print()

    # Update local .env
    print("Updating local .env file...")
    if update_env_file(li_at, csrf_token):
        print()

        # Show Render instructions
        update_render_env(li_at, csrf_token)

        print("✅ Credentials refreshed successfully!")
        print()
        print("Next steps:")
        print("1. Update Render environment variables (see above)")
        print("2. Your API will be ready to use")
        print("3. No more daily credential updates needed!")
        print()

        return 0
    else:
        print("❌ Failed to update .env file")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
