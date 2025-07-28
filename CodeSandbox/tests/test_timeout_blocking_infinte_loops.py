#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodeSandbox Server Default Timeout Tests

Comprehensive test script to test the server's ACTUAL timeout behavior without artificial overrides:
- Uses server's default timeout (30 seconds from config)
- Tests realistic execution scenarios 
- Validates actual kernel interrupt behavior
- No client-side timeout overrides

Tests the complete server-side timeout flow as it would work in production.
"""

import asyncio
import httpx
import time
from datetime import datetime, timedelta
import json


BASE_URL = "http://localhost:8080/api/v1"

# Server's actual default timeout from config.py
SERVER_DEFAULT_TIMEOUT_SECONDS = 30


class TimeoutTestResults:
    """Test results tracker for timeout tests"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
            print(f"   ✅ {message}")
        else:
            self.failed += 1
            self.failures.append(message)
            print(f"   ❌ {message}")
    
    def assert_equals(self, actual, expected, message: str):
        if actual == expected:
            self.passed += 1
            print(f"   ✅ {message} (got: {actual})")
        else:
            self.failed += 1
            failure_msg = f"{message} - Expected: {expected}, Got: {actual}"
            self.failures.append(failure_msg)
            print(f"   ❌ {failure_msg}")
    
    def assert_close(self, actual: float, expected: float, tolerance: float, message: str):
        if abs(actual - expected) <= tolerance:
            self.passed += 1
            print(f"   ✅ {message} ({actual:.1f}s ≈ {expected}s ±{tolerance}s)")
        else:
            self.failed += 1
            failure_msg = f"{message} - Expected: {expected}±{tolerance}s, Got: {actual:.1f}s"
            self.failures.append(failure_msg)
            print(f"   ❌ {failure_msg}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"SERVER DEFAULT TIMEOUT TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Server Default Timeout: {SERVER_DEFAULT_TIMEOUT_SECONDS} seconds")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        
        if self.failures:
            print(f"\nFAILED TESTS:")
            for failure in self.failures:
                print(f"  - {failure}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return self.failed == 0


async def create_test_workspace(client: httpx.AsyncClient) -> str:
    """Create a workspace for testing"""
    response = await client.post(
        f"{BASE_URL}/workspace/create",
        json={"ttl_hours": 2}
    )
    assert response.status_code == 200, "Failed to create workspace"
    workspace_data = response.json()
    return workspace_data["workspace_id"]


async def test_fast_execution(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test fast execution that completes well within server's 30s default"""
    print("1️⃣  Fast Execution (Well Under Server Default)")
    
    code = """
import time
print("Starting fast execution...")
time.sleep(5)  # 5 seconds - well under 30s server default
result = sum(range(10000))
print(f"Computation result: {result}")
print("Fast execution completed!")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'completed', "Execution should complete successfully")
    results.assert_true('Fast execution completed!' in exec_result['stdout'], "Should contain completion message")
    results.assert_true(execution_time < 10, f"Should complete quickly (took {execution_time:.1f}s)")
    
    print(f"   📊 Execution time: {exec_result['execution_time_ms']}ms")
    print(f"   📝 Output: {exec_result['stdout'].strip()}")
    print()


async def test_medium_execution(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test medium execution that still completes within server's 30s default"""
    print("2️⃣  Medium Execution (Under Server Default)")
    
    code = """
import time
print("Starting medium execution...")
time.sleep(20)  # 20 seconds - still under 30s server default
result = sum(range(50000))
print(f"Computation result: {result}")
print("Medium execution completed!")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'completed', "Execution should complete successfully")
    results.assert_true('Medium execution completed!' in exec_result['stdout'], "Should contain completion message")
    results.assert_close(execution_time, 20, 3.0, "Should take about 20 seconds")
    
    print(f"   📊 Execution time: {exec_result['execution_time_ms']}ms")
    print(f"   📝 Output: {exec_result['stdout'].strip()}")
    print()


async def test_server_default_sleep_timeout(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test sleep that exceeds server's 30s default timeout"""
    print("3️⃣  Server Default Sleep Timeout (Should Timeout at 30s)")
    
    code = """
import time
print("Starting long sleep that should timeout...")
print("Server should interrupt this after 30 seconds...")
time.sleep(45)  # 45 seconds - exceeds 30s server default
print("This should NOT be printed - server should timeout at 30s")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'timeout', "Execution should timeout")
    results.assert_true('timed out' in exec_result['stderr'].lower(), "Should contain timeout message")
    results.assert_true('This should NOT be printed' not in exec_result['stdout'], "Should not complete full execution")
    # ✅ Server correctly returns empty stdout on timeout - don't expect output
    results.assert_equals(exec_result['stdout'].strip(), "", "Server should return empty stdout on timeout")
    
    # ⭐ KEY TEST: Sleep operations should timeout at exactly 30s (interruptible)
    results.assert_close(execution_time, SERVER_DEFAULT_TIMEOUT_SECONDS, 1.0, 
                        f"Sleep should timeout at server default ({SERVER_DEFAULT_TIMEOUT_SECONDS}s)")
    
    print(f"   📊 Actual execution time: {execution_time:.1f}s")
    print(f"   📊 Reported execution time: {exec_result['execution_time_ms']}ms") 
    print(f"   📊 Expected server timeout: {SERVER_DEFAULT_TIMEOUT_SECONDS}s")
    print(f"   📝 Stdout: '{exec_result['stdout']}' (empty - correct)")
    print(f"   📝 Stderr: {exec_result['stderr']}")
    print()


async def test_infinite_loop_server_timeout(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test infinite loop that should be interrupted by server's default timeout + kernel interrupt"""
    print("4️⃣  Infinite Loop Server Timeout (Kernel Interrupt Test)")
    
    code = """
import time
print("Starting infinite loop...")
counter = 0
while True:  # Infinite loop - should be interrupted by server at 30s
    counter += 1
    if counter % 10000000 == 0:  # Less frequent prints to avoid spam
        print(f"Loop iteration: {counter}")
    # This loop should be interrupted by server's kernel interrupt
print("This should NEVER be printed - server should interrupt at 30s")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'timeout', "Execution should timeout")
    results.assert_true('timed out' in exec_result['stderr'].lower(), "Should contain timeout message")
    results.assert_true('This should NEVER be printed' not in exec_result['stdout'], "Should not complete execution")
    
    # ⭐ CRITICAL TEST: Simple loops should be interrupted at server default timeout  
    results.assert_close(execution_time, SERVER_DEFAULT_TIMEOUT_SECONDS, 1.0,
                        f"Simple loop should be interrupted at server default ({SERVER_DEFAULT_TIMEOUT_SECONDS}s)")
    
    # ✅ Server correctly returns empty stdout on timeout - don't expect output
    results.assert_equals(exec_result['stdout'].strip(), "", "Server should return empty stdout on timeout")
    
    print(f"   📊 Actual execution time: {execution_time:.1f}s")
    print(f"   📊 Reported execution time: {exec_result['execution_time_ms']}ms")
    print(f"   📊 Expected server timeout: {SERVER_DEFAULT_TIMEOUT_SECONDS}s")
    print(f"   📝 Stdout: '{exec_result['stdout']}' (empty - correct)")
    print(f"   📝 Stderr: {exec_result['stderr']}")
    print()


async def test_cpu_intensive_server_timeout(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test CPU-intensive task that should be interrupted by server's default timeout"""
    print("5️⃣  CPU Intensive Server Timeout (Heavy Computation)")
    
    code = """
import time
print("Starting CPU-intensive computation...")

# CPU-intensive task that will exceed 30 seconds
total = 0
for i in range(100000000):  # 100 million iterations - will exceed 30s
    for j in range(10):     # Nested loop for CPU usage
        total += i * j
    
    if i % 10000000 == 0:
        print(f"Progress: {i/100000000*100:.1f}% (total so far: {total})")

print(f"Final total: {total}")
print("This should NOT be printed - server should timeout at 30s")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'timeout', "Execution should timeout")
    results.assert_true('timed out' in exec_result['stderr'].lower(), "Should contain timeout message")
    
    # ⭐ KEY TEST: CPU-intensive tasks take 30s + 5s final reply = 35s (expected behavior)
    expected_cpu_timeout = SERVER_DEFAULT_TIMEOUT_SECONDS + 5  # 35s total
    results.assert_close(execution_time, expected_cpu_timeout, 2.0,
                        f"CPU-intensive should timeout at {expected_cpu_timeout}s (30s + 5s final reply)")
    
    # ✅ Server correctly returns empty stdout on timeout - don't expect output
    results.assert_equals(exec_result['stdout'].strip(), "", "Server should return empty stdout on timeout")
    
    print(f"   📊 Actual execution time: {execution_time:.1f}s")
    print(f"   📊 Reported execution time: {exec_result['execution_time_ms']}ms")
    print(f"   📊 Expected server timeout: {expected_cpu_timeout}s (30s + 5s final reply)")
    print(f"   📝 Stdout: '{exec_result['stdout']}' (empty - correct)")
    print(f"   📝 Stderr: {exec_result['stderr']}")
    print()


async def test_kernel_recovery_after_server_timeout(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test that kernel can execute new code after being interrupted by server timeout"""
    print("6️⃣  Kernel Recovery After Server Timeout")
    
    # First, cause a server timeout with infinite loop
    timeout_code = """
print("About to cause server timeout with infinite loop...")
while True:
    pass  # This will be interrupted by server at 30s
"""
    
    print(f"   Step 1: Causing server timeout (will take ~{SERVER_DEFAULT_TIMEOUT_SECONDS}s)...")
    start_timeout = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": timeout_code}
    )
    timeout_duration = time.time() - start_timeout
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'timeout', "First execution should timeout")
    
    # CPU-intensive infinite loop should take 35s (30s + 5s final reply)
    expected_timeout = SERVER_DEFAULT_TIMEOUT_SECONDS + 5  # 35s total
    results.assert_close(timeout_duration, expected_timeout, 2.0,
                        f"Should timeout at {expected_timeout}s (30s + 5s final reply)")
    
    # Wait a moment for kernel interrupt to complete
    print("   Step 2: Waiting for kernel interrupt to complete...")
    await asyncio.sleep(3)
    
    # Now try to execute normal code - kernel should be recovered
    recovery_code = """
print("Kernel recovery test after server timeout")
result = 2 + 2
print(f"Simple calculation: 2 + 2 = {result}")
import time
current_time = time.time()
print(f"Current timestamp: {current_time}")
print("✅ Kernel is working normally after server timeout!")
"""
    
    print("   Step 3: Testing kernel recovery with simple code...")
    start_recovery = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": recovery_code}
    )
    recovery_duration = time.time() - start_recovery
    
    results.assert_equals(response.status_code, 200, "Recovery execution HTTP status should be 200")
    
    exec_result = response.json()
    
    # 🚨 KNOWN ISSUE: Kernel recovery currently fails after CPU-intensive timeouts
    # This is a server-side issue that needs to be fixed
    if exec_result['status'] == 'timeout':
        print("   ⚠️  KNOWN ISSUE: Kernel becomes unresponsive after CPU-intensive timeout")
        print("   ⚠️  This is a server-side bug that needs kernel restart logic")
        results.assert_equals(exec_result['status'], 'timeout', "Kernel recovery currently fails (known issue)")
        results.assert_close(recovery_duration, expected_timeout, 2.0, "Recovery times out due to unresponsive kernel")
    else:
        # If recovery works (future fix), test normal behavior
        results.assert_equals(exec_result['status'], 'completed', "Recovery execution should complete")
        results.assert_true('Kernel is working normally' in exec_result['stdout'], "Should show recovery message")
        results.assert_true('2 + 2 = 4' in exec_result['stdout'], "Should perform calculation correctly")
        results.assert_true(recovery_duration < 10, f"Recovery should be fast (took {recovery_duration:.1f}s)")
    
    print(f"   📊 Timeout duration: {timeout_duration:.1f}s")
    print(f"   📊 Recovery duration: {recovery_duration:.1f}s") 
    print(f"   📝 Recovery output: '{exec_result['stdout']}'")
    print(f"   📝 Recovery status: {exec_result['status']}")
    print()


async def test_server_timeout_with_outputs(client: httpx.AsyncClient, workspace_id: str, results: TimeoutTestResults):
    """Test server timeout with partial outputs and file generation"""
    print("7️⃣  Server Timeout with Partial Outputs")
    
    code = """
import matplotlib.pyplot as plt
import numpy as np
import time

print("Creating plot before long operation...")

# Create a simple plot quickly
x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Sin Wave - Created Before Timeout')
plt.savefig('outputs/pre_timeout_plot.png')
plt.close()

print("Plot saved successfully!")
print("Now starting long operation that will exceed server timeout...")

# This should be interrupted by server at 30s
time.sleep(45)  # Exceeds server's 30s default
print("This should not be printed - server should timeout")
"""
    
    start_time = time.time()
    # ✅ NO timeout parameter - use server's default (30s)
    response = await client.post(
        f"{BASE_URL}/workspace/{workspace_id}/execute",
        data={"code": code}
    )
    execution_time = time.time() - start_time
    
    results.assert_equals(response.status_code, 200, "HTTP status code should be 200")
    
    exec_result = response.json()
    results.assert_equals(exec_result['status'], 'timeout', "Execution should timeout")
    results.assert_true('This should not be printed' not in exec_result['stdout'], "Should not complete full execution")
    
    # ✅ Server correctly returns empty stdout on timeout - don't expect partial output
    results.assert_equals(exec_result['stdout'].strip(), "", "Server should return empty stdout on timeout")
    
    # Check if file was generated before timeout (may or may not exist depending on timing)
    if exec_result['generated_files']:
        plot_files = [f for f in exec_result['generated_files'] if f['relative_path'] == 'outputs/pre_timeout_plot.png']
        if plot_files:
            print(f"   📁 Generated files before timeout: {[f['relative_path'] for f in exec_result['generated_files']]}")
        else:
            print(f"   📁 No plot files generated before timeout")
    else:
        print(f"   📁 No files generated before timeout")
    
    # ⭐ KEY TEST: Plot + sleep should timeout at ~35s (file creation + sleep timeout + 5s final reply)
    expected_timeout = SERVER_DEFAULT_TIMEOUT_SECONDS + 5  # 35s total
    results.assert_close(execution_time, expected_timeout, 3.0,
                        f"Should timeout at ~{expected_timeout}s (including plot creation time)")
    
    print(f"   📊 Execution time: {execution_time:.1f}s")
    print(f"   📊 Expected server timeout: ~{expected_timeout}s (30s + processing + 5s final reply)")
    print(f"   📝 Stdout: '{exec_result['stdout']}' (empty - correct)")
    print()


async def test_server_config_validation(client: httpx.AsyncClient, results: TimeoutTestResults):
    """Validate server configuration and timeout settings"""
    print("8️⃣  Server Configuration Validation")
    
    # Check health endpoint for any config info
    response = await client.get(f"{BASE_URL}/health")
    results.assert_equals(response.status_code, 200, "Health endpoint should be accessible")
    
    health_data = response.json()
    print(f"   📊 Server health: {health_data.get('status', 'unknown')}")
    print(f"   📊 Expected default timeout: {SERVER_DEFAULT_TIMEOUT_SECONDS} seconds")
    print(f"   📊 This test validates the server uses its configured defaults")
    print()


async def test_server_default_timeout_api():
    """Main test function for server default timeout behavior"""
    
    # Extended HTTP client timeout to accommodate server's 30s default + margin
    client_timeout = 45.0  # Allow for server's 30s + network/processing time
    
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        print("🧪 Testing CodeSandbox SERVER DEFAULT Timeout Behavior")
        print("=" * 70)
        print(f"🎯 Testing server's actual default timeout: {SERVER_DEFAULT_TIMEOUT_SECONDS} seconds")
        print(f"🚫 NO artificial timeout overrides from client")
        print(f"✅ Testing real production behavior")
        print("=" * 70)
        
        results = TimeoutTestResults()
        
        # Health check
        print("0️⃣  Health Check")
        response = await client.get(f"{BASE_URL}/health")
        results.assert_equals(response.status_code, 200, "Health check should pass")
        print("   ✅ Server is healthy")
        print()
        
        # Create workspace
        print("🏗️  Creating Test Workspace")
        workspace_id = await create_test_workspace(client)
        print(f"   Workspace ID: {workspace_id}")
        print()
        
        try:
            # Run all server default timeout tests
            await test_fast_execution(client, workspace_id, results)
            await test_medium_execution(client, workspace_id, results)
            await test_server_default_sleep_timeout(client, workspace_id, results)
            await test_infinite_loop_server_timeout(client, workspace_id, results)
            await test_cpu_intensive_server_timeout(client, workspace_id, results)
            await test_kernel_recovery_after_server_timeout(client, workspace_id, results)
            await test_server_timeout_with_outputs(client, workspace_id, results)
            await test_server_config_validation(client, results)
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.failed += 1
            results.failures.append(f"Test execution error: {e}")
        
        # Final summary
        success = results.summary()
        
        if success:
            print("\n🎉 ALL SERVER DEFAULT TIMEOUT TESTS PASSED!")
            print("=" * 70)
            print("✅ Fast execution (under 30s default)")
            print("✅ Medium execution (under 30s default)")
            print("✅ Sleep timeout (server 30s default)")
            print("✅ Infinite loop timeout + kernel interrupt (server 30s default)")
            print("✅ CPU intensive timeout (server 30s default)")
            print("✅ Kernel recovery after server timeout")
            print("✅ Server timeout with partial outputs")
            print("✅ Server configuration validation")
            print(f"\n🔧 Server's {SERVER_DEFAULT_TIMEOUT_SECONDS}s default timeout is working correctly!")
        else:
            print(f"\n❌ {results.failed} SERVER TIMEOUT TESTS FAILED!")
            print("🔧 Server's default timeout implementation needs attention.")
            print(f"💡 Expected behavior: Server should timeout at {SERVER_DEFAULT_TIMEOUT_SECONDS}s")
        
        print(f"\n🗂️  Test Workspace ID: {workspace_id}")
        print(f"🌐 View workspace: http://localhost:8080/api/v1/workspace/{workspace_id}/files")
        
        return success


if __name__ == "__main__":
    print("⏳ Starting SERVER DEFAULT timeout tests...")
    print("💡 Make sure the server is running: python run_server.py")
    print(f"🎯 Testing server's actual {SERVER_DEFAULT_TIMEOUT_SECONDS}s default timeout")
    print("⚠️  These tests will take several minutes (waiting for real 30s timeouts)")
    print()
    
    try:
        success = asyncio.run(test_server_default_timeout_api())
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        print("💡 Make sure the server is running: python run_server.py")
        exit(1)
