#!/usr/bin/env python3
"""
Load CSV files from docs/dataset/ into the Ovulite system.
Authenticates as admin and imports multiple CSV files.
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
CREDENTIALS = {
    "username": "admin",
    "password": "ovulite2026"
}

CSV_FILES = [
    "docs/dataset/New_Records_ET Summary - ET Data.csv",
]

def get_auth_token():
    """Login and get bearer token."""
    print("🔐 Authenticating...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=CREDENTIALS,
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Authenticated successfully")
    return token

def import_csv_file(token, csv_path):
    """Upload and import a CSV file."""
    print(f"\n📤 Importing: {csv_path}")
    
    # Check if file exists
    if not Path(csv_path).exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    # Read and upload file
    with open(csv_path, 'rb') as f:
        files = {'file': (Path(csv_path).name, f, 'text/csv')}
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = requests.post(
                f"{BASE_URL}/import/csv",
                headers=headers,
                files=files,
                timeout=30
            )
        except requests.Timeout:
            print(f"⏱️  Request timeout - import may still be processing")
            return False
    
    if response.status_code != 200:
        print(f"❌ Import failed: {response.status_code}")
        print(response.text)
        return False
    
    # Success
    data = response.json()
    rows_read = data.get('rows_read', 0)
    rows_ingested = data.get('rows_ingested', 0)
    rows_skipped = data.get('rows_skipped', 0)
    
    print(f"✅ Import completed:")
    print(f"   Rows read: {rows_read}")
    print(f"   Rows ingested: {rows_ingested}")
    print(f"   Rows skipped: {rows_skipped}")
    
    if data.get('errors'):
        print(f"⚠️  Errors: {len(data['errors'])} errors found")
        for err in data['errors'][:5]:  # Show first 5
            print(f"   - {err}")
    
    return True

def verify_import():
    """Check total records in database."""
    print("\n📊 Verifying import...")
    try:
        response = requests.get(f"{BASE_URL}/transfers/?page_size=1")
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"✅ Total transfers in database: {total}")
            return total
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
    return None

def main():
    print("=" * 60)
    print("Ovulite CSV File Loader")
    print("=" * 60)
    
    # Authenticate
    token = get_auth_token()
    if not token:
        print("❌ Failed to authenticate")
        return
    
    # Import all CSV files
    success_count = 0
    for csv_file in CSV_FILES:
        if import_csv_file(token, csv_file):
            success_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"✅ Successfully imported {success_count}/{len(CSV_FILES)} files")
    print(f"{'=' * 60}")
    
    # Verify
    total = verify_import()
    if total and total > 0:
        print(f"🎉 Database now contains {total} ET transfer records!")
    
    print("\n📈 Dashboard will auto-update on next page load/refresh")

if __name__ == "__main__":
    main()
