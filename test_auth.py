#!/usr/bin/env python
"""Test authentication endpoints"""
import requests
import json

print("Testing Backend Authentication Endpoints")
print("=" * 70)

users = [
    {"username": "admin", "password": "ovulite2026"},
    {"username": "lab_tech", "password": "ovulite2026"},
    {"username": "et_tech", "password": "ovulite2026"},
    {"username": "et_Tech", "password": "ovulite2026"},
]

for user in users:
    url = "http://localhost:8000/auth/login"
    data = f"username={user['username']}&password={user['password']}"
    
    try:
        resp = requests.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        print(f"\n{user['username'].upper()}")
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"PASS: Login successful")
            print(f"  Token: {result.get('access_token', 'N/A')[:30]}...")
            
            # Test /auth/me endpoint
            access_token = result['access_token']
            me_resp = requests.get(
                "http://localhost:8000/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5
            )
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                print(f"  User: {me_data.get('username')}")
                print(f"  Role: {me_data.get('role')}")
            else:
                print(f"  /auth/me failed: {me_resp.status_code}")
        else:
            print(f"FAIL: Login failed")
            print(f"  Response: {resp.text}")
            
    except Exception as e:
        print(f"\n{user['username'].upper()}")
        print(f"FAIL Error: {e}")

print("\n" + "=" * 70)
