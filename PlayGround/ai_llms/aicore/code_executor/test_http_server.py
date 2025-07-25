#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test suite for the FastAPI code execution server with per-execution workspaces.
Tests HTTP-based code execution, file handling, and download functionality.
"""

import os
import sys
import time
import requests
import tempfile
from pathlib import Path
import json
import io

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, str(project_root))

from aicore.code_executor.logger import get_logger

# Configure matplotlib for headless operation
import matplotlib
matplotlib.use('Agg')

# Test configuration
SERVER_URL = "http://localhost:8080"
SERVER_TIMEOUT = 60  # seconds
TEST_TIMEOUT = 30   # seconds per HTTP request

logger = get_logger()

def check_server_health():
    """Check if the FastAPI server is running and healthy."""
    logger.info("🏥 Checking if FastAPI server is running...")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Server is healthy and ready for testing!")
            logger.info(f"   Status: {data['status']}")
            logger.info(f"   Version: {data['version']}")
            logger.info(f"   Active workspaces: {data['active_workspaces']}")
            return True
        else:
            logger.error(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to server. Is it running?")
        logger.error(f"   Expected server at: {SERVER_URL}")
        logger.error("   Start the server with: python fastapi_server.py")
        return False
    except Exception as e:
        logger.error(f"❌ Server health check error: {e}")
        return False

def test_health_check():
    """Test the health check endpoint."""
    logger.info("🧪 Testing health check endpoint...")
    
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=TEST_TIMEOUT)
        logger.info(f"Health check status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Service status: {data['status']}")
            logger.info(f"Version: {data['version']}")
            logger.info(f"Active workspaces: {data['active_workspaces']}")
            logger.info("✓ Health check successful")
            return True
        else:
            logger.error(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return False

def test_simple_code_execution():
    """Test basic Python code execution."""
    logger.info("🧪 Testing simple code execution...")
    
    try:
        # Simple Python code
        code = """
print("Hello, World!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        
        # Execute code
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Execution status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Stdout: {data['stdout']}")
            logger.info(f"Execution time: {data['execution_time']:.3f}s")
            logger.info(f"Workspace ID: {data['workspace_id']}")
            
            assert data["status"] == "success"
            assert "Hello, World!" in data["stdout"]
            assert "2 + 2 = 4" in data["stdout"]
            
            logger.info("✓ Simple code execution successful")
            return True
        else:
            logger.error(f"❌ Code execution failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Simple code execution error: {e}")
        return False

def test_code_with_output_file():
    """Test code execution that creates output files."""
    logger.info("🧪 Testing code execution with output file creation...")
    
    try:
        # Code that creates an output file
        code = """
import os

# Create outputs directory if it doesn't exist
os.makedirs('outputs', exist_ok=True)

# Write to output file
with open('outputs/test_result.txt', 'w') as f:
    f.write('This is a test output file\\n')
    f.write('Created from Python code\\n')
    f.write('File size should be small\\n')

print("Output file created successfully")
"""
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Execution status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Output files count: {len(data['output_files'])}")
            
            assert data["status"] == "success"
            assert "Output file created successfully" in data["stdout"]
            assert len(data["output_files"]) == 1
            
            # Check output file details
            output_file = data["output_files"][0]
            assert output_file["name"] == "test_result.txt"
            # New server response no longer includes 'relative_path'; validate download_url instead
            assert output_file["download_url"].endswith("/test_result.txt")
            assert "download_url" in output_file
            assert output_file["size"] > 0
            
            # Test downloading the file
            # Server now returns an absolute download_url; prepend host only if needed
            download_url = output_file["download_url"]
            download_response = requests.get(download_url, timeout=TEST_TIMEOUT)
            
            if download_response.status_code == 200:
                file_content = download_response.text
                assert "This is a test output file" in file_content
                logger.info("✓ File download successful")
            else:
                logger.error(f"❌ File download failed: {download_response.status_code}")
                return False
            
            logger.info("✓ Code execution with output file successful")
            return True
        else:
            logger.error(f"❌ Code execution failed with status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Code execution with output file error: {e}")
        return False

def test_file_upload_and_processing():
    """Test uploading files and processing them in code."""
    logger.info("🧪 Testing file upload and processing...")
    
    try:
        # Create a test CSV file
        csv_content = """name,age,city
Alice,25,New York
Bob,30,San Francisco
Charlie,35,Chicago
Diana,28,Boston
"""
        
        # Code that processes the uploaded file
        code = """
import pandas as pd
import os

# Read the uploaded CSV file
df = pd.read_csv('inputs/test_data.csv')
print(f"Loaded CSV with {len(df)} rows")
print("Data preview:")
print(df.head())

# Process the data
avg_age = df['age'].mean()
print(f"Average age: {avg_age:.1f}")

# Create output files
os.makedirs('outputs', exist_ok=True)

# Save processed data
df_processed = df.copy()
df_processed['age_category'] = df['age'].apply(lambda x: 'Young' if x < 30 else 'Mature')

df_processed.to_csv('outputs/processed_data.csv', index=False)
print("Processed data saved to outputs/processed_data.csv")

# Save summary
with open('outputs/summary.txt', 'w') as f:
    f.write(f"Data Summary\\n")
    f.write(f"Total records: {len(df)}\\n")
    f.write(f"Average age: {avg_age:.1f}\\n")
    f.write(f"Cities: {', '.join(df['city'].unique())}\\n")

print("Summary saved to outputs/summary.txt")
"""
        
        # Prepare multipart form data
        files = {
            'files': ('test_data.csv', csv_content, 'text/csv')
        }
        data = {
            'code': code
        }
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data=data,
            files=files,
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Execution status: {response.status_code}")
        
        if response.status_code == 200:
            result_data = response.json()
            logger.info(f"Result status: {result_data['status']}")
            logger.info(f"Output files count: {len(result_data['output_files'])}")
            
            assert result_data["status"] == "success"
            assert "Loaded CSV with 4 rows" in result_data["stdout"]
            assert "Average age: 29.5" in result_data["stdout"]
            assert len(result_data["output_files"]) == 2
            
            # Check that we have both output files
            output_filenames = [f["name"] for f in result_data["output_files"]]
            assert "processed_data.csv" in output_filenames
            assert "summary.txt" in output_filenames
            
            logger.info("✓ File upload and processing successful")
            return True
        else:
            logger.error(f"❌ File upload and processing failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ File upload and processing error: {e}")
        return False

def test_plot_generation():
    """Test matplotlib plot generation."""
    logger.info("🧪 Testing plot generation...")
    
    try:
        # Code that generates matplotlib plots
        code = """
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import os

# Create outputs directory
os.makedirs('outputs', exist_ok=True)

# Generate sample data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create first plot
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='sin(x)', color='blue')
plt.plot(x, y2, label='cos(x)', color='red')
plt.xlabel('X values')
plt.ylabel('Y values')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True)
plt.savefig('outputs/trig_plot.png', dpi=100, bbox_inches='tight')
plt.close()

# Create second plot  
plt.figure(figsize=(8, 6))
categories = ['A', 'B', 'C', 'D', 'E']
values = [23, 45, 56, 78, 32]
plt.bar(categories, values, color=['red', 'green', 'blue', 'orange', 'purple'])
plt.title('Sample Bar Chart')
plt.xlabel('Categories')
plt.ylabel('Values')
plt.savefig('outputs/bar_chart.png', dpi=100, bbox_inches='tight')
plt.close()

print("Generated trig_plot.png and bar_chart.png")
"""
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Execution status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Stdout: {data['stdout']}")
            logger.info(f"Total output files: {len(data['output_files'])}")
            
            # Log details of each output file
            for file_info in data["output_files"]:
                logger.info(f"File: {file_info['name']} ({file_info['size']} bytes) - {file_info['mime_type']}")
            
            assert data["status"] == "success"
            assert "Generated trig_plot.png and bar_chart.png" in data["stdout"]
            
            # Check for PNG files
            png_files = [f for f in data["output_files"] if f["name"].endswith('.png')]
            logger.info(f"PNG files found: {len(png_files)}")
            
            assert len(png_files) == 2, f"Expected 2 PNG files, got {len(png_files)}"
            
            # Verify file names
            png_names = [f["name"] for f in png_files]
            assert "trig_plot.png" in png_names
            assert "bar_chart.png" in png_names
            
            logger.info("✓ Plot generation successful")
            return True
        else:
            logger.error(f"❌ Plot generation failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Plot generation error: {e}")
        return False

def test_error_handling():
    """Test error handling for invalid code."""
    logger.info("🧪 Testing error handling...")
    
    try:
        # Code with syntax error
        code = """
print("This will work")
print("But this has a syntax error:
invalid_syntax_here
"""
        
        response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Execution status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Error: {data.get('error', 'No error message')}")
            
            assert data["status"] == "error"
            assert data["error"] is not None
            assert len(data["output_files"]) == 0  # No files should be created
            
            logger.info("✓ Error handling successful")
            return True
        else:
            logger.error(f"❌ Error handling test failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error handling test error: {e}")
        return False

def test_workspace_isolation():
    """Test that workspaces are properly isolated."""
    logger.info("🧪 Testing workspace isolation...")
    
    try:
        # First execution creates a file
        code1 = """
import os
os.makedirs('outputs', exist_ok=True)
with open('outputs/workspace1.txt', 'w') as f:
    f.write('This is from workspace 1')
print("Created workspace1.txt")
"""
        
        response1 = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code1},
            timeout=TEST_TIMEOUT
        )
        
        # Second execution tries to read the file from first execution
        code2 = """
import os
if os.path.exists('outputs/workspace1.txt'):
    print("ERROR: Found file from previous workspace!")
    with open('outputs/workspace1.txt', 'r') as f:
        print(f"Content: {f.read()}")
else:
    print("Good: Previous workspace file not found")
    os.makedirs('outputs', exist_ok=True)
    with open('outputs/workspace2.txt', 'w') as f:
        f.write('This is from workspace 2')
    print("Created workspace2.txt")
"""
        
        response2 = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code2},
            timeout=TEST_TIMEOUT
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            
            logger.info(f"Workspace 1 ID: {data1['workspace_id']}")
            logger.info(f"Workspace 2 ID: {data2['workspace_id']}")
            
            # Workspaces should be different
            assert data1["workspace_id"] != data2["workspace_id"]
            
            # Both should succeed
            assert data1["status"] == "success"
            assert data2["status"] == "success"
            
            # Second execution should not see first execution's files
            assert "Good: Previous workspace file not found" in data2["stdout"]
            assert "ERROR: Found file from previous workspace!" not in data2["stdout"]
            
            # Each should have their own output file
            assert len(data1["output_files"]) == 1
            assert len(data2["output_files"]) == 1
            assert data1["output_files"][0]["name"] == "workspace1.txt"
            assert data2["output_files"][0]["name"] == "workspace2.txt"
            
            logger.info("✓ Workspace isolation successful")
            return True
        else:
            logger.error("❌ Workspace isolation test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Workspace isolation test error: {e}")
        return False

def test_list_workspaces():
    """Test listing active workspaces."""
    logger.info("🧪 Testing workspace listing...")
    
    try:
        # Create a workspace by executing code
        code = """
import os
os.makedirs('outputs', exist_ok=True)
with open('outputs/test.txt', 'w') as f:
    f.write('test')
print("Workspace created")
"""
        
        exec_response = requests.post(
            f"{SERVER_URL}/execute",
            data={"code": code},
            timeout=TEST_TIMEOUT
        )
        
        if exec_response.status_code != 200:
            logger.error("Failed to create workspace")
            return False
        
        # List workspaces
        list_response = requests.get(f"{SERVER_URL}/workspaces", timeout=TEST_TIMEOUT)
        
        if list_response.status_code == 200:
            data = list_response.json()
            logger.info(f"Active workspaces: {data['active_workspaces']}")
            
            assert data["active_workspaces"] >= 1
            assert len(data["workspaces"]) >= 1
            
            # Check workspace details
            workspace_info = data["workspaces"][0]
            assert "workspace_id" in workspace_info
            assert "created_at" in workspace_info
            assert "expires_at" in workspace_info
            
            logger.info("✓ Workspace listing successful")
            return True
        else:
            logger.error(f"❌ Workspace listing failed: {list_response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Workspace listing test error: {e}")
        return False

def test_system_command():
    """Test system command execution with security filtering."""
    logger.info("🧪 Testing system command execution...")
    
    try:
        # Test 1: Valid command (should succeed)
        logger.info("Testing valid command: python --version")
        
        valid_command_payload = {
            "command": "python --version",
            "allowed_prefixes": ["python ", "pip ", "python -m "]
        }
        
        response = requests.post(
            f"{SERVER_URL}/system-command",
            json=valid_command_payload,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Valid command status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Exit code: {data['exit_code']}")
            logger.info(f"Stdout: {data['stdout'][:100]}...")  # First 100 chars
            logger.info(f"Workspace ID: {data['workspace_id']}")
            logger.info(f"Execution time: {data['execution_time']:.3f}s")
            
            assert data["status"] == "success"
            assert data["exit_code"] == 0
            assert data["command"] == "python --version"
            assert "Python" in data["stdout"] or "Python" in data["stderr"]  # Version info
            assert "workspace_id" in data
            assert "execution_id" in data
            
            logger.info("✓ Valid command execution successful")
        else:
            logger.error(f"❌ Valid command failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
        # Test 2: Invalid command (should be blocked)
        logger.info("Testing invalid command: rm -rf /")
        
        invalid_command_payload = {
            "command": "rm -rf /",  # This should be blocked
            "allowed_prefixes": ["python ", "pip ", "python -m "]
        }
        
        response = requests.post(
            f"{SERVER_URL}/system-command",
            json=invalid_command_payload,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Invalid command status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Exit code: {data['exit_code']}")
            logger.info(f"Stderr: {data['stderr']}")
            
            assert data["status"] == "error"
            assert data["exit_code"] == 1
            assert "Command not allowed" in data["stderr"]
            
            logger.info("✓ Invalid command properly blocked")
        else:
            logger.error(f"❌ Invalid command test failed: {response.status_code}")
            return False
        
        # Test 3: Pip list command (should work)
        logger.info("Testing pip command: pip list")
        
        pip_command_payload = {
            "command": "pip list",
            "allowed_prefixes": ["python ", "pip ", "python -m "]
        }
        
        response = requests.post(
            f"{SERVER_URL}/system-command",
            json=pip_command_payload,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Pip command status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Exit code: {data['exit_code']}")
            logger.info(f"Stdout length: {len(data['stdout'])} chars")
            
            # pip list should succeed and return package list
            assert data["status"] == "success"
            assert data["exit_code"] == 0
            assert len(data["stdout"]) > 0  # Should have some output
            
            logger.info("✓ Pip command execution successful")
        else:
            logger.error(f"❌ Pip command failed: {response.status_code}")
            return False
        
        # Test 4: Command with default allowed prefixes (no explicit prefixes)
        logger.info("Testing command with default allowed prefixes")
        
        default_command_payload = {
            "command": "python -c \"print('Hello from system command!')\""
            # No allowed_prefixes - should use defaults
        }
        
        response = requests.post(
            f"{SERVER_URL}/system-command",
            json=default_command_payload,
            headers={"Content-Type": "application/json"},
            timeout=TEST_TIMEOUT
        )
        
        logger.info(f"Default prefixes command status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Result status: {data['status']}")
            logger.info(f"Stdout: {data['stdout']}")
            
            assert data["status"] == "success"
            assert data["exit_code"] == 0
            assert "Hello from system command!" in data["stdout"]
            
            logger.info("✓ Default allowed prefixes working")
        else:
            logger.error(f"❌ Default prefixes command failed: {response.status_code}")
            return False
        
        logger.info("✓ System command execution tests successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ System command execution test error: {e}")
        return False

def run_all_tests():
    """Run all tests against the running FastAPI server."""
    logger.info("🚀 Starting FastAPI Code Executor Tests")
    logger.info("=" * 60)
    
    # Check server health first
    if not check_server_health():
        logger.error("❌ Server is not running or not healthy. Please start it first:")
        logger.error("   cd backend/aicore/code_executor")
        logger.error("   python fastapi_server.py")
        return False
    
    # Define all tests
    tests = [
        ("Health Check", test_health_check),
        ("Simple Code Execution", test_simple_code_execution),
        ("Code with Output File", test_code_with_output_file),
        ("File Upload and Processing", test_file_upload_and_processing),
        ("Plot Generation", test_plot_generation),
        ("Error Handling", test_error_handling),
        ("Workspace Isolation", test_workspace_isolation),
        ("System Command Execution", test_system_command),
        ("List Workspaces", test_list_workspaces),
    ]
    
    # Run tests
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info("-" * 40)
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Brief pause between tests
        time.sleep(0.5)
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"📊 TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! FastAPI server is working perfectly.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Check logs for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 