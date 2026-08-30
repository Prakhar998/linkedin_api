#!/usr/bin/env python3

import json

def validate_li_at(token: str) -> bool:
    return len(token) > 100 and isinstance(token, str)

def validate_csrf(token: str) -> bool:
    return len(token) > 10 and isinstance(token, str)

def main():
    print("="*60)
    print("LinkedIn Credential Extraction Helper")
    print("="*60)
    print()
    print("Steps:")
    print("1. Go to LinkedIn.com and log in")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Application -> Cookies -> linkedin.com")
    print("4. Find the 'li_at' cookie value")
    print("5. Go to Network tab, reload page")
    print("6. Find any request to linkedin.com")
    print("7. Look for 'x-csrf-token' in Request Headers")
    print()
    
    li_at = input("Enter li_at cookie: ").strip()
    
    if not li_at:
        print("Error: li_at cannot be empty")
        return
    
    if not validate_li_at(li_at):
        print("Warning: li_at seems short")
        confirm = input("Continue? (y/n): ").lower()
        if confirm != 'y':
            return
    
    print(f"OK - li_at received ({len(li_at)} chars)")
    
    csrf_token = input("Enter CSRF token: ").strip()
    
    if not csrf_token:
        print("Error: CSRF token cannot be empty")
        return
    
    if not validate_csrf(csrf_token):
        print("Warning: CSRF token seems short")
        confirm = input("Continue? (y/n): ").lower()
        if confirm != 'y':
            return
    
    print(f"OK - CSRF token received ({len(csrf_token)} chars)")
    
    print()
    print("="*60)
    print("Credentials extracted successfully")
    print("="*60)
    print(f"li_at: {li_at[:20]}...{li_at[-20:]}")
    print(f"CSRF:  {csrf_token[:20]}...{csrf_token[-20:]}")
    print()
    
    env_content = f"""LINKEDIN_CSRF_TOKEN={csrf_token}
LINKEDIN_LI_AT_COOKIE={li_at}
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5000
HOST=0.0.0.0
"""
    
    save = input("Save to .env file? (y/n): ").lower()
    if save == 'y':
        try:
            with open('.env', 'w') as f:
                f.write(env_content)
            print("Saved to .env")
        except Exception as e:
            print(f"Error: {e}")
            print("Content to save:")
            print(env_content)
    
    print()
    print("Next steps:")
    print("1. python3 app.py")
    print("2. curl http://localhost:5000/health")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)