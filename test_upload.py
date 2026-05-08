#!/usr/bin/env python
"""Test file upload to import/csv endpoint."""
import sys
import requests
from pathlib import Path

# Test file
csv_file = Path("d:/Ovulite new/docs/dataset/ET Summary - Sheet10.csv")

headers = {
    "Origin": "http://localhost:5174",
    "Authorization": "Bearer test"
}

with open(csv_file, 'rb') as f:
    files = {'file': (csv_file.name, f, 'text/csv')}
    print(f"Uploading {csv_file.name}...")
    try:
        resp = requests.post(
            "http://localhost:8000/import/csv",
            files=files,
            headers=headers,
            timeout=30
        )
        print(f"Status: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")
