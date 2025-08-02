#!/usr/bin/env python3
"""
Simple script to download code-generated files with authentication
Usage: python download_file.py
"""

import requests
import os
from urllib.parse import urlparse
import sys

from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

from app.core.config import settings

# Configuration
PROXY_URL = "http://localhost:8000/api/v1/proxy/code-files/code_generated_2025_08_02_b6b6073b_Solar_System_Designer_Documentation.md"
AUTH_TOKEN = settings.CODE_EXECUTOR_TOKEN

def download_file(url, token):
    """Download file from proxy URL with auth token"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Get filename from URL
    filename = os.path.basename(urlparse(url).path)
    
    # Save to current directory (where this script is located)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(current_dir, "temp_outputs_logs")
    file_path = os.path.join(temp_dir, filename)
    
    print(f"Downloading: {filename}")
    print(f"From: {url}")
    print(f"To: {file_path}")
    
    # Make request
    response = requests.get(url, headers=headers, allow_redirects=True)
    
    if response.status_code == 200:
        # Save file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Downloaded successfully!")
        print(f"📁 Full path: {os.path.abspath(file_path)}")
        print(f"📊 Size: {len(response.content)} bytes")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    download_file(PROXY_URL, AUTH_TOKEN)