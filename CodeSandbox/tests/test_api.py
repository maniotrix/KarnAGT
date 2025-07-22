#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodeSandbox API Test

Simple test script to demonstrate the API functionality.
"""

import asyncio
import httpx
import json
from pathlib import Path


BASE_URL = "http://localhost:8080/api/v1"


async def test_api():
    """Test the CodeSandbox API"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing CodeSandbox API")
        print("=" * 50)
        
        # 1. Health check
        print("1️⃣  Health Check")
        response = await client.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 2. Create workspace
        print("2️⃣  Create Workspace")
        response = await client.post(
            f"{BASE_URL}/workspace/create",
            json={"ttl_hours": 1}
        )
        print(f"   Status: {response.status_code}")
        workspace_data = response.json()
        workspace_id = workspace_data["workspace_id"]
        print(f"   Workspace ID: {workspace_id}")
        print()
        
        # 3. Upload test file
        print("3️⃣  Upload Test File")
        test_csv = "name,age,city\nAlice,25,NYC\nBob,30,SF\nCharlie,35,LA"
        files = {"file": ("test_data.csv", test_csv, "text/csv")}
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/upload",
            files=files
        )
        print(f"   Status: {response.status_code}")
        upload_result = response.json()
        print(f"   File: {upload_result['filename']} ({upload_result['size']} bytes)")
        print(f"   Download URL: {upload_result['download_url']}")
        print()
        
        # 4. Execute code - Load and analyze data
        print("4️⃣  Execute Code - Load Data")
        code1 = """
import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('test_data.csv')
print(f"Loaded {len(df)} rows")
print(df.head())

result = {"rows": len(df), "columns": list(df.columns)}
"""
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/execute",
            data={"code": code1}
        )
        print(f"   Status: {response.status_code}")
        exec_result = response.json()
        print(f"   Stdout: {exec_result['stdout']}")
        print(f"   Result: {exec_result['result_data']}")
        print()
        
        # 5. Execute more code - Create visualization
        print("5️⃣  Execute Code - Create Plot")
        code2 = """
# Create a simple plot
plt.figure(figsize=(8, 6))
plt.bar(df['name'], df['age'])
plt.title('Age by Name')
plt.xlabel('Name')
plt.ylabel('Age')
plt.xticks(rotation=45)
plt.tight_layout()

# Save plot
plt.savefig('outputs/age_plot.png', dpi=150, bbox_inches='tight')
plt.close()

print("Plot saved to outputs/age_plot.png")
result = {"plot_created": True, "output_file": "age_plot.png"}
"""
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/execute",
            data={"code": code2}
        )
        print(f"   Status: {response.status_code}")
        exec_result = response.json()
        print(f"   Stdout: {exec_result['stdout']}")
        print(f"   Result: {exec_result['result_data']}")
        print(f"   Generated Files: {len(exec_result['generated_files'])}")
        print()
        
        # 6. List workspace files
        print("6️⃣  List Workspace Files")
        response = await client.get(f"{BASE_URL}/workspace/{workspace_id}/files")
        print(f"   Status: {response.status_code}")
        files_result = response.json()
        print(f"   Total Files: {files_result['total_files']}")
        for file in files_result['files']:
            print(f"   📄 {file['filename']} ({file['size']} bytes)")
            print(f"      Download: {file['download_url']}")
        print()
        
        # 7. Get workspace info
        print("7️⃣  Get Workspace Info")
        response = await client.get(f"{BASE_URL}/workspace/{workspace_id}")
        print(f"   Status: {response.status_code}")
        workspace_info = response.json()
        print(f"   Status: {workspace_info['status']}")
        print(f"   Files: {workspace_info['files_count']}")
        print(f"   Size: {workspace_info['total_size_bytes']} bytes")
        print()
        
        # 8. System stats
        print("8️⃣  System Statistics")
        response = await client.get(f"{BASE_URL}/stats")
        print(f"   Status: {response.status_code}")
        stats = response.json()
        print(f"   Active Workspaces: {stats['workspace_stats']['active_workspaces']}")
        print(f"   Total Executions: {stats['execution_stats']['total_executions']}")
        print(f"   Success Rate: {stats['execution_stats']['success_rate']}%")
        print()
        
        print("🎉 All tests completed successfully!")
        print(f"🌐 View files at: http://localhost:8888/tree/workspaces/{workspace_id}")
        print(f"📚 API Docs: http://localhost:8080/docs")


if __name__ == "__main__":
    print("⏳ Make sure the CodeSandbox server is running:")
    print("   python run_server.py")
    print()
    
    try:
        asyncio.run(test_api())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the server is running: python run_server.py") 