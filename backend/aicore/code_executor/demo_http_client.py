#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo HTTP client for the FastAPI Code Executor Service.
Demonstrates per-execution workspace usage with file uploads and downloads.
"""

import requests
import time
import io
from pathlib import Path
import json

# Configure matplotlib for headless operation
import matplotlib
matplotlib.use('Agg')

# Configuration
SERVER_URL = "http://localhost:8080"
TIMEOUT = 30

def demo_health_check():
    """Test server health."""
    print("🏥 Testing server health...")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy!")
            print(f"   Version: {data['version']}")
            print(f"   Active workspaces: {data['active_workspaces']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def demo_simple_code_execution():
    """Demo simple Python code execution."""
    print("\n🐍 Demo: Simple Code Execution")
    print("-" * 40)
    
    code = """
# Simple calculations and output
import math

print("Hello from the code executor!")
print(f"Python is running in workspace: {__import__('os').getcwd()}")

# Some calculations
numbers = [1, 2, 3, 4, 5]
sum_numbers = sum(numbers)
sqrt_sum = math.sqrt(sum_numbers)

print(f"Numbers: {numbers}")
print(f"Sum: {sum_numbers}")
print(f"Square root of sum: {sqrt_sum:.2f}")

result = {"sum": sum_numbers, "sqrt": sqrt_sum}
print(f"Final result: {result}")
"""
    
    try:
        print("Executing simple Python code...")
        start_time = time.time()
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TIMEOUT
        )
        
        execution_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Execution successful ({execution_time:.3f}s)")
            print(f"   Workspace ID: {data['workspace_id']}")
            print(f"   Server execution time: {data['execution_time']:.3f}s")
            print(f"   Output files: {len(data['output_files'])}")
            print(f"   Stdout:\n{data['stdout']}")
            return True
        else:
            print(f"❌ Execution failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Simple code execution error: {e}")
        return False

def demo_code_with_output_files():
    """Demo code execution that creates output files."""
    print("\n📁 Demo: Code with Output Files")
    print("-" * 40)
    
    code = """
import os
import json
import csv

# Create outputs directory
os.makedirs('outputs', exist_ok=True)

# Create a text file
with open('outputs/demo_output.txt', 'w') as f:
    f.write("This is a demo output file!\\n")
    f.write("Created by the FastAPI code executor.\\n")
    f.write("Timestamp: " + __import__('datetime').datetime.now().isoformat() + "\\n")

# Create a JSON file
data = {
    "demo": "output_files",
    "created_by": "fastapi_code_executor", 
    "file_count": 3,
    "items": ["file1.txt", "data.json", "results.csv"]
}

with open('outputs/demo_data.json', 'w') as f:
    json.dump(data, f, indent=2)

# Create a CSV file
csv_data = [
    ["name", "value", "category"],
    ["Item A", 100, "Category 1"],
    ["Item B", 150, "Category 2"], 
    ["Item C", 75, "Category 1"],
    ["Item D", 200, "Category 3"]
]

with open('outputs/demo_results.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(csv_data)

print("Created 3 output files:")
print("- demo_output.txt (text file)")
print("- demo_data.json (JSON data)")
print("- demo_results.csv (CSV data)")

# List created files with sizes
for filename in os.listdir('outputs'):
    filepath = os.path.join('outputs', filename)
    size = os.path.getsize(filepath)
    print(f"  {filename}: {size} bytes")
"""

    try:
        print("Executing code that creates output files...")
        
        response = requests.post(
            f"{SERVER_URL}/execute", 
            data={"code": code},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Execution successful!")
            print(f"   Workspace ID: {data['workspace_id']}")
            print(f"   Output files created: {len(data['output_files'])}")
            
            print(f"   Stdout:\n{data['stdout']}")
            
            # Display output files
            for file_info in data['output_files']:
                print(f"   📄 {file_info['name']}")
                print(f"      Size: {file_info['size']} bytes")
                print(f"      Type: {file_info['mime_type']}")
                print(f"      Download: {file_info['download_url']}")
            
            return True
        else:
            print(f"❌ Execution failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Output files demo error: {e}")
        return False

def demo_file_upload_and_processing():
    """Demo uploading files and processing them."""
    print("\n📤 Demo: File Upload and Processing")
    print("-" * 40)
    
    # Create sample CSV data
    csv_content = """name,age,department,salary
Alice Johnson,28,Engineering,85000
Bob Smith,34,Marketing,72000
Carol Davis,29,Engineering,88000
David Wilson,42,Sales,91000
Eva Brown,31,Marketing,67000
Frank Miller,38,Engineering,95000
Grace Lee,26,Sales,58000
Henry Taylor,45,Engineering,105000
"""
    
    # Code to process the uploaded file
    code = """
import pandas as pd
import matplotlib.pyplot as plt
import os

# Create outputs directory
os.makedirs('outputs', exist_ok=True)

# Read the uploaded CSV file
print("Reading employee data...")
df = pd.read_csv('inputs/employee_data.csv')
print(f"Loaded {len(df)} employee records")
print()
print("Data preview:")
print(df.head())

# Basic analysis
print()
print("📊 Analysis Results:")
avg_salary = df['salary'].mean()
max_salary = df['salary'].max()
min_salary = df['salary'].min()

print(f"Average salary: ${avg_salary:,.2f}")
print(f"Highest salary: ${max_salary:,.2f}")
print(f"Lowest salary: ${min_salary:,.2f}")

# Department statistics
dept_stats = df.groupby('department').agg({
    'salary': ['mean', 'count'],
    'age': 'mean'
}).round(2)

print()
print("🏢 Department Statistics:")
print(dept_stats)

# Create visualizations
# Salary by department
plt.figure(figsize=(10, 6))
df.boxplot(column='salary', by='department', ax=plt.gca())
plt.title('Salary Distribution by Department')
plt.suptitle('')  # Remove default title
plt.xlabel('Department')
plt.ylabel('Salary ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('outputs/salary_by_department.png', dpi=100, bbox_inches='tight')
plt.close()

# Age vs Salary scatter plot
plt.figure(figsize=(10, 6))
colors = {'Engineering': 'blue', 'Marketing': 'red', 'Sales': 'green'}
for dept in df['department'].unique():
    dept_data = df[df['department'] == dept]
    plt.scatter(dept_data['age'], dept_data['salary'], 
               label=dept, color=colors.get(dept, 'gray'), alpha=0.7)

plt.xlabel('Age')
plt.ylabel('Salary ($)')
plt.title('Age vs Salary by Department')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/age_vs_salary.png', dpi=100, bbox_inches='tight')
plt.close()

# Save processed data and summary
processed_df = df.copy()
processed_df['salary_category'] = pd.cut(processed_df['salary'], 
                                       bins=[0, 70000, 90000, float('inf')], 
                                       labels=['Low', 'Medium', 'High'])

processed_df.to_csv('outputs/processed_employees.csv', index=False)

# Save summary report
with open('outputs/analysis_summary.txt', 'w') as f:
    f.write("Employee Data Analysis Summary\\n")
    f.write("=" * 35 + "\\n\\n")
    f.write(f"Total employees: {len(df)}\\n")
    f.write(f"Average salary: ${avg_salary:,.2f}\\n")
    f.write(f"Salary range: ${min_salary:,.2f} - ${max_salary:,.2f}\\n\\n")
    f.write("Department breakdown:\\n")
    for dept in df['department'].unique():
        dept_df = df[df['department'] == dept]
        f.write(f"  {dept}: {len(dept_df)} employees, avg salary ${dept_df['salary'].mean():,.2f}\\n")

print()
print("✅ Analysis complete! Generated:")
print("- salary_by_department.png (box plot)")
print("- age_vs_salary.png (scatter plot)")
print("- processed_employees.csv (enhanced data)")
print("- analysis_summary.txt (summary report)")
"""
    
    try:
        print("Uploading employee data and processing...")
        
        # Prepare multipart form data
        files = {
            'files': ('employee_data.csv', csv_content, 'text/csv')
        }
        data = {
            'code': code
        }
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data=data,
            files=files,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result_data = response.json()
            print(f"✅ Processing successful!")
            print(f"   Workspace ID: {result_data['workspace_id']}")
            print(f"   Files generated: {len(result_data['output_files'])}")
            
            print(f"   Stdout:\n{result_data['stdout']}")
            
            # List generated files
            print("\n📁 Generated files:")
            for file_info in result_data['output_files']:
                print(f"   📄 {file_info['name']} ({file_info['size']} bytes)")
                print(f"      Type: {file_info['mime_type']}")
                print(f"      Download: {file_info['download_url']}")
            
            return True
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ File processing demo error: {e}")
        return False

def demo_plot_generation():
    """Demo advanced plot generation."""
    print("\n📊 Demo: Advanced Plot Generation")
    print("-" * 40)
    
    code = """
import matplotlib.pyplot as plt
import numpy as np
import os

# Create outputs directory
os.makedirs('outputs', exist_ok=True)

# Generate sample data
np.random.seed(42)  # For reproducible results
x = np.linspace(0, 4*np.pi, 100)
y1 = np.sin(x) + 0.1 * np.random.randn(100)
y2 = np.cos(x) + 0.1 * np.random.randn(100)

# Create a comprehensive plot
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('Advanced Plot Generation Demo', fontsize=16)

# Plot 1: Line plots with noise
axes[0, 0].plot(x, y1, 'b-', alpha=0.7, label='sin(x) + noise')
axes[0, 0].plot(x, y2, 'r-', alpha=0.7, label='cos(x) + noise')
axes[0, 0].plot(x, np.sin(x), 'b--', alpha=0.5, label='sin(x)')
axes[0, 0].plot(x, np.cos(x), 'r--', alpha=0.5, label='cos(x)')
axes[0, 0].set_title('Trigonometric Functions with Noise')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: Histogram
data = np.random.normal(100, 15, 1000)
axes[0, 1].hist(data, bins=30, alpha=0.7, color='green', edgecolor='black')
axes[0, 1].axvline(data.mean(), color='red', linestyle='--', 
                   label=f'Mean: {data.mean():.1f}')
axes[0, 1].set_title('Normal Distribution Histogram')
axes[0, 1].legend()

# Plot 3: Scatter plot with colors
n_points = 100
x_scatter = np.random.randn(n_points)
y_scatter = np.random.randn(n_points)
colors = np.random.rand(n_points)
sizes = 1000 * np.random.rand(n_points)

scatter = axes[1, 0].scatter(x_scatter, y_scatter, c=colors, s=sizes, 
                           alpha=0.6, cmap='viridis')
axes[1, 0].set_title('Colorful Scatter Plot')
plt.colorbar(scatter, ax=axes[1, 0])

# Plot 4: Bar chart
categories = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
values = [23, 45, 56, 78, 32]
colors_bar = ['red', 'green', 'blue', 'orange', 'purple']

bars = axes[1, 1].bar(categories, values, color=colors_bar, alpha=0.8)
axes[1, 1].set_title('Product Sales')
axes[1, 1].set_ylabel('Sales')
axes[1, 1].tick_params(axis='x', rotation=45)

# Add value labels on bars
for bar, value in zip(bars, values):
    height = bar.get_height()
    axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{value}', ha='center', va='bottom')

plt.tight_layout()
plt.savefig('outputs/comprehensive_analysis.png', dpi=150, bbox_inches='tight')
plt.close()

# Create a second plot - 3D surface
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Create 3D surface data
x_3d = np.linspace(-5, 5, 50)
y_3d = np.linspace(-5, 5, 50)
X, Y = np.meshgrid(x_3d, y_3d)
Z = np.sin(np.sqrt(X**2 + Y**2)) * np.exp(-0.1 * np.sqrt(X**2 + Y**2))

# Plot surface
surf = ax.plot_surface(X, Y, Z, cmap='coolwarm', alpha=0.8)
ax.contour(X, Y, Z, zdir='z', offset=-0.5, cmap='coolwarm', alpha=0.5)

ax.set_xlabel('X')
ax.set_ylabel('Y') 
ax.set_zlabel('Z')
ax.set_title('3D Surface: sin(r) * exp(-0.1*r)')

plt.colorbar(surf)
plt.savefig('outputs/3d_surface.png', dpi=150, bbox_inches='tight')
plt.close()

print("Generated advanced plots:")
print("- comprehensive_analysis.png (multi-subplot analysis)")  
print("- 3d_surface.png (3D surface plot)")
print("\\nPlot generation complete!")
"""
    
    try:
        print("Generating advanced plots...")
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Plot generation successful!")
            print(f"   Workspace ID: {data['workspace_id']}")
            print(f"   Plots created: {len(data['output_files'])}")
            
            print(f"   Stdout:\n{data['stdout']}")
            
            # Display plot files
            print("\n🎨 Generated plots:")
            for file_info in data['output_files']:
                if file_info['name'].endswith('.png'):
                    print(f"   🖼️  {file_info['name']} ({file_info['size']:,} bytes)")
                    print(f"       Download: {file_info['download_url']}")
            
            return True
        else:
            print(f"❌ Plot generation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Plot generation demo error: {e}")
        return False

def demo_error_handling():
    """Demo error handling."""
    print("\n⚠️  Demo: Error Handling")
    print("-" * 40)
    
    code = """
print("This part will work fine...")

# This will cause an error
import non_existent_module_that_does_not_exist

print("This part will never be reached")
"""
    
    try:
        print("Testing error handling with invalid code...")
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Error handling working correctly!")
            print(f"   Status: {data['status']}")
            print(f"   Workspace ID: {data['workspace_id']}")
            
            if data['status'] == 'error':
                print(f"   Error message: {data['error']}")
                print(f"   Stderr: {data['stderr']}")
                print(f"   Files created: {len(data['output_files'])} (should be 0)")
                return True
            else:
                print("❌ Expected error status but got success")
                return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error handling demo error: {e}")
        return False

def demo_workspace_list():
    """Demo listing active workspaces."""
    print("\n📋 Demo: List Active Workspaces")
    print("-" * 40)
    
    try:
        response = requests.get(f"{SERVER_URL}/workspaces", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Active workspaces: {data['active_workspaces']}")
            
            if data['workspaces']:
                print("   Recent workspaces:")
                for i, workspace in enumerate(data['workspaces'][:5]):  # Show first 5
                    print(f"   {i+1}. {workspace['workspace_id']}")
                    print(f"      Created: {workspace['created_at']}")
                    print(f"      Expires: {workspace['expires_at']}")
            else:
                print("   No active workspaces")
            
            return True
        else:
            print(f"❌ Workspace listing failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Workspace listing demo error: {e}")
        return False

def download_sample_file(workspace_id, filename):
    """Download a sample file from a workspace."""
    print(f"\n💾 Demo: Download File")
    print(f"Downloading {filename} from workspace {workspace_id}")
    
    try:
        download_url = f"{SERVER_URL}/download/{workspace_id}/{filename}"
        response = requests.get(download_url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            content = response.content
            print(f"✅ Downloaded {filename} ({len(content)} bytes)")
            
            # For text files, show preview
            if filename.endswith(('.txt', '.csv', '.json')):
                try:
                    text_content = content.decode('utf-8')
                    print("   Preview:")
                    lines = text_content.split('\n')[:5]  # First 5 lines
                    for line in lines:
                        print(f"   | {line}")
                    total_lines = len(text_content.split('\n'))
                    if len(lines) == 5 and total_lines > 5:
                        print(f"   | ... ({total_lines - 5} more lines)")
                except UnicodeDecodeError:
                    print("   (Binary file - no preview)")
            
            return True
        else:
            print(f"❌ Download failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Download demo error: {e}")
        return False

def main():
    """Run all demos."""
    print("🚀 FastAPI Code Executor - Demo Client")
    print("=" * 60)
    
    demos = [
        ("Health Check", demo_health_check),
        ("Simple Code Execution", demo_simple_code_execution),
        ("Code with Output Files", demo_code_with_output_files), 
        ("File Upload and Processing", demo_file_upload_and_processing),
        ("Advanced Plot Generation", demo_plot_generation),
        ("Error Handling", demo_error_handling),
        ("Workspace Listing", demo_workspace_list),
    ]
    
    results = []
    
    for demo_name, demo_func in demos:
        print(f"\n{'='*20} {demo_name} {'='*20}")
        try:
            success = demo_func()
            results.append((demo_name, success))
            if success:
                print(f"✅ {demo_name} completed successfully")
            else:
                print(f"❌ {demo_name} failed")
        except Exception as e:
            print(f"❌ {demo_name} error: {e}")
            results.append((demo_name, False))
        
        # Brief pause between demos
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEMO SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Completed: {passed}/{total} demos")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print("\nDetailed Results:")
    for demo_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {demo_name}")
    
    if passed == total:
        print("\n🎉 All demos completed successfully!")
        print("The FastAPI Code Executor is working perfectly!")
    else:
        print(f"\n⚠️  {total - passed} demos had issues.")
        print("Check the server logs for more details.")

if __name__ == "__main__":
    main() 