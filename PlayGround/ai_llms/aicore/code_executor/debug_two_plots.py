#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to test the exact matplotlib code that should create 2 plots with per-execution workspaces.
"""

import requests
import json

# Configure matplotlib for headless operation
import matplotlib
matplotlib.use('Agg')

def debug_two_plots():
    """Test the exact same code that should create 2 plots using new per-execution API."""
    base_url = "http://localhost:8080"
    
    print("🔍 Testing two-plot generation with new per-execution workspace API...")
    
    # EXACT same code as the failing test, but updated for new structure
    code = """
import matplotlib
matplotlib.use('Agg')  # Ensure non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

print("=== STARTING PLOT GENERATION ===")
print(f"Working directory: {os.getcwd()}")
print(f"Outputs directory exists: {os.path.exists('outputs')}")

# Create outputs directory
os.makedirs('outputs', exist_ok=True)

# Create sample data (same as original test)
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

print()
print("=== CREATING FIRST PLOT (comprehensive_plots.png) ===")

# Create plots
plt.figure(figsize=(12, 8))

# Subplot 1
plt.subplot(2, 2, 1)
plt.plot(x, y1, 'b-', label='sin(x)')
plt.plot(x, y2, 'r-', label='cos(x)')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True)

# Subplot 2 - Bar chart
plt.subplot(2, 2, 2)
categories = ['A', 'B', 'C', 'D']
values = [23, 45, 56, 78]
plt.bar(categories, values, color=['red', 'green', 'blue', 'orange'])
plt.title('Sample Bar Chart')

# Subplot 3 - Scatter plot
plt.subplot(2, 2, 3)
x_scatter = np.random.randn(50)
y_scatter = np.random.randn(50)
plt.scatter(x_scatter, y_scatter, alpha=0.6)
plt.title('Random Scatter Plot')

# Subplot 4 - Histogram
plt.subplot(2, 2, 4)
data = np.random.normal(0, 1, 1000)
plt.hist(data, bins=30, alpha=0.7)
plt.title('Normal Distribution Histogram')

plt.tight_layout()

# Save first plot
print("Saving first plot...")
try:
    plt.savefig('outputs/comprehensive_plots.png', dpi=150, bbox_inches='tight')
    print("✅ First plot saved successfully!")
except Exception as e:
    print(f"❌ Error saving first plot: {e}")

plt.close()
print("✅ First plot closed")

print()
print("=== CREATING SECOND PLOT (product_plot.png) ===")

# Individual plot
plt.figure(figsize=(8, 6))
plt.plot(x, y1 * y2, 'g-', linewidth=2)
plt.title('sin(x) * cos(x)')
plt.xlabel('x')
plt.ylabel('sin(x) * cos(x)')
plt.grid(True)

# Save second plot
print("Saving second plot...")
try:
    plt.savefig('outputs/product_plot.png', dpi=150)
    print("✅ Second plot saved successfully!")
except Exception as e:
    print(f"❌ Error saving second plot: {e}")

plt.close()
print("✅ Second plot closed")

print()
print("=== VERIFYING FILES ===")
# Check what files actually exist
import os
if os.path.exists('outputs'):
    files = os.listdir('outputs')
    print(f"Files in outputs directory: {len(files)}")
    for file in files:
        full_path = os.path.join('outputs', file)
        size = os.path.getsize(full_path)
        print(f"  📄 {file} ({size} bytes)")
    
    # Check specific files
    file1_exists = os.path.exists('outputs/comprehensive_plots.png')
    file2_exists = os.path.exists('outputs/product_plot.png')
    
    print()
    print("Specific file checks:")
    print(f"  comprehensive_plots.png exists: {file1_exists}")
    print(f"  product_plot.png exists: {file2_exists}")
    
else:
    print("❌ outputs directory doesn't exist!")

print("Generated comprehensive_plots.png and product_plot.png")
result = "Plots generated successfully"
"""
    
    print("\n🔍 Executing exact test code...")
    
    # Execute using new per-execution API
    response = requests.post(
        f"{base_url}/execute",
        data={"code": code},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Execution status: {data['status']}")
        print(f"   Workspace ID: {data['workspace_id']}")
        print(f"   Execution time: {data['execution_time']:.3f}s")
        
        print(f"\n📝 FULL CODE OUTPUT:")
        print("=" * 50)
        print(data['stdout'])
        print("=" * 50)
        
        if data['stderr']:
            print(f"\n⚠️ STDERR:")
            print(data['stderr'])
        
        print(f"\n📁 API DETECTED FILES: {len(data['output_files'])}")
        for i, file in enumerate(data['output_files'], 1):
            print(f"  {i}. 📄 {file['name']} ({file['size']} bytes, {file['mime_type']})")
            print(f"     Download URL: {file['download_url']}")
        
        # Expected vs actual
        expected_files = ['comprehensive_plots.png', 'product_plot.png']
        found_files = [f['name'] for f in data['output_files']]
        
        print(f"\n🎯 ANALYSIS:")
        print(f"Expected files: {expected_files}")
        print(f"Found files: {found_files}")
        missing_files = set(expected_files) - set(found_files)
        if missing_files:
            print(f"Missing files: {missing_files}")
        else:
            print("Missing files: None")
        
        if len(data['output_files']) == 2:
            print("\n✅ SUCCESS: Both plots created correctly!")
            
            # Try downloading both files to verify they're valid
            workspace_id = data['workspace_id']
            for file_info in data['output_files']:
                filename = file_info['name']
                print(f"\n⬇️ Downloading {filename}...")
                
                download_response = requests.get(
                    f"{base_url}/download/{workspace_id}/{filename}",
                    timeout=10
                )
                
                if download_response.status_code == 200:
                    print(f"✅ Download successful: {len(download_response.content)} bytes")
                    
                    # Verify it's a valid PNG
                    if download_response.content[:8] == b'\x89PNG\r\n\x1a\n':
                        print(f"✅ {filename} is a valid PNG file")
                    else:
                        print(f"❌ {filename} doesn't appear to be a valid PNG")
                else:
                    print(f"❌ Download failed: {download_response.status_code}")
        else:
            print(f"\n❌ FAILURE: Expected 2 plots, got {len(data['output_files'])}")
    
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
    print("🔍 Debug Two Plots Test - Per-Execution Workspaces")
    print("=" * 60)
    
    # Test server health first
    if test_server_health():
        print()
        debug_two_plots()
    else:
        print("\n❌ Server is not running. Please start it first:")
        print("   cd backend/aicore/code_executor")
        print("   python fastapi_server.py") 