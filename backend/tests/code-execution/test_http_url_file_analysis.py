#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test: CSV File Analysis with Workspace
Tests uploading CSV file and executing analysis code in workspace
"""

import asyncio
import sys
import os
from typing import Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from app.aicore.code_executor.services import WorkspaceService, FileService, ExecutionService
from app.aicore.code_executor.models import ExecutionOperationResult
from app.aicore.code_executor.clients import SandboxClient
from app.aicore.code_executor.clients.exceptions import NetworkError

class TestLogger:
    """Simple test logger"""
    
    def __init__(self) -> None:
        self.logs = []
    
    def info(self, message: str, **kwargs: Any) -> None:
        entry = f"[INFO] {message}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)
    
    def error(self, message: str, **kwargs: Any) -> None:
        entry = f"[ERROR] {message}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)

# HTTP URL
http_file_url = 'https://raw.githubusercontent.com/orangetw/Tiny-URL-Fuzzer/master/samples.txt'

# Analysis code to execute in workspace
ANALYSIS_CODE = '''
import os
from pathlib import Path
import time

print("🔍 Starting File Analysis...")

# File to analyze
filename = "samples.txt"

try:
    # Check if file exists
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        raise FileNotFoundError(f"File {filename} not found in workspace")
    
    print(f"✅ File found: {filename}")
    
    # Get file metadata
    file_path = Path(filename)
    file_stats = file_path.stat()
    
    print("\\n" + "="*40)
    print("📋 FILE METADATA")
    print("="*40)
    print(f"📄 Filename: {file_path.name}")
    print(f"📏 Size: {file_stats.st_size:,} bytes ({file_stats.st_size/1024:.2f} KB)")
    print(f"🕐 Modified: {time.ctime(file_stats.st_mtime)}")
    print(f"🔧 Permissions: {oct(file_stats.st_mode)[-3:]}")
    
    # Read and analyze file content
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Basic content analysis
    lines = content.splitlines()
    total_lines = len(lines)
    total_chars = len(content)
    words = content.split()
    total_words = len(words)
    
    print("\\n" + "="*40)
    print("📊 CONTENT ANALYSIS")
    print("="*40)
    print(f"📜 Total Lines: {total_lines:,}")
    print(f"🔤 Total Characters: {total_chars:,}")
    print(f"📝 Total Words: {total_words:,}")
    print(f"📈 Avg Line Length: {total_chars/max(total_lines,1):.1f} chars")
    print(f"📉 Avg Word Length: {total_chars/max(total_words,1):.1f} chars")
    
    # Show first 10 lines
    print("\\n" + "="*40)
    print("📖 FIRST 10 LINES")
    print("="*40)
    for i, line in enumerate(lines[:10], 1):
        print(f"{i:2d}: {line[:80]}")  # Limit line display to 80 chars
    
    if total_lines > 10:
        print(f"... ({total_lines - 10} more lines)")
    
    # Create result summary
    result = {
        'filename': filename,
        'size_bytes': file_stats.st_size,
        'total_lines': total_lines,
        'total_words': total_words,
        'total_chars': total_chars,
        'first_lines': lines[:10] if lines else []
    }
    
    print(f"\\n🎯 Analysis Complete! File has {total_lines} lines, {total_words} words")

except Exception as e:
    print(f"❌ Error analyzing file: {e}")
    result = {'error': str(e)}

print(f"\\n📊 Final Result: {result}")
result
'''

async def test_server_connectivity():
    """Test if CodeSandbox server is running"""
    logger = TestLogger()
    logger.info("Testing CodeSandbox server connectivity...")
    
    try:
        async with SandboxClient() as client:
            health = await client.health_check()
            logger.info("Server health check successful", status=health.status)
            return True, health
    except NetworkError as e:
        logger.error("Network error - server likely not running", error=str(e))
        return False, str(e)
    except Exception as e:
        logger.error("Unexpected error during health check", error=str(e))
        return False, str(e)

async def test_http_url_file_analysis():
    """Run comprehensive HTTP URL file analysis test"""
    logger = TestLogger()
    
    print("=" * 80)
    print("HTTP URL FILE ANALYSIS TEST")
    print("=" * 80)
    
    # Test 1: Server connectivity
    print("\\n1. Testing server connectivity...")
    server_running, server_info = await test_server_connectivity()
    
    if not server_running:
        print(f"❌ CodeSandbox server is not running: {server_info}")
        return
    
    print("✅ CodeSandbox server is running")
    
    # Test 2: Create workspace
    print("\\n2. Creating workspace...")
    try:
        workspace_service = WorkspaceService()
        workspace_result = await workspace_service.create_workspace()
        
        if not workspace_result.success or not workspace_result.workspace_info:
            print(f"❌ Failed to create workspace: {workspace_result.error}")
            return
        
        workspace_id = workspace_result.workspace_info.workspace_id
        print(f"✅ Workspace created: {workspace_id}")
        
    except Exception as e:
        print(f"❌ Workspace creation error: {e}")
        return
    
    # Test 3: Upload HTTP URL file
    print("\\n3. Uploading HTTP URL file to workspace...")
    try:
        file_service = FileService()
        upload_result = await file_service.download_and_upload_file_to_workspace(
            workspace_id=workspace_id,
            source=http_file_url,
            file_name="samples.txt",
            max_size_mb=20
        )
        
        if not upload_result.success:
            print(f"❌ Failed to upload HTTP URL file: {upload_result.error}")
            return
        
        file_info = upload_result.file_info
        if file_info:
            print(f"✅ HTTP URL file uploaded successfully: {file_info.filename} ({file_info.size} bytes)")
            if hasattr(file_info, 'download_url') and file_info.download_url:
                print(f"🔗 Download URL: {file_info.download_url}")
        
    except Exception as e:
        print(f"❌ File upload error: {e}")
        return
    
    # Test 4: Execute analysis code
    print("\\n4. Executing HTTP URL file analysis code...")
    try:
        execution_service = ExecutionService()
        execution_result: ExecutionOperationResult = await execution_service.execute_code(workspace_id, ANALYSIS_CODE)
        
        if not execution_result.success:
            print(f"❌ Code execution failed: {execution_result.error}")
            return
        
        print("✅ Analysis code executed successfully!")
        
        # Show execution output
        if execution_result.execution_result and execution_result.execution_result.stdout:
            print("\\n" + "="*50)
            print("📊 ANALYSIS OUTPUT")
            print("="*50)
            print(execution_result.execution_result.stdout)
        
        # Show any generated files
        if execution_result.execution_result and execution_result.execution_result.generated_files:
            print(f"\\n📁 Generated {len(execution_result.execution_result.generated_files)} file(s):")
            for file_info in execution_result.execution_result.generated_files:
                print(f"   📄 {file_info.filename} ({file_info.size} bytes)")
                if hasattr(file_info, 'download_url') and file_info.download_url:
                    print(f"      🔗 {file_info.download_url}")
        
        # Show final result
        if execution_result.execution_result and execution_result.execution_result.result_data:
            print(f"\\n🎯 Final Analysis Result:")
            print(f"   {execution_result.execution_result.result_data}")
        
    except Exception as e:
        print(f"❌ Code execution error: {e}")
        return
    
    # Test 5: Cleanup
    print(f"\\n5. Cleaning up workspace {workspace_id}...")
    try:
        delete_result = await workspace_service.delete_workspace(workspace_id)
        if delete_result.success:
            print("✅ Workspace cleaned up successfully")
        else:
            print(f"⚠️ Workspace cleanup failed: {delete_result.error}")
    except Exception as e:
        print(f"⚠️ Workspace cleanup error: {e}")
    
    print("\\n🎉 CSV Analysis Test Completed!")

if __name__ == "__main__":
    asyncio.run(test_http_url_file_analysis())


