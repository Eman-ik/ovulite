#!/usr/bin/env python
"""Test authenticated file upload."""
import requests
from pathlib import Path

# Login to get token
login_resp = requests.post(
    "http://localhost:8000/auth/login",
    data={"username": "admin", "password": "ovulite2026"}
)
print(f"Login Status: {login_resp.status_code}")

if login_resp.status_code == 200:
    token = login_resp.json().get("access_token")
    print(f"Token obtained: {token[:30]}...")
    
    # Now test file upload with valid token
    csv_file = Path("docs/dataset/ET Summary - Sheet10.csv")
    
    headers = {
        "Origin": "http://localhost:5174",
        "Authorization": f"Bearer {token}"
    }
    
    with open(csv_file, 'rb') as f:
        files = {'file': (csv_file.name, f)}
        print(f"\nUploading {csv_file.name}...")
        resp = requests.post(
            "http://localhost:8000/import/csv",
            files=files,
            headers=headers,
            timeout=60
        )
        print(f"Upload Status: {resp.status_code}")
        print(f"Response: {resp.json() if resp.headers.get('content-type') == 'application/json' else resp.text}")
else:
    print(f"Login failed: {login_resp.json()}")
