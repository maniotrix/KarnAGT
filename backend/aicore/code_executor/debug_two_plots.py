#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug script to test the exact matplotlib code that should create 2 plots.
"""

import requests
import json

def debug_two_plots():
    """Test the exact same code that should create 2 plots."""
    base_url = "http://127.0.0.1:8081"
    
    # Create session
    response = requests.post(f"{base_url}/session")
    if response.status_code != 200:
        print("Failed to create session")
        return
    
    session_id = response.json()["session_id"]
    print(f"Created session: {session_id}")
    
    # EXACT same code as the failing test
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

# Create sample data (same as original test)
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

print("\\n=== CREATING FIRST PLOT (comprehensive_plots.png) ===")

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

print("\\n=== CREATING SECOND PLOT (product_plot.png) ===")

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

print("\\n=== VERIFYING FILES ===")
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
    
    print(f"\\nSpecific file checks:")
    print(f"  comprehensive_plots.png exists: {file1_exists}")
    print(f"  product_plot.png exists: {file2_exists}")
    
else:
    print("❌ outputs directory doesn't exist!")

print("Generated comprehensive_plots.png and product_plot.png")
result = "Plots generated successfully"
"""
    
    # Execute the debug code
    payload = {
        "code": code,
        "session_id": session_id
    }
    
    print("\n🔍 Executing exact test code...")
    response = requests.post(
        f"{base_url}/execute",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Execution status: {data['status']}")
        print(f"Execution time: {data['execution_time']:.3f}s")
        
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
        
        # Expected vs actual
        expected_files = ['comprehensive_plots.png', 'product_plot.png']
        found_files = [f['name'] for f in data['output_files']]
        
        print(f"\n🎯 ANALYSIS:")
        print(f"Expected files: {expected_files}")
        print(f"Found files: {found_files}")
        print(f"Missing files: {set(expected_files) - set(found_files)}")
        
        if len(data['output_files']) == 2:
            print("✅ SUCCESS: Both plots created correctly!")
        else:
            print("❌ FAILURE: Expected 2 plots, got", len(data['output_files']))
    
    else:
        print(f"❌ Execution failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("🔍 Debug Two Plots Test")
    print("=" * 50)
    debug_two_plots() 