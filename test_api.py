#!/usr/bin/env python3

import sys
import requests
import time

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
    
    def test(self, name: str, method: str, endpoint: str, params=None, json_data=None, expected_status=200):
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = self.session.get(url, params=params, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=json_data, timeout=10)
            else:
                return False, f"Unknown method: {method}"
            
            if response.status_code != expected_status:
                return False, f"Expected {expected_status}, got {response.status_code}"
            
            try:
                response.json()
            except:
                return False, "Response is not JSON"
            
            return True, f"Status {response.status_code}"
            
        except requests.exceptions.Timeout:
            return False, "Timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, str(e)
    
    def print_test(self, name: str, passed: bool, message: str):
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name:<40} {message}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def run_all(self):
        print(f"Testing: {self.base_url}")
        print("="*60)
        
        print("\nBasic Tests:")
        passed, msg = self.test("Health Check", "GET", "/health", expected_status=200)
        self.print_test("GET /health", passed, msg)
        
        passed, msg = self.test("API Docs", "GET", "/api/v1/docs", expected_status=200)
        self.print_test("GET /api/v1/docs", passed, msg)
        
        print("\nValidation Tests:")
        passed, msg = self.test("Missing URL", "GET", "/api/v1/profile", expected_status=400)
        self.print_test("Missing url parameter", passed, msg)
        
        passed, msg = self.test("Invalid URL", "GET", "/api/v1/profile", 
                               params={"url": "https://example.com"}, expected_status=400)
        self.print_test("Non-LinkedIn URL", passed, msg)
        
        passed, msg = self.test("Empty batch", "POST", "/api/v1/profile/batch",
                               json_data={"urls": []}, expected_status=400)
        self.print_test("Empty batch array", passed, msg)
        
        print("\n" + "="*60)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("="*60)
        
        return self.failed == 0

def main():
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        api_url = "http://localhost:5000"
    
    tester = APITester(api_url)
    success = tester.run_all()
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)