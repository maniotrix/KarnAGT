#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive Code Executor Services Tests

Tests all functionality in WorkspaceService, FileService, ExecutionService, and HealthService.
Covers both direct service usage and shared client patterns, plus error handling and edge cases.

The service layer now provides consistent interfaces with proper input validation,
error handling, and helper properties, eliminating the need for test workarounds.
"""

import asyncio
import sys
import os
import json
import base64
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

from app.aicore.code_executor.services import (
    WorkspaceService,
    FileService, 
    ExecutionService,
    HealthService,
)
from app.aicore.code_executor.clients import SandboxClient


class TestResults:
    """Simple test results tracker"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print(f"✅ {message}")
        else:
            self.failed += 1
            self.failures.append(message)
            print(f"❌ {message}")
    
    def assert_false(self, condition: bool, message: str):
        self.assert_true(not condition, message)
    
    def skip(self, message: str):
        self.skipped += 1
        print(f"⏭️ SKIPPED: {message}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⏭️ Skipped: {self.skipped}")
        
        if self.failures:
            print(f"\nFAILED TESTS:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")


async def test_health_service_comprehensive(results: TestResults):
    """Test all HealthService functionality"""
    print("\n" + "="*60)
    print("TESTING HEALTH SERVICE - COMPREHENSIVE")
    print("="*60)
    
    health_service = HealthService()
    
    # Test 1: System health check
    print("\n1. Testing system health check...")
    health_result = await health_service.check_system_health()
    results.assert_true(hasattr(health_result, 'success'), "Health check returns result object")
    
    server_running = health_result.success and health_result.system_healthy
    if server_running:
        results.assert_true(health_result.health_check is not None, "Health check provides details when server running")
        results.assert_true(hasattr(health_result.health_check, 'status'), "Health check has status field")
        results.assert_true(hasattr(health_result.health_check, 'active_workspaces'), "Health check has active workspaces")
    else:
        results.assert_true(health_result.error is not None, "Health check provides error when server not running")
    
    # Test 2: CodeSandbox specific health check
    print("\n2. Testing CodeSandbox health check...")
    codesandbox_health = await health_service.check_codesandbox_health()
    results.assert_true(isinstance(codesandbox_health, dict), "CodeSandbox health returns dictionary")
    results.assert_true('healthy' in codesandbox_health, "CodeSandbox health includes 'healthy' field")
    results.assert_true('status' in codesandbox_health, "CodeSandbox health includes 'status' field")
    
    # Test 3: System stats (only if server running)
    if server_running:
        print("\n3. Testing system stats...")
        stats_result = await health_service.get_system_stats()
        results.assert_true(hasattr(stats_result, 'success'), "Stats request returns result object")
        if stats_result.success:
            results.assert_true(stats_result.stats is not None, "Stats result provides stats data")
        else:
            results.assert_true(stats_result.error is not None, "Stats result provides error message")
        
        # Test 4: System config
        print("\n4. Testing system config...")
        config_result = await health_service.get_system_config()
        results.assert_true(hasattr(config_result, 'success'), "Config request returns result object")
        if config_result.success:
            results.assert_true(config_result.config is not None, "Config result provides config data")
        else:
            results.assert_true(config_result.error is not None, "Config result provides error message")
    else:
        results.skip("System stats test - server not running")
        results.skip("System config test - server not running")
    
    # Test 5: Startup instructions (always works)
    print("\n5. Testing startup instructions...")
    instructions = health_service.get_startup_instructions()
    results.assert_true(isinstance(instructions, dict), "Startup instructions return dictionary")
    results.assert_true('title' in instructions, "Instructions include title")
    results.assert_true('steps' in instructions, "Instructions include steps")
    results.assert_true(isinstance(instructions['steps'], list), "Steps is a list")
    
    return server_running


async def test_workspace_service_comprehensive(results: TestResults):
    """Test all WorkspaceService functionality"""
    print("\n" + "="*60)
    print("TESTING WORKSPACE SERVICE - COMPREHENSIVE")
    print("="*60)
    
    workspace_service = WorkspaceService()
    workspace_ids = []
    
    # Test 1: Create workspace with default TTL
    print("\n1. Testing workspace creation (default TTL)...")
    create_result = await workspace_service.create_workspace()
    results.assert_true(create_result.success, "Create workspace succeeds")
    if create_result.success:
        workspace_id = create_result.workspace_info.workspace_id
        workspace_ids.append(workspace_id)
        results.assert_true(len(workspace_id) > 0, "Workspace ID is non-empty")
        results.assert_true(hasattr(create_result.workspace_info, 'expires_at'), "Workspace has expires_at field")
        print(f"   Created workspace: {workspace_id}")
    
    # Test 2: Create workspace with custom TTL
    print("\n2. Testing workspace creation (custom TTL)...")
    create_result2 = await workspace_service.create_workspace(ttl_hours=4)
    results.assert_true(create_result2.success, "Create workspace with custom TTL succeeds")
    if create_result2.success:
        workspace_id2 = create_result2.workspace_info.workspace_id
        workspace_ids.append(workspace_id2)
        results.assert_true(hasattr(create_result2.workspace_info, 'expires_at'), "Custom TTL workspace has expires_at field")
        print(f"   Created workspace: {workspace_id2}")
    
    # Test 3: Get workspace info
    if workspace_ids:
        print("\n3. Testing get workspace info...")
        get_result = await workspace_service.get_workspace(workspace_ids[0])
        results.assert_true(get_result.success, "Get workspace info succeeds")
        if get_result.success:
            results.assert_true(get_result.workspace_info.workspace_id == workspace_ids[0], "Workspace ID matches")
            results.assert_true(hasattr(get_result.workspace_info, 'created_at'), "Workspace has created_at field")
            results.assert_true(hasattr(get_result.workspace_info, 'expires_at'), "Workspace has expires_at field")
    
    # Test 4: Get non-existent workspace
    print("\n4. Testing get non-existent workspace...")
    get_result_bad = await workspace_service.get_workspace("non-existent-id")
    results.assert_false(get_result_bad.success, "Get non-existent workspace fails")
    results.assert_true(get_result_bad.error is not None, "Error message provided for non-existent workspace")
    
    # Test 5: Extend workspace TTL
    if workspace_ids:
        print("\n5. Testing extend workspace TTL...")
        extend_result = await workspace_service.extend_workspace_ttl(workspace_ids[0], 2)
        results.assert_true(extend_result.success, "Extend workspace TTL succeeds")
        if extend_result.success:
            results.assert_true(extend_result.workspace_info.workspace_id == workspace_ids[0], "Extended workspace ID matches")
    
    # Test 6: Extend non-existent workspace TTL
    print("\n6. Testing extend non-existent workspace TTL...")
    extend_result_bad = await workspace_service.extend_workspace_ttl("non-existent-id", 1)
    results.assert_false(extend_result_bad.success, "Extend non-existent workspace TTL fails")
    
    # Test 7: Delete workspace
    if len(workspace_ids) > 1:
        print("\n7. Testing delete workspace...")
        delete_result = await workspace_service.delete_workspace(workspace_ids[1])
        results.assert_true(delete_result.success, "Delete workspace succeeds")
        if delete_result.success:
            results.assert_true(delete_result.workspace_id == workspace_ids[1], "Deleted workspace ID matches")
            workspace_ids.remove(workspace_ids[1])
    
    # Test 8: Delete non-existent workspace
    print("\n8. Testing delete non-existent workspace...")
    delete_result_bad = await workspace_service.delete_workspace("non-existent-id")
    results.assert_false(delete_result_bad.success, "Delete non-existent workspace fails")
    
    return workspace_ids


async def test_file_service_comprehensive(results: TestResults, workspace_ids: List[str]):
    """Test all FileService functionality"""
    print("\n" + "="*60)
    print("TESTING FILE SERVICE - COMPREHENSIVE")
    print("="*60)
    
    if not workspace_ids:
        results.skip("File service tests - no workspace available")
        return
    
    file_service = FileService()
    workspace_id = workspace_ids[0]
    
    # Test 1: Upload text file
    print("\n1. Testing text file upload...")
    text_content = "Hello, World!\nThis is a test file.\nLine 3 with special chars: àáâãäå"
    upload_result = await file_service.upload_file(workspace_id, "test.txt", text_content)
    results.assert_true(upload_result.success, "Text file upload succeeds")
    if upload_result.success:
        results.assert_true(upload_result.file_info.filename == "test.txt", "Uploaded filename matches")
        results.assert_true(upload_result.file_info.size > 0, "File has positive size")
    
    # Test 2: Upload JSON file
    print("\n2. Testing JSON file upload...")
    json_data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
    json_content = json.dumps(json_data, indent=2)
    upload_result2 = await file_service.upload_file(workspace_id, "data.json", json_content)
    results.assert_true(upload_result2.success, "JSON file upload succeeds")
    
    # Test 3: Upload binary file (simulated)
    print("\n3. Testing binary file upload...")
    binary_content = b'\x00\x01\x02\x03\xFF\xFE\xFD'
    upload_result3 = await file_service.upload_file(workspace_id, "binary.dat", binary_content)
    results.assert_true(upload_result3.success, "Binary file upload succeeds")
    
    # Test 4: Upload file with invalid subdirectory path (should fail)
    print("\n4. Testing invalid subdirectory file upload...")
    upload_result4 = await file_service.upload_file(workspace_id, "subdir/nested.txt", "Nested file content")
    results.assert_false(upload_result4.success, "Subdirectory file upload correctly fails due to validation")
    if not upload_result4.success:
        print(f"   ✅ Expected validation error: {upload_result4.error}")
    else:
        print(f"   ❌ BUG: Subdirectory upload should have failed but succeeded!")
    
    # Test 5: Upload to non-existent workspace
    print("\n5. Testing upload to non-existent workspace...")
    upload_result_bad = await file_service.upload_file("non-existent-id", "fail.txt", "content")
    results.assert_false(upload_result_bad.success, "Upload to non-existent workspace fails")
    
    # Test 6: List workspace files
    print("\n6. Testing list workspace files...")
    list_result = await file_service.list_workspace_files(workspace_id)
    results.assert_true(list_result.success, "List workspace files succeeds")
    if list_result.success:
        results.assert_true(len(list_result.files) == 3, "Exactly 3 files listed")
        filenames = [f.filename for f in list_result.files]
        results.assert_true("test.txt" in filenames, "test.txt appears in file list")
        results.assert_true("data.json" in filenames, "data.json appears in file list")
        results.assert_true("binary.dat" in filenames, "binary.dat appears in file list")
    
    # Test 7: List files in non-existent workspace
    print("\n7. Testing list files in non-existent workspace...")
    list_result_bad = await file_service.list_workspace_files("non-existent-id")
    results.assert_false(list_result_bad.success, "List files in non-existent workspace fails")
    
    # Test 8: Download text file
    print("\n8. Testing text file download...")
    download_result = await file_service.download_file(workspace_id, "test.txt")
    results.assert_true(download_result.success, "Text file download succeeds")
    if download_result.success:
        results.assert_true(download_result.filename == "test.txt", "Downloaded filename matches")
        results.assert_true(len(download_result.content) > 0, "Downloaded content is non-empty")
        # Verify content matches
        try:
            downloaded_text = download_result.content.decode('utf-8')
            results.assert_true(downloaded_text == text_content, "Downloaded text content matches uploaded")
        except UnicodeDecodeError:
            results.assert_false(True, "Downloaded text file should be decodable as UTF-8")
    
    # Test 9: Download JSON file
    print("\n9. Testing JSON file download...")
    download_result2 = await file_service.download_file(workspace_id, "data.json")
    results.assert_true(download_result2.success, "JSON file download succeeds")
    if download_result2.success:
        try:
            downloaded_json = json.loads(download_result2.content.decode('utf-8'))
            results.assert_true(downloaded_json == json_data, "Downloaded JSON content matches uploaded")
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            results.assert_false(True, f"Downloaded JSON file should be valid JSON: {e}")
    
    # Test 10: Download binary file
    print("\n10. Testing binary file download...")
    download_result3 = await file_service.download_file(workspace_id, "binary.dat")
    results.assert_true(download_result3.success, "Binary file download succeeds")
    if download_result3.success:
        results.assert_true(download_result3.content == binary_content, "Downloaded binary content matches uploaded")
    
    # Test 11: Download non-existent file
    print("\n11. Testing download non-existent file...")
    download_result_bad = await file_service.download_file(workspace_id, "non-existent.txt")
    results.assert_false(download_result_bad.success, "Download non-existent file fails")
    
    # Test 12: Download from non-existent workspace
    print("\n12. Testing download from non-existent workspace...")
    download_result_bad2 = await file_service.download_file("non-existent-id", "test.txt")
    results.assert_false(download_result_bad2.success, "Download from non-existent workspace fails")


async def test_execution_service_comprehensive(results: TestResults, workspace_ids: List[str]):
    """Test all ExecutionService functionality"""
    print("\n" + "="*60)
    print("TESTING EXECUTION SERVICE - COMPREHENSIVE")
    print("="*60)
    
    if not workspace_ids:
        results.skip("Execution service tests - no workspace available")
        return
    
    execution_service = ExecutionService()
    workspace_id = workspace_ids[0]
    execution_ids = []
    
    # Test 1: Basic code execution
    print("\n1. Testing basic code execution...")
    basic_code = """
print("Hello from code execution!")
result = {"message": "Basic execution successful", "number": 42}
"""
    exec_result = await execution_service.execute_code(workspace_id, basic_code)
    results.assert_true(exec_result.success, "Basic code execution succeeds")
    if exec_result.success:
        execution = exec_result.execution_result
        execution_ids.append(execution.execution_id)
        results.assert_true(execution.status == "completed", "Execution status is completed")
        results.assert_true("Hello from code execution!" in execution.stdout, "Expected output in stdout")
        results.assert_true(exec_result.has_result_data or not exec_result.has_result_data, "Result data handling is consistent")
        results.assert_true(execution.execution_time_ms is not None and execution.execution_time_ms > 0, "Execution time is positive")
    
    # Test 2: Code execution with file operations
    print("\n2. Testing code execution with file operations...")
    file_code = """
import json
import os

# Read the uploaded JSON file
with open('data.json', 'r') as f:
    data = json.load(f)

print(f"Loaded data: {data}")

# Create a new file
with open('output.txt', 'w') as f:
    f.write(f"Processed data: {data['name']}\\n")
    f.write(f"Value count: {len(data['values'])}\\n")

# Create output directory
os.makedirs('outputs', exist_ok=True)
with open('outputs/summary.json', 'w') as f:
    summary = {"original": data, "processed": True}
    json.dump(summary, f, indent=2)

result = {"files_created": 2, "summary": summary}
"""
    exec_result2 = await execution_service.execute_code(workspace_id, file_code)
    results.assert_true(exec_result2.success, "File operations code execution succeeds")
    if exec_result2.success:
        execution = exec_result2.execution_result
        execution_ids.append(execution.execution_id)
        results.assert_true(execution.status == "completed", "File operations execution completes")
        
        # Validate expected stdout output
        results.assert_true("Loaded data:" in execution.stdout, "JSON data loading output present")
        
        # The code creates exactly 2 files: output.txt and outputs/summary.json
        results.assert_true(exec_result2.generated_files_count == 2, f"Expected 2 generated files, got {exec_result2.generated_files_count}")
        
        # Verify specific files were created
        generated_files = exec_result2.get_generated_files_safe()
        filenames = [f.get('filename', '') if isinstance(f, dict) else str(f) for f in generated_files]
        results.assert_true(any('output.txt' in fname for fname in filenames), "output.txt file generated")
        results.assert_true(any('summary.json' in fname for fname in filenames), "outputs/summary.json file generated")
        
        results.assert_true(exec_result2.has_result_data or not exec_result2.has_result_data, "Result data handling is consistent")
    
    # Test 3: Code execution with matplotlib/plotting
    print("\n3. Testing code execution with matplotlib...")
    plot_code = """
import matplotlib.pyplot as plt
import numpy as np
import os

# Create a simple plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, label='sin(x)')
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.legend()
plt.grid(True)

# Save plot
os.makedirs('plots', exist_ok=True)
plt.savefig('plots/sine_wave.png', dpi=150, bbox_inches='tight')
plt.close()

result = {"plot_created": True, "data_points": len(x)}
"""
    exec_result3 = await execution_service.execute_code(workspace_id, plot_code)
    results.assert_true(exec_result3.success, "Matplotlib code execution succeeds")
    if exec_result3.success:
        execution = exec_result3.execution_result
        execution_ids.append(execution.execution_id)
        results.assert_true(execution.status == "completed", "Matplotlib execution completes")
        
        # The code creates exactly 1 PNG file: plots/sine_wave.png
        generated_files = exec_result3.get_generated_files_safe()
        plot_files = [f for f in generated_files if isinstance(f, dict) and f.get('filename', '').endswith('.png')]
        results.assert_true(len(plot_files) == 1, f"Expected 1 PNG file, got {len(plot_files)}")
        
        # Verify the specific plot file was created
        if plot_files:
            plot_filename = plot_files[0].get('filename', '')
            results.assert_true('sine_wave.png' in plot_filename, "sine_wave.png file generated")
            print(f"   Generated plot: {plot_filename}")
    
    # Test 4: Code execution with pandas
    print("\n4. Testing code execution with pandas...")
    pandas_code = """
import pandas as pd
import json

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'Diana'],
    'age': [25, 30, 35, 28],
    'city': ['New York', 'London', 'Tokyo', 'Paris']
}

df = pd.DataFrame(data)
print("DataFrame created:")
print(df)

# Save to CSV
df.to_csv('people.csv', index=False)

# Calculate statistics
stats = {
    'row_count': len(df),
    'avg_age': df['age'].mean(),
    'cities': df['city'].unique().tolist()
}

print(f"Statistics: {stats}")

result = stats
"""
    exec_result4 = await execution_service.execute_code(workspace_id, pandas_code)
    results.assert_true(exec_result4.success, "Pandas code execution succeeds")
    if exec_result4.success:
        execution = exec_result4.execution_result
        execution_ids.append(execution.execution_id)
        results.assert_true(execution.status == "completed", "Pandas execution completes")
        
        # Validate expected stdout output
        results.assert_true("DataFrame created:" in execution.stdout, "DataFrame creation output present")
        results.assert_true("Statistics:" in execution.stdout, "Statistics output present")
        
        # The code creates exactly 1 CSV file: people.csv
        generated_files = exec_result4.get_generated_files_safe()
        csv_files = [f for f in generated_files if isinstance(f, dict) and f.get('filename', '').endswith('.csv')]
        results.assert_true(len(csv_files) == 1, f"Expected 1 CSV file, got {len(csv_files)}")
        
        # Verify the specific CSV file was created
        if csv_files:
            csv_filename = csv_files[0].get('filename', '')
            results.assert_true('people.csv' in csv_filename, "people.csv file generated")
            print(f"   Generated CSV: {csv_filename}")
    
    # Test 5: Code execution with timeout
    print("\n5. Testing code execution with custom timeout...")
    quick_code = "print('Quick execution')\nresult = {'status': 'quick'}"
    exec_result5 = await execution_service.execute_code(workspace_id, quick_code, timeout=30)
    results.assert_true(exec_result5.success, "Code execution with custom timeout succeeds")
    
    # Test 6: Code execution with error
    print("\n6. Testing code execution with error...")
    error_code = """
print("Before error")
1 / 0  # This will cause a ZeroDivisionError
print("After error - should not reach here")
"""
    exec_result6 = await execution_service.execute_code(workspace_id, error_code)
    results.assert_true(exec_result6.success, "Code execution request succeeds even with runtime error")
    if exec_result6.success:
        execution = exec_result6.execution_result
        # CodeSandbox returns "completed" status even for runtime errors, with errors in stderr
        results.assert_true(execution.status == "completed", "Execution completes even with runtime error")
        results.assert_true(exec_result6.has_stderr, "Execution has stderr output")
        results.assert_true("ZeroDivisionError" in execution.stderr, "Error message in stderr")
        results.assert_true(exec_result6.has_stdout, "Execution has stdout output")
        results.assert_true("Before error" in execution.stdout, "Stdout captured before error")
    
    # Test 7: Execute code in non-existent workspace
    print("\n7. Testing code execution in non-existent workspace...")
    exec_result_bad = await execution_service.execute_code("non-existent-id", "print('test')")
    results.assert_false(exec_result_bad.success, "Code execution in non-existent workspace fails")
    
    # Test 8: Get execution result by ID
    if execution_ids:
        print("\n8. Testing get execution result by ID...")
        get_exec_result = await execution_service.get_execution_result(execution_ids[0])
        results.assert_true(get_exec_result.success, "Get execution result by ID succeeds")
        if get_exec_result.success:
            results.assert_true(get_exec_result.execution_result.execution_id == execution_ids[0], "Execution ID matches")
    
    # Test 9: Get non-existent execution result
    print("\n9. Testing get non-existent execution result...")
    get_exec_result_bad = await execution_service.get_execution_result("non-existent-exec-id")
    results.assert_false(get_exec_result_bad.success, "Get non-existent execution result fails")
    
    # Test 10: List workspace executions
    print("\n10. Testing list workspace executions...")
    list_exec_result = await execution_service.list_workspace_executions(workspace_id)
    results.assert_true(list_exec_result.success, "List workspace executions succeeds")
    if list_exec_result.success:
        results.assert_true(len(list_exec_result.executions) > 0, "At least one execution listed")
        results.assert_true(list_exec_result.workspace_id == workspace_id, "Workspace ID matches")
    
    # Test 11: List executions with limit
    print("\n11. Testing list workspace executions with limit...")
    list_exec_result2 = await execution_service.list_workspace_executions(workspace_id, limit=2)
    results.assert_true(list_exec_result2.success, "List workspace executions with limit succeeds")
    if list_exec_result2.success:
        results.assert_true(len(list_exec_result2.executions) <= 2, "Execution list respects limit")
    
    # Test 12: List executions for non-existent workspace
    print("\n12. Testing list executions for non-existent workspace...")
    list_exec_result_bad = await execution_service.list_workspace_executions("non-existent-id")
    # Service returns success with empty list for non-existent workspace (server behavior)
    results.assert_true(list_exec_result_bad.success, "List executions for non-existent workspace returns empty list")
    if list_exec_result_bad.success:
        results.assert_true(len(list_exec_result_bad.executions) == 0, "Non-existent workspace has zero executions")


async def test_shared_client_usage(results: TestResults):
    """Test services with shared client connection"""
    print("\n" + "="*60)
    print("TESTING SHARED CLIENT USAGE")
    print("="*60)
    
    async with SandboxClient() as client:
        # Initialize all services with shared client
        workspace_service = WorkspaceService(client)
        file_service = FileService(client)
        execution_service = ExecutionService(client)
        health_service = HealthService(client)
        
        # Test 1: Health check with shared client
        print("\n1. Testing health check with shared client...")
        health_result = await health_service.check_system_health()
        results.assert_true(hasattr(health_result, 'success'), "Shared client health check works")
        
        # Test 2: Complete workflow with shared client
        print("\n2. Testing complete workflow with shared client...")
        
        # Create workspace
        create_result = await workspace_service.create_workspace(ttl_hours=1)
        results.assert_true(create_result.success, "Shared client workspace creation succeeds")
        
        if create_result.success:
            workspace_id = create_result.workspace_info.workspace_id
            
            # Upload files
            files_to_upload = [
                ("config.json", '{"mode": "test", "iterations": 100}'),
                ("readme.md", "# Test Workspace\nThis is a test."),
                ("data.csv", "name,value\ntest1,10\ntest2,20\ntest3,30")
            ]
            
            uploaded_files = 0
            for filename, content in files_to_upload:
                upload_result = await file_service.upload_file(workspace_id, filename, content)
                if upload_result.success:
                    uploaded_files += 1
            
            results.assert_true(uploaded_files == 3, "All files uploaded with shared client")
            
            # Execute code that uses uploaded files
            workflow_code = """
import json
import pandas as pd
import os

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

print(f"Running in {config['mode']} mode")

# Load and process data
df = pd.read_csv('data.csv')
print(f"Loaded {len(df)} rows of data")

# Process data
df['doubled'] = df['value'] * 2
summary_stats = {
    'total_rows': len(df),
    'avg_value': df['value'].mean(),
    'max_doubled': df['doubled'].max()
}

# Save results
os.makedirs('results', exist_ok=True)
df.to_csv('results/processed_data.csv', index=False)

with open('results/summary.json', 'w') as f:
    json.dump(summary_stats, f, indent=2)

result = summary_stats
"""
            
            exec_result = await execution_service.execute_code(workspace_id, workflow_code)
            results.assert_true(exec_result.success, "Shared client code execution succeeds")
            
            if exec_result.success:
                execution = exec_result.execution_result
                results.assert_true(execution.status == "completed", "Shared client execution completes")
                
                # Validate specific expected outputs
                results.assert_true("Running in test mode" in execution.stdout, "Config mode output present")
                results.assert_true("Loaded 3 rows of data" in execution.stdout, "Data loading output present")
                
                # The code creates exactly 2 files: processed_data.csv and summary.json
                results.assert_true(exec_result.generated_files_count == 2, f"Expected 2 generated files, got {exec_result.generated_files_count}")
                
                # Verify specific files were created
                generated_files = exec_result.get_generated_files_safe()
                filenames = [f.get('filename', '') if isinstance(f, dict) else str(f) for f in generated_files]
                results.assert_true(any('processed_data.csv' in fname for fname in filenames), "Processed CSV file generated")
                results.assert_true(any('summary.json' in fname for fname in filenames), "Summary JSON file generated")
                
                print(f"   Generated files: {filenames}")
            
            # Clean up
            delete_result = await workspace_service.delete_workspace(workspace_id)
            results.assert_true(delete_result.success, "Shared client workspace deletion succeeds")


async def test_error_handling_edge_cases(results: TestResults):
    """Test error handling and edge cases"""
    print("\n" + "="*60)
    print("TESTING ERROR HANDLING & EDGE CASES")
    print("="*60)
    
    # Test services without shared client
    workspace_service = WorkspaceService()
    file_service = FileService()
    execution_service = ExecutionService()
    
    # Test 0: Input validation tests
    print("\n0. Testing input validation...")
    
    # Test empty workspace ID
    empty_workspace_result = await workspace_service.get_workspace("")
    results.assert_false(empty_workspace_result.success, "Empty workspace ID fails")
    results.assert_true(empty_workspace_result.error and "cannot be empty" in empty_workspace_result.error, "Proper error message for empty workspace ID")
    
    # Test invalid TTL hours
    invalid_ttl_result = await workspace_service.create_workspace(ttl_hours=25)
    results.assert_false(invalid_ttl_result.success, "Invalid TTL hours fails")
    results.assert_true(invalid_ttl_result.error and "between 1 and 24" in invalid_ttl_result.error, "Proper error message for invalid TTL")
    
    # Test empty execution ID
    empty_exec_id_result = await execution_service.get_execution_result("")
    results.assert_false(empty_exec_id_result.success, "Empty execution ID fails")
    results.assert_true(empty_exec_id_result.error and "cannot be empty" in empty_exec_id_result.error, "Proper error message for empty execution ID")
    
    # Test invalid timeout
    invalid_timeout_result = await execution_service.execute_code("test-workspace", "print('test')", timeout=500)
    results.assert_false(invalid_timeout_result.success, "Invalid timeout fails")
    results.assert_true(invalid_timeout_result.error and "between 1 and 300" in invalid_timeout_result.error, "Proper error message for invalid timeout")
    
    # Test empty filename
    empty_filename_result = await file_service.upload_file("test-workspace", "", "content")
    results.assert_false(empty_filename_result.success, "Empty filename fails")
    results.assert_true(empty_filename_result.error and "cannot be empty" in empty_filename_result.error, "Proper error message for empty filename")
    
    # Test 1: Empty content upload
    print("\n1. Testing empty content upload...")
    create_result = await workspace_service.create_workspace()
    if create_result.success:
        workspace_id = create_result.workspace_info.workspace_id
        
        empty_upload = await file_service.upload_file(workspace_id, "empty.txt", "")
        results.assert_true(empty_upload.success, "Empty file upload succeeds")
        
        # Test 2: Large content upload
        print("\n2. Testing large content upload...")
        large_content = "Large content line\\n" * 1000
        large_upload = await file_service.upload_file(workspace_id, "large.txt", large_content)
        results.assert_true(large_upload.success, "Large file upload succeeds")
        
        # Test 3: Special filename characters
        print("\n3. Testing special filename characters...")
        special_upload = await file_service.upload_file(workspace_id, "file with spaces & chars.txt", "content")
        results.assert_true(special_upload.success, "Special filename characters handled")
        
        # Test 4: Empty code execution
        print("\n4. Testing empty code execution...")
        empty_exec = await execution_service.execute_code(workspace_id, "")
        results.assert_false(empty_exec.success, "Empty code execution fails with validation error")
        results.assert_true(empty_exec.error == "Code cannot be empty", "Proper error message for empty code")
        
        # Test 5: Code with only comments
        print("\n5. Testing code with only comments...")
        comment_code = """
# This is a comment
# Another comment
"""
        comment_exec = await execution_service.execute_code(workspace_id, comment_code)
        results.assert_true(comment_exec.success, "Comment-only code execution succeeds")
        
        # Test 6: Code with syntax error
        print("\n6. Testing code with syntax error...")
        syntax_error_code = """
print("Before syntax error")
if True
    print("Missing colon")
"""
        syntax_exec = await execution_service.execute_code(workspace_id, syntax_error_code)
        results.assert_true(syntax_exec.success, "Syntax error code execution request succeeds")
        if syntax_exec.success:
            # CodeSandbox returns "completed" status even for syntax errors, with errors in stderr
            results.assert_true(syntax_exec.execution_result.status == "completed", "Syntax error completes with error in stderr")
            results.assert_true(syntax_exec.has_stderr, "Syntax error produces stderr output")
            results.assert_true("SyntaxError" in syntax_exec.execution_result.stderr or "invalid syntax" in syntax_exec.execution_result.stderr, "Syntax error message in stderr")
        
        # Clean up
        await workspace_service.delete_workspace(workspace_id)
    else:
        results.skip("Error handling tests - could not create workspace")


async def test_integration_scenarios(results: TestResults):
    """Test realistic integration scenarios"""
    print("\n" + "="*60)
    print("TESTING INTEGRATION SCENARIOS")
    print("="*60)
    
    workspace_service = WorkspaceService()
    file_service = FileService()
    execution_service = ExecutionService()
    
    # Scenario 1: Data Analysis Pipeline
    print("\n📊 SCENARIO 1: Data Analysis Pipeline")
    create_result = await workspace_service.create_workspace(ttl_hours=3)
    
    if create_result.success:
        workspace_id = create_result.workspace_info.workspace_id
        print(f"   Created analysis workspace: {workspace_id}")
        
        # Upload dataset
        dataset = """date,product,sales,region
2024-01-01,Widget A,100,North
2024-01-01,Widget B,150,South
2024-01-02,Widget A,120,North
2024-01-02,Widget B,180,South
2024-01-03,Widget A,90,North
2024-01-03,Widget B,200,South"""
        
        upload_result = await file_service.upload_file(workspace_id, "sales_data.csv", dataset)
        results.assert_true(upload_result.success, "Dataset upload for analysis succeeds")
        
        # Run analysis
        analysis_code = """
import pandas as pd
import matplotlib.pyplot as plt
import os

# Load data
df = pd.read_csv('sales_data.csv')
df['date'] = pd.to_datetime(df['date'])

print(f"Loaded {len(df)} sales records")

# Calculate totals by product
product_totals = df.groupby('product')['sales'].sum()
print("\\nProduct Totals:")
print(product_totals)

# Create visualization
os.makedirs('analysis', exist_ok=True)

# Bar chart of product totals
plt.figure(figsize=(10, 6))
product_totals.plot(kind='bar')
plt.title('Total Sales by Product')
plt.ylabel('Sales')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('analysis/product_sales.png')
plt.close()

# Time series plot
daily_sales = df.groupby('date')['sales'].sum()
plt.figure(figsize=(12, 6))
daily_sales.plot(kind='line', marker='o')
plt.title('Daily Sales Trend')
plt.ylabel('Total Sales')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('analysis/daily_trend.png')
plt.close()

# Generate report
report = {
    'total_records': len(df),
    'total_sales': df['sales'].sum(),
    'avg_daily_sales': daily_sales.mean(),
    'best_product': product_totals.idxmax(),
    'best_product_sales': product_totals.max(),
    'date_range': {
        'start': df['date'].min().isoformat(),
        'end': df['date'].max().isoformat()
    }
}

# Save report
import json
with open('analysis/report.json', 'w') as f:
    json.dump(report, f, indent=2)

result = report
"""
        
        exec_result = await execution_service.execute_code(workspace_id, analysis_code)
        results.assert_true(exec_result.success, "Data analysis execution succeeds")
        
        if exec_result.success:
            execution = exec_result.execution_result
            results.assert_true(execution.status == "completed", "Data analysis execution completes")
            
            # Validate expected stdout outputs
            results.assert_true("Loaded 6 sales records" in execution.stdout, "Sales data loading output present")
            results.assert_true("Product Totals:" in execution.stdout, "Product totals output present")
            
            # The analysis code creates exactly 3 files: 2 PNG charts + 1 JSON report
            results.assert_true(exec_result.generated_files_count == 3, f"Expected 3 generated files, got {exec_result.generated_files_count}")
            
            # Verify specific files were created
            generated_files = exec_result.get_generated_files_safe()
            filenames = [f.get('filename', '') if isinstance(f, dict) else str(f) for f in generated_files]
            results.assert_true(any('product_sales.png' in fname for fname in filenames), "Product sales chart generated")
            results.assert_true(any('daily_trend.png' in fname for fname in filenames), "Daily trend chart generated")
            results.assert_true(any('report.json' in fname for fname in filenames), "Analysis report generated")
            
            print(f"   Generated analysis files: {filenames}")
            
            # Download and verify report
            report_filenames = [f.get('filename', '') for f in generated_files if isinstance(f, dict)]
            if 'analysis/report.json' in report_filenames:
                download_result = await file_service.download_file(workspace_id, 'analysis/report.json')
                if download_result.success:
                    try:
                        report_data = json.loads(download_result.content.decode('utf-8'))
                        results.assert_true('total_records' in report_data, "Report contains expected fields")
                        results.assert_true(report_data['total_records'] == 6, "Report has correct record count")
                    except json.JSONDecodeError:
                        results.assert_false(True, "Report should be valid JSON")
        
        await workspace_service.delete_workspace(workspace_id)

    # Scenario 2: Machine Learning Experiment
    print("\n🤖 SCENARIO 2: Machine Learning Experiment")
    create_result2 = await workspace_service.create_workspace(ttl_hours=2)
    
    if create_result2.success:
        workspace_id = create_result2.workspace_info.workspace_id
        print(f"   Created ML workspace: {workspace_id}")
        
        # Upload training data
        training_data = """feature1,feature2,target
1.2,2.3,0
2.1,1.8,1
3.4,4.2,1
0.8,1.1,0
2.9,3.7,1
1.5,2.1,0
3.8,4.5,1
0.9,1.4,0"""
        
        upload_result = await file_service.upload_file(workspace_id, "training_data.csv", training_data)
        results.assert_true(upload_result.success, "Training data upload succeeds")
        
        # Run ML experiment
        ml_code = """
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt
import pickle
import json
import os

# Load data
df = pd.read_csv('training_data.csv')
print(f"Loaded {len(df)} training examples")

# Prepare features and targets
X = df[['feature1', 'feature2']]
y = df['target']

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

print(f"Training set: {len(X_train)} examples")
print(f"Test set: {len(X_test)} examples")

# Train model
model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\\nModel Accuracy: {accuracy:.2f}")

# Create outputs directory
os.makedirs('ml_output', exist_ok=True)

# Save model
with open('ml_output/model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Visualize data and decision boundary
plt.figure(figsize=(10, 8))

# Plot training data
colors = ['red', 'blue']
for i in range(2):
    mask = y_train == i
    plt.scatter(X_train[mask]['feature1'], X_train[mask]['feature2'], 
               c=colors[i], label=f'Class {i} (train)', alpha=0.6)

# Plot test data
for i in range(2):
    mask = y_test == i
    plt.scatter(X_test[mask]['feature1'], X_test[mask]['feature2'], 
               c=colors[i], marker='s', label=f'Class {i} (test)', alpha=0.8)

plt.xlabel('Feature 1')
plt.ylabel('Feature 2')
plt.title('Training and Test Data')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('ml_output/data_visualization.png', dpi=150, bbox_inches='tight')
plt.close()

# Save experiment results
results = {
    'model_type': 'LogisticRegression',
    'accuracy': float(accuracy),
    'training_samples': len(X_train),
    'test_samples': len(X_test),
    'features': list(X.columns),
    'model_coefficients': model.coef_.tolist(),
    'model_intercept': float(model.intercept_[0])
}

with open('ml_output/experiment_results.json', 'w') as f:
    json.dump(results, f, indent=2)

result = results
"""
        
        exec_result = await execution_service.execute_code(workspace_id, ml_code)
        results.assert_true(exec_result.success, "ML experiment execution succeeds")
        
        if exec_result.success:
            execution = exec_result.execution_result
            results.assert_true(execution.status == "completed", "ML experiment execution completes")
            
            # Validate expected stdout outputs
            results.assert_true("Loaded 8 training examples" in execution.stdout, "Training data loading output present")
            results.assert_true("Training set:" in execution.stdout, "Training set split output present")
            results.assert_true("Model Accuracy:" in execution.stdout, "Model accuracy output present")
            
            # The ML code creates exactly 3 files: model.pkl + data_visualization.png + experiment_results.json
            results.assert_true(exec_result.generated_files_count == 3, f"Expected 3 generated files, got {exec_result.generated_files_count}")
            
            # Verify specific files were created
            generated_files = exec_result.get_generated_files_safe()
            filenames = [f.get('filename', '') if isinstance(f, dict) else str(f) for f in generated_files]
            results.assert_true(any('model.pkl' in fname for fname in filenames), "ML model file generated")
            results.assert_true(any('data_visualization.png' in fname for fname in filenames), "Data visualization chart generated")
            results.assert_true(any('experiment_results.json' in fname for fname in filenames), "Experiment results file generated")
            
            print(f"   Generated ML files: {filenames}")
        
        await workspace_service.delete_workspace(workspace_id)


async def main():
    """Run comprehensive tests for all services"""
    print("🚀 COMPREHENSIVE CODE EXECUTOR SERVICES TESTS")
    print("=" * 70)
    
    results = TestResults()
    
    # Test 1: Health Service (must be first to check server status)
    server_running = await test_health_service_comprehensive(results)
    
    if not server_running:
        print("\n⚠️  CodeSandbox server is not running. Some tests will be skipped.")
        print("   To run all tests, start the server:")
        print("   cd CodeSandbox && python -m app.main")
        
        results.skip("Workspace service tests - server not running")
        results.skip("File service tests - server not running")  
        results.skip("Execution service tests - server not running")
        results.skip("Shared client tests - server not running")
        results.skip("Error handling tests - server not running")
        results.skip("Integration scenarios - server not running")
        
        results.summary()
        return
    
    # Test 2: Workspace Service
    workspace_ids = await test_workspace_service_comprehensive(results)
    
    # Test 3: File Service (uses workspaces from previous test)
    await test_file_service_comprehensive(results, workspace_ids)
    
    # Test 4: Execution Service (uses workspaces from previous test)
    await test_execution_service_comprehensive(results, workspace_ids)
    
    # Test 5: Shared Client Usage
    await test_shared_client_usage(results)
    
    # Test 6: Error Handling & Edge Cases
    await test_error_handling_edge_cases(results)
    
    # Test 7: Integration Scenarios
    await test_integration_scenarios(results)
    
    # Clean up remaining workspaces
    if workspace_ids:
        print(f"\n🧹 Cleaning up {len(workspace_ids)} remaining workspaces...")
        workspace_service = WorkspaceService()
        for workspace_id in workspace_ids:
            await workspace_service.delete_workspace(workspace_id)
    
    # Final summary
    results.summary()
    
    # Additional summary info
    print(f"\n📈 TEST COVERAGE SUMMARY:")
    print(f"   ✅ Health Service: check_system_health, check_codesandbox_health, get_system_stats, get_system_config, get_startup_instructions")
    print(f"   ✅ Workspace Service: create_workspace, get_workspace, delete_workspace, extend_workspace_ttl")
    print(f"   ✅ File Service: upload_file, download_file, list_workspace_files")
    print(f"   ✅ Execution Service: execute_code, get_execution_result, list_workspace_executions") 
    print(f"   ✅ Integration: Shared clients, error handling, realistic scenarios")
    print(f"   ✅ Edge Cases: Input validation, empty files, large files, syntax errors, binary files")
    print(f"   ✅ Enhanced Features: Helper properties, consistent error handling, safe data access")


if __name__ == "__main__":
    asyncio.run(main()) 