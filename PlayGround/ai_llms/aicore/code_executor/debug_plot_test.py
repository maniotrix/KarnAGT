#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to test matplotlib plot generation and file detection with per-execution workspaces.
"""

import os
import sys
import requests
import json
import time

# Configure matplotlib for headless operation
import matplotlib
matplotlib.use('Agg')

def test_plot_issue():
    """Test the plot generation issue with new per-execution API."""
    base_url = "http://localhost:8080"
    
    print("🔍 Testing plot generation with new per-execution workspace API...")
    
    # Test code with explicit file flushing
    code_with_flush = """
import matplotlib
matplotlib.use('Agg')  # Ensure non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import os

print(f"Current working directory: {os.getcwd()}")
print(f"Output directory exists: {os.path.exists('outputs')}")

# Create output directory if it doesn't exist
os.makedirs('outputs', exist_ok=True)

# Simple plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.title('Debug Test Plot')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)

# Save with explicit path
plot_path = os.path.join('outputs', 'debug_plot.png')
plt.savefig(plot_path, dpi=150, bbox_inches='tight')
plt.close()

# Force file system sync
import sys
sys.stdout.flush()
import time
time.sleep(0.1)  # Small delay for file system

# Verify file was created
if os.path.exists(plot_path):
    file_size = os.path.getsize(plot_path)
    print(f"✅ Plot saved successfully: {plot_path} ({file_size} bytes)")
    
    # List all files in outputs directory
    print("Files in outputs directory:")
    for file in os.listdir('outputs'):
        full_path = os.path.join('outputs', file)
        size = os.path.getsize(full_path)
        print(f"  📄 {file} ({size} bytes)")
else:
    print("❌ Plot file not found!")

# List current directory contents
print()
print("Current directory contents:")
for item in os.listdir('.'):
    print(f"  📁 {item}")

result = "Debug plot generation completed"
"""
    
    print("\n🔍 Executing debug plot code...")
    
    # Execute using new per-execution API
    response = requests.post(
        f"{base_url}/execute",
        data={"code": code_with_flush},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Execution status: {data['status']}")
        print(f"   Workspace ID: {data['workspace_id']}")
        print(f"   Execution time: {data['execution_time']:.3f}s")
        print(f"   Output files detected: {len(data['output_files'])}")
        
        print("\n📝 Code output:")
        print("-" * 40)
        print(data['stdout'])
        print("-" * 40)
        
        if data['stderr']:
            print("\n⚠️ Stderr:")
            print(data['stderr'])
        
        print(f"\n📁 Detected output files:")
        for file in data['output_files']:
            print(f"  📄 {file['name']} ({file['size']} bytes, {file['mime_type']})")
            print(f"      Download URL: {file['download_url']}")
        
        # Try to download the file if it exists
        if data['output_files']:
            file_info = data['output_files'][0]
            filename = file_info['name']
            workspace_id = data['workspace_id']
            
            print(f"\n⬇️ Attempting to download: {filename}")
            
            download_response = requests.get(
                f"{base_url}/download/{workspace_id}/{filename}",
                timeout=10
            )
            
            if download_response.status_code == 200:
                print(f"✅ Download successful: {len(download_response.content)} bytes")
                
                # Verify it's a valid PNG
                if download_response.content[:8] == b'\x89PNG\r\n\x1a\n':
                    print("✅ Downloaded file is a valid PNG")
                else:
                    print("❌ Downloaded file doesn't appear to be a valid PNG")
            else:
                print(f"❌ Download failed: {download_response.status_code}")
                print(f"   Response: {download_response.text}")
        else:
            print("⚠️ No output files to download")
    
    else:
        print(f"❌ Execution failed: {response.status_code}")
        print(f"   Response: {response.text}")

def test_server_health():
    """Test if the server is running."""
    base_url = "http://localhost:8080"
    
    print("🏥 Testing server health...")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy!")
            print(f"   Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Active workspaces: {data['active_workspaces']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        print("   Make sure the FastAPI server is running:")
        print("   python fastapi_server.py")
        return False

if __name__ == "__main__":
    print("🔍 Debug Plot Test - Per-Execution Workspaces")
    print("=" * 60)
    
    # Test server health first
    if test_server_health():
        print()
        test_plot_issue()
    else:
        print("\n❌ Server is not running. Please start it first:")
        print("   cd backend/aicore/code_executor")
        print("   python fastapi_server.py") 