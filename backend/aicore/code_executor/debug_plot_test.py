#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to test matplotlib plot generation and file detection.
"""

import os
import sys
import requests
import json
import time

def test_plot_issue():
    """Test the plot generation issue."""
    base_url = "http://127.0.0.1:8081"
    
    # Create session
    response = requests.post(f"{base_url}/session")
    if response.status_code != 200:
        print("Failed to create session")
        return
    
    session_id = response.json()["session_id"]
    print(f"Created session: {session_id}")
    
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
print("\\nCurrent directory contents:")
for item in os.listdir('.'):
    print(f"  📁 {item}")

result = "Debug plot generation completed"
"""
    
    # Execute the debug code
    payload = {
        "code": code_with_flush,
        "session_id": session_id
    }
    
    print("\n🔍 Executing debug plot code...")
    response = requests.post(
        f"{base_url}/execute",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Execution status: {data['status']}")
        print(f"Execution time: {data['execution_time']:.3f}s")
        print(f"Output files detected: {len(data['output_files'])}")
        
        print("\n📝 Code output:")
        print(data['stdout'])
        
        if data['stderr']:
            print("\n⚠️ Stderr:")
            print(data['stderr'])
        
        print(f"\n📁 Detected output files:")
        for file in data['output_files']:
            print(f"  📄 {file['name']} ({file['size']} bytes, {file['mime_type']})")
        
        # Try to download the file
        if data['output_files']:
            filename = data['output_files'][0]['name']
            print(f"\n⬇️ Attempting to download: {filename}")
            
            download_response = requests.get(
                f"{base_url}/session/{session_id}/download/outputs/{filename}"
            )
            
            if download_response.status_code == 200:
                print(f"✅ Download successful: {len(download_response.content)} bytes")
            else:
                print(f"❌ Download failed: {download_response.status_code}")
    
    else:
        print(f"❌ Execution failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("🔍 Debug Plot Test")
    print("=" * 50)
    test_plot_issue() 