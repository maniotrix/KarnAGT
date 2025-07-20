#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo HTTP client for the FastAPI Code Executor Service.
Shows how to interact with the service programmatically.
"""

import requests
import json
import time
from pathlib import Path

class CodeExecutorClient:
    """Simple client for the Code Executor HTTP service."""
    
    def __init__(self, base_url="http://127.0.0.1:8081"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        """Check if the service is running."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def create_session(self):
        """Create a new execution session."""
        response = self.session.post(f"{self.base_url}/session")
        if response.status_code == 200:
            return response.json()["session_id"]
        raise Exception(f"Failed to create session: {response.status_code}")
    
    def upload_file(self, session_id, file_path, file_content):
        """Upload a file to a session."""
        files = {'files': (file_path, file_content)}
        response = self.session.post(
            f"{self.base_url}/session/{session_id}/upload",
            files=files
        )
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to upload file: {response.status_code}")
    
    def execute_code(self, code, session_id=None):
        """Execute Python code."""
        payload = {"code": code}
        if session_id:
            payload["session_id"] = session_id
            
        response = self.session.post(
            f"{self.base_url}/execute",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to execute code: {response.status_code}")
    
    def list_files(self, session_id):
        """List files in a session."""
        response = self.session.get(f"{self.base_url}/session/{session_id}/files")
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to list files: {response.status_code}")
    
    def download_file(self, session_id, file_type, filename):
        """Download a file from a session."""
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/download/{file_type}/{filename}"
        )
        if response.status_code == 200:
            return response.content
        raise Exception(f"Failed to download file: {response.status_code}")

def demo_basic_usage():
    """Demonstrate basic usage of the code executor service."""
    client = CodeExecutorClient()
    
    print("🚀 FastAPI Code Executor Service Demo")
    print("="*50)
    
    # Check if service is running
    if not client.health_check():
        print("❌ Service is not running!")
        print("Please start the service first:")
        print("  python fastapi_server.py")
        return
    
    print("✅ Service is running")
    
    # Create session
    print("\n📁 Creating session...")
    session_id = client.create_session()
    print(f"✅ Session created: {session_id}")
    
    # Execute simple code
    print("\n🐍 Executing simple Python code...")
    simple_code = """
result = "Hello from Code Executor!"
print(result)
print("Current time:", __import__('datetime').datetime.now())
"""
    
    result = client.execute_code(simple_code, session_id)
    print(f"✅ Execution successful:")
    print(f"   Status: {result['status']}")
    print(f"   Output: {result['stdout'].strip()}")
    print(f"   Time: {result['execution_time']:.3f}s")
    
    return session_id

def demo_file_processing():
    """Demonstrate file upload and processing."""
    client = CodeExecutorClient()
    
    print("\n📊 File Processing Demo")
    print("="*30)
    
    # Create session
    session_id = client.create_session()
    print(f"Session: {session_id}")
    
    # Create sample data
    csv_data = """name,age,department,salary
Alice Johnson,28,Engineering,75000
Bob Smith,35,Marketing,65000
Carol Davis,42,Engineering,85000
David Wilson,29,Sales,55000
Eve Brown,38,Marketing,70000"""
    
    print("\n📤 Uploading CSV data...")
    client.upload_file(session_id, "employees.csv", csv_data)
    print("✅ File uploaded")
    
    # Process the data
    print("\n⚙️ Processing data...")
    processing_code = """
import pandas as pd

# Load the data
df = pd.read_csv('inputs/employees.csv')
print(f"Loaded {len(df)} employee records")

# Basic analysis
print("\\nDepartment Summary:")
dept_summary = df.groupby('department').agg({
    'salary': ['mean', 'count'],
    'age': 'mean'
}).round(2)
print(dept_summary)

# Save results
df_sorted = df.sort_values('salary', ascending=False)
df_sorted.to_csv('outputs/employees_sorted.csv', index=False)

dept_summary.to_csv('outputs/department_summary.csv')

print(f"\\nHighest paid employee: {df_sorted.iloc[0]['name']} (${df_sorted.iloc[0]['salary']:,})")

result = {
    'total_employees': len(df),
    'avg_salary': df['salary'].mean(),
    'departments': df['department'].unique().tolist()
}
"""
    
    result = client.execute_code(processing_code, session_id)
    print("✅ Processing complete:")
    print(result['stdout'])
    
    # List output files
    files = client.list_files(session_id)
    print(f"\n📋 Output files created: {len(files['output_files'])}")
    for file in files['output_files']:
        print(f"   📄 {file['name']} ({file['size']} bytes)")
    
    return session_id

def demo_data_visualization():
    """Demonstrate data visualization."""
    client = CodeExecutorClient()
    
    print("\n📈 Data Visualization Demo")
    print("="*35)
    
    session_id = client.create_session()
    
    # Create visualization
    viz_code = """
import matplotlib
matplotlib.use('Agg')  # Ensure non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Generate sample data
np.random.seed(42)
categories = ['Product A', 'Product B', 'Product C', 'Product D', 'Product E']
q1_sales = np.random.randint(100, 500, 5)
q2_sales = np.random.randint(120, 550, 5)

# Create subplots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

# Bar chart comparison
x = np.arange(len(categories))
width = 0.35
ax1.bar(x - width/2, q1_sales, width, label='Q1', alpha=0.8)
ax1.bar(x + width/2, q2_sales, width, label='Q2', alpha=0.8)
ax1.set_xlabel('Products')
ax1.set_ylabel('Sales')
ax1.set_title('Quarterly Sales Comparison')
ax1.set_xticks(x)
ax1.set_xticklabels(categories, rotation=45)
ax1.legend()
ax1.grid(True, alpha=0.3)

# Pie chart for Q2
ax2.pie(q2_sales, labels=categories, autopct='%1.1f%%', startangle=90)
ax2.set_title('Q2 Sales Distribution')

# Line plot showing trends
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
trend_a = [150, 165, 180, 175, 190, 200]
trend_b = [120, 140, 155, 165, 180, 185]
ax3.plot(months, trend_a, 'o-', label='Product A', linewidth=2, markersize=6)
ax3.plot(months, trend_b, 's-', label='Product B', linewidth=2, markersize=6)
ax3.set_title('6-Month Sales Trends')
ax3.set_ylabel('Sales')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Scatter plot
x_scatter = np.random.normal(100, 15, 50)
y_scatter = x_scatter * 1.2 + np.random.normal(0, 10, 50)
ax4.scatter(x_scatter, y_scatter, alpha=0.6, s=60)
ax4.set_xlabel('Marketing Spend')
ax4.set_ylabel('Sales Revenue')
ax4.set_title('Marketing Spend vs Sales')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/comprehensive_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# Create summary report
report = f'''
Sales Analysis Report
====================
Q1 Total Sales: ${sum(q1_sales):,}
Q2 Total Sales: ${sum(q2_sales):,}
Growth: {((sum(q2_sales) - sum(q1_sales)) / sum(q1_sales) * 100):+.1f}%

Top Performer Q2: {categories[np.argmax(q2_sales)]} (${max(q2_sales):,})
'''

with open('outputs/sales_report.txt', 'w') as f:
    f.write(report)

print("📊 Comprehensive analysis complete!")
print(report)

result = "Analysis and visualizations created successfully"
"""
    
    result = client.execute_code(viz_code, session_id)
    print("✅ Visualization created:")
    print(result['stdout'])
    
    files = client.list_files(session_id)
    print(f"\n📁 Files created: {len(files['output_files'])}")
    for file in files['output_files']:
        print(f"   📄 {file['name']} ({file['size']} bytes, {file['mime_type']})")
    
    return session_id

def main():
    """Run all demos."""
    print("🎯 FastAPI Code Executor Service - Interactive Demo")
    print("="*60)
    
    try:
        # Basic demo
        session1 = demo_basic_usage()
        
        # File processing demo
        session2 = demo_file_processing()
        
        # Visualization demo
        session3 = demo_data_visualization()
        
        print("\n🎉 All demos completed successfully!")
        print(f"Sessions created: {session1}, {session2}, {session3}")
        print("\nYou can now:")
        print("- Access the API docs at: http://127.0.0.1:8080/docs")
        print("- Download files using the download endpoints")
        print("- Create your own sessions and run custom code")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure the FastAPI service is running:")
        print("  python fastapi_server.py")

if __name__ == "__main__":
    main() 