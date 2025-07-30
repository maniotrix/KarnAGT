#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test: File URL Upload and Local File Upload
Tests the new download_and_upload_file_to_workspace function
"""

import asyncio
import sys
import os
from typing import Optional, List, Tuple, Union, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from app.aicore.code_executor.services import WorkspaceService, FileService
from app.aicore.code_executor.clients import SandboxClient
from app.aicore.code_executor.clients.exceptions import NetworkError

class TestLogger:
    """Simple test logger"""
    
    def __init__(self) -> None:
        self.logs: List[str] = []
    
    def log(self, level: str, message: str, **kwargs: Any) -> None:
        entry = f"[{level.upper()}] {message}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self.log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self.log("warning", message, **kwargs)


async def test_server_connectivity() -> Tuple[bool, Any]:
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


async def test_workspace_creation() -> Tuple[bool, Union[str, Any]]:
    """Test workspace creation"""
    logger = TestLogger()
    logger.info("Testing workspace creation...")
    
    try:
        workspace_service = WorkspaceService()
        result = await workspace_service.create_workspace()
        
        if result.success and result.workspace_info:
            workspace_id = result.workspace_info.workspace_id
            logger.info("Workspace created successfully", workspace_id=workspace_id)
            return True, workspace_id
        else:
            logger.error("Workspace creation failed", error=result.error)
            return False, result.error or "Unknown error"
            
    except Exception as e:
        logger.error("Exception during workspace creation", error=str(e))
        return False, str(e)


async def test_download_and_upload(workspace_id: str, source: str, filename: Optional[str] = None, max_size_mb: int = 20):
    """Test download_and_upload_file_to_workspace function"""
    logger = TestLogger()
    source_type = "URL" if source.startswith(('http://', 'https://')) else "Local file"
    logger.info(f"Testing {source_type} download and upload", source=source, filename=filename)
    
    try:
        file_service = FileService()
        result = await file_service.download_and_upload_file_to_workspace(
            workspace_id=workspace_id,
            source=source,
            file_name=filename,
            max_size_mb=max_size_mb
        )
        
        if result.success and result.file_info:
            file_info = result.file_info
            logger.info(f"{source_type} upload succeeded", 
                       file_name=getattr(file_info, 'filename', 'unknown'), 
                       size=getattr(file_info, 'size', 0),
                       download_url=getattr(file_info, 'download_url', None))
            return True, result.file_info
        else:
            logger.error(f"{source_type} upload failed", error=result.error)
            return False, result.error
            
    except Exception as e:
        logger.error(f"Exception during {source_type} upload", error=str(e))
        return False, f"Exception: {e}"


async def run_file_upload_test() -> None:
    """Run comprehensive file upload test"""
    logger = TestLogger()
    
    print("=" * 80)
    print("FILE URL UPLOAD AND LOCAL FILE UPLOAD TEST")
    print("=" * 80)
    
    # Test URLs and local file
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    test_local_file = os.path.join(test_docs_dir, "PRY NDLS 20 June.pdf")
    
    test_cases = [
        {
            "name": "Small JSON URL (5MB)",
            "source": "https://microsoftedge.github.io/Demos/json-dummy-data/5MB.json",
            "filename": "test_data.json",
            "max_size_mb": 10
        },
        {
            "name": "GitHub text file URL",
            "source": "https://raw.githubusercontent.com/orangetw/Tiny-URL-Fuzzer/master/samples.txt",
            "filename": "samples.txt",
            "max_size_mb": 5
        },
        {
            "name": "Local PDF file",
            "source": test_local_file,
            "filename": "test_ticket.pdf",
            "max_size_mb": 20
        }
    ]
    
    # Test 1: Server connectivity
    print("\n1. Testing server connectivity...")
    server_running, server_info = await test_server_connectivity()
    
    if not server_running:
        print(f"❌ CodeSandbox server is not running: {server_info}")
        print("   Start the CodeSandbox server and re-run this test.")
        return
    
    print(f"✅ CodeSandbox server is running")
    
    # Test 2: Workspace creation
    print("\n2. Creating test workspace...")
    workspace_created, workspace_id = await test_workspace_creation()
    
    if not workspace_created:
        print(f"❌ Failed to create workspace: {workspace_id}")
        return
    
    print(f"✅ Workspace created: {workspace_id}")
    
    # Ensure workspace_id is a string
    if not isinstance(workspace_id, str):
        print(f"❌ Invalid workspace_id type: {type(workspace_id)}")
        return
    
    # Test 3: Run upload tests
    results: List[Tuple[str, bool, Any]] = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i+2}. Testing {test_case['name']}...")
        
        # Check if local file exists before testing
        source = str(test_case['source'])
        filename = str(test_case['filename'])
        max_size_mb = int(test_case['max_size_mb'])
        
        if not source.startswith(('http://', 'https://')):
            if not os.path.exists(source):
                print(f"   ⚠️  Local file not found: {source}")
                print(f"   📝 Skipping local file test - file doesn't exist")
                results.append((str(test_case['name']), False, "File not found"))
                continue
        
        success, result = await test_download_and_upload(
            workspace_id=workspace_id,
            source=source,
            filename=filename,
            max_size_mb=max_size_mb
        )
        
        results.append((str(test_case['name']), success, result))
        
        if success and hasattr(result, 'filename'):
            filename = getattr(result, 'filename', 'unknown')
            size = getattr(result, 'size', 0)
            print(f"   ✅ SUCCESS - File uploaded: {filename} ({size} bytes)")
            download_url = getattr(result, 'download_url', None)
            if download_url:
                print(f"   🔗 Download URL: {download_url}")
        else:
            print(f"   ❌ FAILED - {result}")
    
    # Test 4: Error handling tests
    print(f"\n{len(test_cases)+3}. Testing error handling...")
    
    # Test invalid URL
    print("   Testing invalid URL...")
    invalid_url_success, invalid_url_result = await test_download_and_upload(
        workspace_id=workspace_id,
        source="https://this-domain-does-not-exist-12345.com/file.txt",
        filename="invalid.txt",
        max_size_mb=5
    )
    print(f"   Invalid URL: {'❌ UNEXPECTEDLY SUCCEEDED' if invalid_url_success else '✅ CORRECTLY FAILED'}")
    if not invalid_url_success:
        print(f"   Error: {invalid_url_result}")
    
    # Test file too large (if we have a working URL)
    print("   Testing file size limit...")
    size_limit_success, size_limit_result = await test_download_and_upload(
        workspace_id=workspace_id,
        source="https://microsoftedge.github.io/Demos/json-dummy-data/5MB.json",
        filename="too_large.json",
        max_size_mb=1  # Very small limit
    )
    print(f"   Size limit: {'❌ UNEXPECTEDLY SUCCEEDED' if size_limit_success else '✅ CORRECTLY FAILED'}")
    if not size_limit_success:
        print(f"   Error: {size_limit_result}")
    
    # Test empty source
    print("   Testing empty source...")
    empty_source_success, empty_source_result = await test_download_and_upload(
        workspace_id=workspace_id,
        source="",
        filename="empty.txt",
        max_size_mb=5
    )
    print(f"   Empty source: {'❌ UNEXPECTEDLY SUCCEEDED' if empty_source_success else '✅ CORRECTLY FAILED'}")
    if not empty_source_success:
        print(f"   Error: {empty_source_result}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    successful_uploads = sum(1 for _, success, _ in results if success)
    total_uploads = len(results)
    
    print(f"Server running: ✅")
    print(f"Workspace created: ✅")
    print(f"Successful uploads: {successful_uploads}/{total_uploads}")
    
    print("\nDETAILED RESULTS:")
    for name, success, result in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")
        if not success:
            print(f"    Error: {result}")
    
    print("\nERROR HANDLING:")
    print(f"  Invalid URL rejected: {'✅' if not invalid_url_success else '❌'}")
    print(f"  Size limit enforced: {'✅' if not size_limit_success else '❌'}")
    print(f"  Empty source rejected: {'✅' if not empty_source_success else '❌'}")
    
    # Cleanup
    print(f"\n{len(test_cases)+4}. Cleaning up workspace {workspace_id}...")
    try:
        workspace_service = WorkspaceService()
        delete_result = await workspace_service.delete_workspace(workspace_id)
        if delete_result.success:
            print("✅ Workspace cleaned up successfully")
        else:
            print(f"⚠️ Workspace cleanup failed: {delete_result.error}")
    except Exception as e:
        print(f"⚠️ Workspace cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(run_file_upload_test())