#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example Usage of Code Executor Tools

Demonstrates both direct service usage and LLM tool usage patterns.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

from app.aicore.code_executor.services import (
    # Services for direct usage
    WorkspaceService,
    FileService, 
    ExecutionService,
    HealthService,
)

from app.aicore.code_executor.clients import SandboxClient


async def example_direct_service_usage():
    """Example: Using services directly (no decorators)"""
    print("=== Direct Service Usage ===")
    
    # Create services
    workspace_service = WorkspaceService()
    file_service = FileService()
    execution_service = ExecutionService()
    
    # Create workspace
    workspace_result = await workspace_service.create_workspace(ttl_hours=2)
    if not workspace_result.success:
        print(f"Failed to create workspace: {workspace_result.error}")
        return
    
    workspace_id = workspace_result.workspace_info.workspace_id
    print(f"Created workspace: {workspace_id}")
    
    # Upload a file
    csv_data = "name,age\nAlice,25\nBob,30"
    upload_result = await file_service.upload_file(workspace_id, "data.csv", csv_data)
    if upload_result.success:
        print(f"Uploaded file: {upload_result.file_info.filename}")
    
    # Execute code
    code = """
import pandas as pd
import matplotlib.pyplot as plt
import os

# Read the uploaded data
df = pd.read_csv('data.csv')
print(f"Loaded {len(df)} rows")

# Create a simple plot
os.makedirs('outputs', exist_ok=True)
plt.figure(figsize=(8, 6))
plt.bar(df['name'], df['age'])
plt.title('Age by Name')
plt.savefig('outputs/age_chart.png')
plt.close()

# Set result
result = {"rows": len(df), "chart_created": True}
"""
    
    exec_result = await execution_service.execute_code(workspace_id, code)
    if exec_result.success:
        execution = exec_result.execution_result
        print(f"Code executed successfully in {execution.execution_time_ms}ms")
        print(f"Generated {len(execution.generated_files)} files")
        if execution.result_data:
            print(f"Result: {execution.result_data}")
    else:
        print(f"Code execution failed: {exec_result.error}")
        return
    
    # Clean up
    delete_result = await workspace_service.delete_workspace(workspace_id)
    if delete_result.success:
        print(f"Workspace deleted: {workspace_id}")


async def example_shared_client_usage():
    """Example: Using services with shared client connection"""
    print("\n=== Shared Client Usage ===")
    
    async with SandboxClient() as client:
        # All services share the same client connection
        workspace_service = WorkspaceService(client)
        file_service = FileService(client)
        execution_service = ExecutionService(client)
        
        # Create workspace
        workspace_result = await workspace_service.create_workspace(ttl_hours=1)
        if not workspace_result.success:
            print(f"Failed to create workspace: {workspace_result.error}")
            return
            
        workspace_id = workspace_result.workspace_info.workspace_id
        print(f"Created workspace with shared client: {workspace_id}")
        
        # Upload multiple files efficiently
        files = [
            ("config.json", '{"debug": true, "max_items": 100}'),
            ("readme.txt", "This is a test workspace")
        ]
        
        for filename, content in files:
            result = await file_service.upload_file(workspace_id, filename, content)
            if result.success:
                print(f"Uploaded: {filename}")
        
        # Execute code that uses the files
        code = """
import json
import os

# Read config
with open('config.json', 'r') as f:
    config = json.load(f)

print(f"Debug mode: {config['debug']}")
print(f"Max items: {config['max_items']}")

# List all files
files = os.listdir('.')
print(f"Workspace contains {len(files)} files: {files}")

result = {"config": config, "file_count": len(files)}
"""
        
        exec_result = await execution_service.execute_code(workspace_id, code)
        if exec_result.success:
            execution = exec_result.execution_result
            print("Code executed with shared client")
            print(f"Output: {execution.stdout.strip()}")
        else:
            print(f"Code execution failed: {exec_result.error}")
        
        # Clean up
        await workspace_service.delete_workspace(workspace_id)


def example_llm_tool_usage():
    """
    Example: LLM Tool Usage
    
    The @function_tool decorated functions are meant to be used by LLM frameworks,
    not called directly in Python code. Here's how they would be used:
    
    # In LLM context:
    result = await create_workspace(ttl_hours=4)
    if result.success:
        workspace_id = result.workspace_info.workspace_id
        
        # Upload file
        upload_result = await upload_file(workspace_id, "data.csv", csv_content)
        
        # Execute code
        exec_result = await execute_code(workspace_id, python_code)
        
        # Download results
        download_result = await download_file(workspace_id, "outputs/plot.png")
        
        # Clean up
        await delete_workspace(workspace_id)
    
    The tools provide the same functionality as the services but with @function_tool
    decorators that make them available to LLM agents.
    """
    print("\n=== LLM Tool Usage ===")
    print("LLM tools are decorated with @function_tool and used by LLM frameworks.")
    print("They provide the same functionality as services but in LLM-compatible format.")
    print("See the docstring above for usage examples.")


async def main():
    """Run all examples"""
    print("🔍 Checking CodeSandbox server status...")
    
    health_service = HealthService()
    health_result = await health_service.check_system_health()
    
    if not health_result.success or not health_result.system_healthy:
        print("❌ CodeSandbox server is not running at http://localhost:8080")
        if health_result.error:
            print(f"   Error: {health_result.error}")
        print()
        
        # Get startup instructions from service
        instructions = health_service.get_startup_instructions()
        print(f"📋 {instructions['title']}")
        for step in instructions["steps"]:
            print(step)
        print()
        print(f"⚠️  {instructions['note']}")
        print()
    else:
        print("✅ CodeSandbox server is running!")
        if health_result.health_check:
            print(f"   Status: {health_result.health_check.status}")
            print(f"   Jupyter: {health_result.health_check.jupyter_server_status}")
            print(f"   Active Workspaces: {health_result.health_check.active_workspaces}")
        print()
    
    await example_direct_service_usage()
    await example_shared_client_usage() 
    example_llm_tool_usage()  # Not async anymore


if __name__ == "__main__":
    asyncio.run(main()) 