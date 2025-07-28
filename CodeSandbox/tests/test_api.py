#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodeSandbox API Test

Comprehensive test script to demonstrate API functionality including
proper HTTP file download testing.
"""

import asyncio
import httpx
import json
from pathlib import Path
import tempfile
import os


BASE_URL = "http://localhost:8080/api/v1"


async def test_api():
    """Test the CodeSandbox API with comprehensive file download testing"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🧪 Testing CodeSandbox API - Full File Download Testing")
        print("=" * 60)
        
        # 1. Health check
        print("1️⃣  Health Check")
        response = await client.get(f"{BASE_URL}/health")
        print(f"   Status: {response.status_code}")
        health_data = response.json()
        print(f"   Jupyter Status: {health_data['jupyter_server_status']}")
        print(f"   Active Workspaces: {health_data['active_workspaces']}")
        assert response.status_code == 200, "Health check failed"
        print("   ✅ Health check passed")
        print()
        
        # 2. Create workspace
        print("2️⃣  Create Workspace")
        response = await client.post(
            f"{BASE_URL}/workspace/create",
            json={"ttl_hours": 2}
        )
        print(f"   Status: {response.status_code}")
        workspace_data = response.json()
        workspace_id = workspace_data["workspace_id"]
        print(f"   Workspace ID: {workspace_id}")
        print(f"   Status: {workspace_data['status']}")
        assert response.status_code == 200, "Workspace creation failed"
        print("   ✅ Workspace created successfully")
        print()
        
        # 3. Upload test file
        print("3️⃣  Upload Test File")
        test_csv_content = "name,age,city,salary\nAlice,25,NYC,75000\nBob,30,SF,95000\nCharlie,35,LA,85000\nDiana,28,Chicago,70000"
        files = {"file": ("test_data.csv", test_csv_content, "text/csv")}
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/upload",
            files=files
        )
        print(f"   Status: {response.status_code}")
        upload_result = response.json()
        print(f"   File: {upload_result['filename']} ({upload_result['size']} bytes)")
        print(f"   MIME Type: {upload_result['mime_type']}")
        print(f"   Download URL: {upload_result['download_url']}")
        
        # Validate download URL format (should be HTTP, not file://)
        download_url = upload_result['download_url']
        expected_url = f"/workspace/{workspace_id}/files/test_data.csv"
        assert download_url == expected_url, f"Expected {expected_url}, got {download_url}"
        print("   ✅ Download URL format correct (HTTP, not file://)")
        
        assert response.status_code == 200, "File upload failed"
        assert upload_result['size'] == len(test_csv_content.encode()), "File size mismatch"
        print("   ✅ File uploaded successfully")
        print()
        
        # 4. Test file download immediately after upload
        print("4️⃣  Test Uploaded File Download")
        download_response = await client.get(f"{BASE_URL}{download_url}")
        print(f"   Download Status: {download_response.status_code}")
        print(f"   Content-Type: {download_response.headers.get('content-type')}")
        print(f"   Content-Length: {download_response.headers.get('content-length')}")
        
        downloaded_content = download_response.content.decode('utf-8')
        print(f"   Downloaded Size: {len(downloaded_content)} chars")
        print(f"   Content Preview: {downloaded_content[:50]}...")
        
        assert download_response.status_code == 200, "File download failed"
        assert downloaded_content == test_csv_content, "Downloaded content doesn't match uploaded content"
        print("   ✅ File download successful and content verified")
        print()
        
        # 5. Execute code - Load and analyze data
        print("5️⃣  Execute Code - Load & Analyze Data")
        code1 = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('test_data.csv')
print(f"Loaded {len(df)} rows of data")
print("Data summary:")
print(df.head())
print(f"Average salary: ${df['salary'].mean():.2f}")

# Store result for API response
result = {
    "rows": len(df), 
    "columns": list(df.columns),
    "avg_salary": float(df['salary'].mean()),
    "cities": list(df['city'].unique())
}
print(f"Analysis complete: {result}")
"""
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/execute",
            data={"code": code1}
        )
        print(f"   Status: {response.status_code}")
        exec_result = response.json()
        print(f"   Execution Status: {exec_result['status']}")
        print(f"   Execution Time: {exec_result['execution_time_ms']}ms")
        print(f"   Stdout Lines: {len(exec_result['stdout'].splitlines()) if exec_result['stdout'] else 0}")
        
        if exec_result['result_data']:
            print(f"   Result Data: {exec_result['result_data']}")
        
        assert response.status_code == 200, "Code execution failed"
        assert exec_result['status'] == 'completed', f"Execution failed: {exec_result.get('stderr', 'Unknown error')}"
        
        # 🔍 CRITICAL TEST: Verify generated_files excludes uploaded files
        print(f"   Generated Files Count: {len(exec_result['generated_files'])}")
        generated_file_paths = [f['relative_path'] for f in exec_result['generated_files']]
        print(f"   Generated Files: {generated_file_paths}")
        
        # This execution only reads uploaded data, should generate NO files
        assert len(exec_result['generated_files']) == 0, f"Expected 0 generated files, got {len(exec_result['generated_files'])}: {generated_file_paths}"
        assert 'test_data.csv' not in generated_file_paths, "Uploaded file incorrectly included in generated_files"
        print("   ✅ Correctly excludes uploaded files from generated_files")
        
        print("   ✅ Data analysis code executed successfully")
        print()
        
        # 6. Execute code - Create multiple output files
        print("6️⃣  Execute Code - Create Visualizations")
        code2 = """
import matplotlib.pyplot as plt
import json

# Create salary bar chart
plt.figure(figsize=(10, 6))
plt.bar(df['name'], df['salary'], color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
plt.title('Salary Comparison by Employee', fontsize=16)
plt.xlabel('Employee Name')
plt.ylabel('Salary ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('outputs/salary_chart.png', dpi=150, bbox_inches='tight')
plt.close()

# Create age vs salary scatter plot
plt.figure(figsize=(8, 6))
plt.scatter(df['age'], df['salary'], c=['red', 'green', 'blue', 'orange'], s=100, alpha=0.7)
plt.title('Age vs Salary')
plt.xlabel('Age')
plt.ylabel('Salary ($)')
for i, name in enumerate(df['name']):
    plt.annotate(name, (df.iloc[i]['age'], df.iloc[i]['salary']), 
                xytext=(5, 5), textcoords='offset points')
plt.tight_layout()
plt.savefig('outputs/age_salary_scatter.png', dpi=150, bbox_inches='tight')
plt.close()

# Save summary data as JSON
summary = {
    "total_employees": len(df),
    "salary_stats": {
        "min": float(df['salary'].min()),
        "max": float(df['salary'].max()),
        "mean": float(df['salary'].mean()),
        "median": float(df['salary'].median())
    },
    "age_stats": {
        "min": int(df['age'].min()),
        "max": int(df['age'].max()),
        "mean": float(df['age'].mean())
    },
    "cities": list(df['city'].unique())
}

with open('outputs/summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("Created files:")
print("- outputs/salary_chart.png")
print("- outputs/age_salary_scatter.png")  
print("- outputs/summary.json")

result = {
    "plots_created": 2,
    "files_created": 3,
    "summary": summary
}
"""
        
        response = await client.post(
            f"{BASE_URL}/workspace/{workspace_id}/execute",
            data={"code": code2}
        )
        print(f"   Status: {response.status_code}")
        exec_result = response.json()
        print(f"   Execution Status: {exec_result['status']}")
        print(f"   Execution Time: {exec_result['execution_time_ms']}ms")
        print(f"   Generated Files: {len(exec_result['generated_files'])}")
        
        if exec_result['stdout']:
            print(f"   Output: {exec_result['stdout'].strip()}")
            
        assert response.status_code == 200, "Visualization code execution failed"
        assert exec_result['status'] == 'completed', f"Execution failed: {exec_result.get('stderr', 'Unknown error')}"
        
        # 🔍 CRITICAL TEST: Verify generated_files contains only code-created files
        print(f"   Generated Files Count: {len(exec_result['generated_files'])}")
        generated_file_paths = [f['relative_path'] for f in exec_result['generated_files']]
        print(f"   Generated Files: {generated_file_paths}")
        
        # This execution creates 3 files: 2 PNGs + 1 JSON
        expected_generated_files = ["outputs/salary_chart.png", "outputs/age_salary_scatter.png", "outputs/summary.json"]
        assert len(exec_result['generated_files']) == 3, f"Expected 3 generated files, got {len(exec_result['generated_files'])}: {generated_file_paths}"
        
        # Verify each expected file is in generated_files
        for expected_file in expected_generated_files:
            assert expected_file in generated_file_paths, f"Expected generated file {expected_file} not found in {generated_file_paths}"
        
        # Verify uploaded file is NOT in generated_files
        assert 'test_data.csv' not in generated_file_paths, "Uploaded file incorrectly included in generated_files"
        print("   ✅ Correctly includes only code-generated files")
        print("   ✅ Correctly excludes uploaded files from generated_files")
        
        print("   ✅ Visualization code executed successfully")
        print()
        
        # 7. List all workspace files
        print("7️⃣  List All Workspace Files")
        response = await client.get(f"{BASE_URL}/workspace/{workspace_id}/files")
        print(f"   Status: {response.status_code}")
        files_result = response.json()
        print(f"   Total Files: {files_result['total_files']}")
        print(f"   Total Size: {files_result['total_size_bytes']} bytes")
        
        expected_files = ["test_data.csv", "outputs/salary_chart.png", "outputs/age_salary_scatter.png", "outputs/summary.json"]
        found_files = []
        
        for file in files_result['files']:
            found_files.append(file['relative_path'])
            print(f"   📄 {file['filename']} - {file['relative_path']} ({file['size']} bytes)")
            print(f"      MIME: {file['mime_type']}")
            print(f"      Download: {file['download_url']}")
            
            # Validate download URL format
            expected_url = f"/workspace/{workspace_id}/files/{file['relative_path']}"
            assert file['download_url'] == expected_url, f"Invalid download URL for {file['filename']}"
        
        print(f"   Found files: {found_files}")
        for expected_file in expected_files:
            assert expected_file in found_files, f"Expected file {expected_file} not found"
        
        assert response.status_code == 200, "File listing failed"
        print("   ✅ All expected files found with correct download URLs")
        print()
        
        # 8. Test downloading each file type
        print("8️⃣  Test Downloading All File Types")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for file in files_result['files']:
                filename = file['filename']
                download_url = file['download_url']
                expected_size = file['size']
                
                print(f"   📥 Downloading {filename}...")
                download_response = await client.get(f"{BASE_URL}{download_url}")
                
                print(f"      Status: {download_response.status_code}")
                print(f"      Content-Type: {download_response.headers.get('content-type')}")
                print(f"      Content-Length: {download_response.headers.get('content-length')}")
                
                assert download_response.status_code == 200, f"Failed to download {filename}"
                
                # Verify file size
                downloaded_size = len(download_response.content)
                print(f"      Downloaded Size: {downloaded_size} bytes")
                assert downloaded_size == expected_size, f"Size mismatch for {filename}: expected {expected_size}, got {downloaded_size}"
                
                # Save file locally for verification
                local_path = Path(temp_dir) / filename
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(download_response.content)
                print(f"      ✅ Successfully downloaded and saved {filename}")
                
                # Additional validation based on file type
                if filename.endswith('.csv'):
                    content = download_response.content.decode('utf-8')
                    assert 'name,age,city,salary' in content, "CSV header missing"
                    assert 'Alice' in content, "CSV data missing"
                    print(f"      ✅ CSV content validated")
                    
                elif filename.endswith('.json'):
                    json_data = json.loads(download_response.content.decode('utf-8'))
                    assert 'total_employees' in json_data, "JSON structure invalid"
                    assert json_data['total_employees'] == 4, "JSON data invalid"
                    print(f"      ✅ JSON content validated")
                    
                elif filename.endswith('.png'):
                    # Check PNG header
                    assert download_response.content[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG header"
                    print(f"      ✅ PNG format validated")
        
        print("   ✅ All files downloaded and validated successfully")
        print()
        
        # 9. Test download edge cases
        print("9️⃣  Test Download Edge Cases")
        
        # Test non-existent file
        print("   Testing non-existent file download...")
        response = await client.get(f"{BASE_URL}/workspace/{workspace_id}/files/nonexistent.txt")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 404, "Expected 404 for non-existent file"
        print("   ✅ Non-existent file returns 404 correctly")
        
        # Test non-existent workspace
        print("   Testing download from non-existent workspace...")
        response = await client.get(f"{BASE_URL}/workspace/invalid_workspace/files/test.txt")
        print(f"   Status: {response.status_code}")
        assert response.status_code == 404, "Expected 404 for non-existent workspace"
        print("   ✅ Non-existent workspace returns 404 correctly")
        print()
        
        # 10. Get workspace info and system stats
        print("🔟 Final Workspace & System Status")
        
        # Workspace info
        response = await client.get(f"{BASE_URL}/workspace/{workspace_id}")
        workspace_info = response.json()
        print(f"   Workspace Status: {workspace_info['status']}")
        print(f"   Files Count: {workspace_info['files_count']}")
        print(f"   Total Size: {workspace_info['total_size_bytes']} bytes")
        
        # System stats
        response = await client.get(f"{BASE_URL}/stats")
        stats = response.json()
        print(f"   Active Workspaces: {stats['workspace_stats']['active_workspaces']}")
        print(f"   Total Executions: {stats['execution_stats']['total_executions']}")
        print(f"   Success Rate: {stats['execution_stats']['success_rate']}%")
        print()
        
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("✅ Workspace creation and management")
        print("✅ File upload with proper HTTP URLs") 
        print("✅ Code execution with pandas & matplotlib")
        print("✅ File generation (PNG, JSON)")
        print("✅ Generated files tracking (excludes uploaded files)")
        print("✅ Uploaded vs generated file distinction")
        print("✅ HTTP file downloads (all file types)")
        print("✅ Download URL format validation")
        print("✅ File content verification")
        print("✅ Error handling (404s)")
        print("✅ Architecture separation of concerns")
        print()
        print(f"🌐 Access workspace files: http://localhost:8080/api/v1/workspace/{workspace_id}/files")
        print(f"📚 API Documentation: http://localhost:8080/docs")
        print(f"🗂️  Workspace ID for manual testing: {workspace_id}")


if __name__ == "__main__":
    print("⏳ Starting comprehensive CodeSandbox API test...")
    print("💡 Make sure the server is running: python run_server.py")
    print()
    
    try:
        asyncio.run(test_api())
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("💡 Make sure the server is running: python run_server.py")
        exit(1) 