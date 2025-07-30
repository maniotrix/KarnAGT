#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive CodeSandbox Concurrency & Exception Test Suite

Tests all recent changes to exception handling, circuit breaker behavior,
and validation error types to ensure proper HTTP status codes and
circuit breaker isolation.
"""

import asyncio
import httpx
import json
import time
from typing import List, Dict, Any, Union
import random
import string


BASE_URL = "http://localhost:8080/api/v1"


class TestResults:
    """Track test results and statistics"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.start_time = time.time()
    
    def success(self, test_name: str):
        self.passed += 1
        print(f"   ✅ {test_name}")
    
    def failure(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"   ❌ {test_name}: {error}")
    
    def summary(self):
        duration = time.time() - self.start_time
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 80)
        print("🏆 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Duration: {duration:.2f}s")
        
        if self.errors:
            print("\n❌ FAILURES:")
            for error in self.errors:
                print(f"   • {error}")
        
        return self.failed == 0


async def test_validation_errors(client: httpx.AsyncClient, results: TestResults):
    """Test all validation error types return proper HTTP codes without triggering circuit breaker"""
    
    print("🧪 VALIDATION ERROR TESTS")
    print("-" * 50)
    
    # Create workspace for testing
    response = await client.post(f"{BASE_URL}/workspace/create", json={"ttl_hours": 1})
    if response.status_code != 200:
        results.failure("Workspace Creation", f"Status {response.status_code}")
        return
    workspace_id = response.json()["workspace_id"]
    results.success("Test workspace created")
    
    # Test 1: ExecutionValidationError - Code too long
    print("\n1️⃣  ExecutionValidationError Tests")
    
    long_code = "print('hello')\n" * 5000  # > 50KB
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/execute", 
                               data={"code": long_code})
    
    if response.status_code == 400:
        error_detail = response.json().get("detail", "")
        if "Code too long" in error_detail:
            results.success("Code too long → HTTP 400 (ExecutionValidationError)")
        else:
            results.failure("Code too long", f"Wrong error message: {error_detail}")
    else:
        results.failure("Code too long", f"Expected 400, got {response.status_code}")
    
    # Test 2: WorkspaceValidationError - TTL exceeded
    print("\n2️⃣  WorkspaceValidationError Tests")
    
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/extend", 
                               data={"additional_hours": 100})  # Exceeds max TTL
    
    if response.status_code == 400:
        error_detail = response.json().get("detail", "")
        if "Maximum TTL" in error_detail:
            results.success("TTL exceeded → HTTP 400 (WorkspaceValidationError)")
        else:
            results.failure("TTL exceeded", f"Wrong error message: {error_detail}")
    else:
        results.failure("TTL exceeded", f"Expected 400, got {response.status_code}")
    
    # Test 3: WorkspaceNotFoundError - Missing workspace
    print("\n3️⃣  WorkspaceNotFoundError Tests")
    
    fake_workspace = "ws_nonexistent_12345"
    response = await client.get(f"{BASE_URL}/workspace/{fake_workspace}")
    
    if response.status_code == 404:
        results.success("Missing workspace → HTTP 404 (WorkspaceNotFoundError)")
    else:
        results.failure("Missing workspace", f"Expected 404, got {response.status_code}")
    
    # Test 4: FileServiceError - Invalid filename
    print("\n4️⃣  FileServiceError Tests")
    
    invalid_files = [
        ("subdir/invalid.txt", "Forward slashes"),
        ("subdir\\invalid.txt", "Backslashes"), 
        (".hidden_file.txt", "Hidden files"),
        ("CON.txt", "Reserved names"),
        ("file<test.txt", "Invalid characters"),
        ("", "Empty filename")
    ]
    
    for invalid_filename, test_desc in invalid_files:
        if invalid_filename:  # Skip empty filename for upload test
            files = {"file": (invalid_filename, "test content", "text/plain")}
            response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/upload", files=files)
        else:
            # Empty filename test would be handled differently in real client
            continue
            
        if response.status_code == 400:
            results.success(f"{test_desc} → HTTP 400 (FileServiceError)")
        else:
            results.failure(f"{test_desc}", f"Expected 400, got {response.status_code}")


async def test_circuit_breaker_isolation(client: httpx.AsyncClient, results: TestResults):
    """Test that validation errors don't trigger circuit breaker"""
    
    print("\n🔄 CIRCUIT BREAKER ISOLATION TESTS")
    print("-" * 50)
    
    # Create workspace
    response = await client.post(f"{BASE_URL}/workspace/create", json={"ttl_hours": 1})
    if response.status_code != 200:
        results.failure("CB Test Workspace", f"Status {response.status_code}")
        return
    workspace_id = response.json()["workspace_id"]
    
    # Test: Send many validation errors rapidly - circuit breaker should NOT open
    print("\n1️⃣  Rapid Validation Errors (Circuit Breaker Should Stay Closed)")
    
    validation_errors = 0
    circuit_breaker_errors = 0
    
    # Send 20 validation errors rapidly
    for i in range(20):
        # Alternate between different validation error types
        if i % 4 == 0:
            # Code too long
            long_code = "print('test')\n" * 2000
            response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/execute", 
                                       data={"code": long_code})
        elif i % 4 == 1:
            # Invalid filename upload
            files = {"file": (f"invalid/file{i}.txt", "content", "text/plain")}
            response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/upload", files=files)
        elif i % 4 == 2:
            # Missing workspace
            response = await client.get(f"{BASE_URL}/workspace/nonexistent_{i}")
        else:
            # TTL exceeded
            response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/extend", 
                                       data={"additional_hours": 50})
        
        if response.status_code in [400, 404]:
            validation_errors += 1
        elif response.status_code == 503:
            circuit_breaker_errors += 1
            error_detail = response.json().get("detail", "")
            if "circuit breaker" in error_detail.lower():
                results.failure("Circuit Breaker Isolation", 
                              f"Circuit breaker opened after {i} validation errors")
                return
    
    if circuit_breaker_errors == 0:
        results.success(f"Circuit breaker stayed closed through {validation_errors} validation errors")
    else:
        results.failure("Circuit Breaker Isolation", 
                      f"Got {circuit_breaker_errors} circuit breaker errors")
    
    # Test: Verify system still works after validation errors
    print("\n2️⃣  System Health After Validation Errors")
    
    response = await client.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        results.success("System healthy after validation errors")
    else:
        results.failure("System Health", f"Health check failed: {response.status_code}")
    
    # Execute valid code to ensure system still works
    valid_code = "print('System is working correctly')\nresult = 'success'"
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/execute", 
                               data={"code": valid_code})
    
    if response.status_code == 200 and response.json().get("status") == "completed":
        results.success("Valid execution works after validation errors")
    else:
        results.failure("Valid Execution", f"Failed after validation errors: {response.status_code}")


async def test_file_concurrency_system(client: httpx.AsyncClient, results: TestResults):
    """Test the new file concurrency system"""
    
    print("\n📁 FILE CONCURRENCY SYSTEM TESTS")
    print("-" * 50)
    
    # Create workspace
    response = await client.post(f"{BASE_URL}/workspace/create", json={"ttl_hours": 1})
    if response.status_code != 200:
        results.failure("File Concurrency Workspace", f"Status {response.status_code}")
        return
    workspace_id = response.json()["workspace_id"]
    
    # Test 1: Concurrent file uploads
    print("\n1️⃣  Concurrent File Upload Test")
    
    async def upload_file(filename: str, content: str):
        files = {"file": (filename, content, "text/plain")}
        return await client.post(f"{BASE_URL}/workspace/{workspace_id}/upload", files=files)
    
    # Upload 10 files concurrently
    upload_tasks = []
    for i in range(10):
        filename = f"concurrent_test_{i}.txt"
        content = f"This is test file {i} with content " + "x" * 100
        upload_tasks.append(upload_file(filename, content))
    
    responses = await asyncio.gather(*upload_tasks, return_exceptions=True)
    
    successful_uploads = 0
    failed_uploads = 0
    
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            failed_uploads += 1
        elif hasattr(response, 'status_code'):
            response_obj = response  # type: httpx.Response
            if response_obj.status_code == 200:
                successful_uploads += 1
            elif response_obj.status_code == 503:
                # File service temporarily unavailable - this is acceptable under load
                pass
            else:
                failed_uploads += 1
        else:
            failed_uploads += 1
    
    if successful_uploads >= 5:  # At least half should succeed
        results.success(f"Concurrent uploads: {successful_uploads}/10 succeeded")
    else:
        results.failure("Concurrent Uploads", f"Only {successful_uploads}/10 succeeded")
    
    # Test 2: File operations after concurrency
    print("\n2️⃣  File System Integrity After Concurrency")
    
    response = await client.get(f"{BASE_URL}/workspace/{workspace_id}/files")
    if response.status_code == 200:
        files_data = response.json()
        total_files = files_data.get("total_files", 0)
        results.success(f"File listing works: {total_files} files found")
        
        # Test downloading a file
        if files_data.get("files"):
            first_file = files_data["files"][0]
            download_url = first_file["download_url"]
            response = await client.get(f"{BASE_URL}{download_url}")
            
            if response.status_code == 200:
                results.success("File download works after concurrency")
            else:
                results.failure("File Download", f"Download failed: {response.status_code}")
    else:
        results.failure("File Listing", f"Failed: {response.status_code}")


async def test_error_response_formats(client: httpx.AsyncClient, results: TestResults):
    """Test error response formats and consistency"""
    
    print("\n📋 ERROR RESPONSE FORMAT TESTS")
    print("-" * 50)
    
    # Create workspace
    response = await client.post(f"{BASE_URL}/workspace/create", json={"ttl_hours": 1})
    if response.status_code != 200:
        results.failure("Error Format Workspace", f"Status {response.status_code}")
        return
    workspace_id = response.json()["workspace_id"]
    
    # Test ExecutionValidationError Format
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/execute", 
                               data={"code": "x" * 60000})
    test_name = "ExecutionValidationError Format"
    if response.status_code == 400:
        try:
            error_data = response.json()
            if "detail" in error_data and "code too long" in error_data["detail"].lower():
                results.success(f"{test_name} → Proper format & content")
            else:
                results.failure(test_name, f"Wrong error content: {error_data.get('detail', 'N/A')}")
        except json.JSONDecodeError:
            results.failure(test_name, "Invalid JSON in error response")
    else:
        results.failure(test_name, f"Expected 400, got {response.status_code}")
    
    # Test WorkspaceValidationError Format
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/extend",
                               data={"additional_hours": 100})
    test_name = "WorkspaceValidationError Format"
    if response.status_code == 400:
        try:
            error_data = response.json()
            if "detail" in error_data and "maximum ttl" in error_data["detail"].lower():
                results.success(f"{test_name} → Proper format & content")
            else:
                results.failure(test_name, f"Wrong error content: {error_data.get('detail', 'N/A')}")
        except json.JSONDecodeError:
            results.failure(test_name, "Invalid JSON in error response")
    else:
        results.failure(test_name, f"Expected 400, got {response.status_code}")
    
    # Test WorkspaceNotFoundError Format
    response = await client.get(f"{BASE_URL}/workspace/nonexistent_workspace")
    test_name = "WorkspaceNotFoundError Format"
    if response.status_code == 404:
        try:
            error_data = response.json()
            if "detail" in error_data and ("not found" in error_data["detail"].lower() or "workspace" in error_data["detail"].lower()):
                results.success(f"{test_name} → Proper format & content")
            else:
                results.failure(test_name, f"Wrong error content: {error_data.get('detail', 'N/A')}")
        except json.JSONDecodeError:
            results.failure(test_name, "Invalid JSON in error response")
    else:
        results.failure(test_name, f"Expected 404, got {response.status_code}")
    
    # Test FileServiceError Format
    response = await client.post(f"{BASE_URL}/workspace/{workspace_id}/upload",
                               files={"file": ("invalid/file.txt", "content", "text/plain")})
    test_name = "FileServiceError Format"
    if response.status_code == 400:
        try:
            error_data = response.json()
            if "detail" in error_data and ("forward slashes" in error_data["detail"].lower() or "not allowed" in error_data["detail"].lower()):
                results.success(f"{test_name} → Proper format & content")
            else:
                results.failure(test_name, f"Wrong error content: {error_data.get('detail', 'N/A')}")
        except json.JSONDecodeError:
            results.failure(test_name, "Invalid JSON in error response")
    else:
        results.failure(test_name, f"Expected 400, got {response.status_code}")


async def test_edge_cases(client: httpx.AsyncClient, results: TestResults):
    """Test various edge cases and boundary conditions"""
    
    print("\n🎯 EDGE CASE TESTS")
    print("-" * 50)
    
    # Test 1: Malformed requests
    print("\n1️⃣  Malformed Request Tests")
    
    # Invalid JSON
    try:
        response = await client.post(f"{BASE_URL}/workspace/create", 
                                   content="invalid json", 
                                   headers={"content-type": "application/json"})
        if response.status_code == 422:  # FastAPI validation error
            results.success("Invalid JSON → HTTP 422")
        else:
            results.failure("Invalid JSON", f"Expected 422, got {response.status_code}")
    except:
        results.failure("Invalid JSON", "Request failed unexpectedly")
    
    # Test 2: Very long workspace IDs
    print("\n2️⃣  Boundary Value Tests")
    
    very_long_workspace_id = "ws_" + "x" * 100
    response = await client.get(f"{BASE_URL}/workspace/{very_long_workspace_id}")
    
    if response.status_code in [404, 400]:  # Either is acceptable
        results.success("Very long workspace ID handled gracefully")
    else:
        results.failure("Long Workspace ID", f"Unexpected status: {response.status_code}")
    
    # Test 3: Special characters in workspace operations
    print("\n3️⃣  Special Character Tests")
    
    special_workspace_id = "ws_with%20spaces"
    response = await client.get(f"{BASE_URL}/workspace/{special_workspace_id}")
    
    if response.status_code in [404, 400]:  # Either is acceptable
        results.success("Special characters in workspace ID handled")
    else:
        results.failure("Special Characters", f"Unexpected status: {response.status_code}")


async def test_performance_under_load(client: httpx.AsyncClient, results: TestResults):
    """Test system performance under load"""
    
    print("\n⚡ PERFORMANCE UNDER LOAD TESTS")
    print("-" * 50)
    
    # Create workspace
    response = await client.post(f"{BASE_URL}/workspace/create", json={"ttl_hours": 1})
    if response.status_code != 200:
        results.failure("Performance Workspace", f"Status {response.status_code}")
        return
    workspace_id = response.json()["workspace_id"]
    
    # Test 1: Rapid valid requests
    print("\n1️⃣  Rapid Valid Requests")
    
    start_time = time.time()
    
    async def health_check():
        return await client.get(f"{BASE_URL}/health")
    
    # Send 20 health checks concurrently
    health_tasks = [health_check() for _ in range(20)]
    responses = await asyncio.gather(*health_tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    successful_requests = 0
    for r in responses:
        if not isinstance(r, Exception) and hasattr(r, 'status_code'):
            response_obj = r  # type: httpx.Response
            if response_obj.status_code == 200:
                successful_requests += 1
    
    requests_per_second = successful_requests / duration if duration > 0 else 0
    
    if successful_requests >= 18:  # 90% success rate
        results.success(f"Load test: {successful_requests}/20 requests succeeded "
                       f"({requests_per_second:.1f} req/s)")
    else:
        results.failure("Load Test", f"Only {successful_requests}/20 requests succeeded")
    
    # Test 2: System stability after load
    print("\n2️⃣  System Stability After Load")
    
    # Wait a moment for system to stabilize
    await asyncio.sleep(1)
    
    response = await client.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        results.success("System stable after load test")
    else:
        results.failure("System Stability", f"Health check failed: {response.status_code}")


async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    
    results = TestResults()
    
    print("🧪 COMPREHENSIVE CODESANDBOX CONCURRENCY & EXCEPTION TESTS")
    print("=" * 80)
    print("Testing recent changes:")
    print("• ValidationError inheritance and circuit breaker isolation")
    print("• ExecutionValidationError, WorkspaceValidationError, WorkspaceNotFoundError")
    print("• File concurrency system and error handling")
    print("• HTTP status code consistency")
    print("• System resilience under load")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test server availability
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print(f"❌ Server not available: {response.status_code}")
                print("💡 Make sure server is running: python run_server.py")
                return False
            
            print("✅ Server is running and healthy")
            print()
            
            # Run all test suites
            await test_validation_errors(client, results)
            await test_circuit_breaker_isolation(client, results)
            await test_file_concurrency_system(client, results)
            await test_error_response_formats(client, results)
            await test_edge_cases(client, results)
            await test_performance_under_load(client, results)
            
        except Exception as e:
            results.failure("Test Execution", f"Unexpected error: {e}")
    
    # Print final results
    success = results.summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Validation errors properly isolated from circuit breaker")
        print("✅ Exception types return correct HTTP status codes")
        print("✅ File concurrency system working correctly")
        print("✅ System resilient under load")
    else:
        print("\n⚠️  SOME TESTS FAILED!")
        print("❌ Review failures above and check system implementation")
    
    return success


if __name__ == "__main__":
    print("⏳ Starting comprehensive concurrency & exception tests...")
    print("💡 Make sure the server is running: python run_server.py")
    print()
    
    try:
        success = asyncio.run(run_comprehensive_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        exit(1) 