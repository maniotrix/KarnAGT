#!/usr/bin/env python3
"""
Comprehensive Concurrency System Test Suite

Tests real-world scenarios, edge cases, race conditions, and system limits.
Covers everything that can go wrong in a production concurrency system.
"""

import asyncio
import sys
import time
import random
import gc
import tracemalloc
import traceback
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import statistics

# Add the app directory to path
current_dir = Path(__file__).parent
code_sandbox_path = current_dir.parent          # …/CodeSandbox
sys.path.insert(0, str(code_sandbox_path))


from app.core.concurrency import ConcurrencyManager
from app.domain.models import ExecutionRequest

@dataclass
class TestMetrics:
    """Track test execution metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timed_out_requests: int = 0
    rejected_requests: int = 0
    mix_ups_detected: int = 0
    memory_leaks_detected: int = 0
    race_conditions_detected: int = 0
    execution_times: List[float] = None
    
    def __post_init__(self):
        if self.execution_times is None:
            self.execution_times = []
    
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def avg_execution_time(self) -> float:
        return statistics.mean(self.execution_times) if self.execution_times else 0.0

class ConcurrencyTester:
    """Comprehensive concurrency testing framework"""
    
    def __init__(self):
        self.metrics = TestMetrics()
        self.test_results = {}
        
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run comprehensive test suite"""
        print("🧪 COMPREHENSIVE CONCURRENCY TEST SUITE")
        print("=" * 60)
        
        test_methods = [
            # Core functionality tests
            ("basic_request_isolation", self.test_basic_request_isolation),
            ("high_concurrency_isolation", self.test_high_concurrency_isolation),
            ("workspace_collision_handling", self.test_workspace_collision_handling),
            
            # Resource management tests
            ("resource_exhaustion", self.test_resource_exhaustion),
            ("resource_leak_prevention", self.test_resource_leak_prevention),
            ("semaphore_integrity", self.test_semaphore_integrity),
            
            # Circuit breaker tests
            ("circuit_breaker_states", self.test_circuit_breaker_states),
            ("circuit_breaker_recovery", self.test_circuit_breaker_recovery),
            ("circuit_breaker_under_load", self.test_circuit_breaker_under_load),
            
            # Timeout and cancellation tests
            ("timeout_scenarios", self.test_timeout_scenarios),
            ("cancellation_edge_cases", self.test_cancellation_edge_cases),
            ("timeout_resource_cleanup", self.test_timeout_resource_cleanup),
            
            # Admission controller tests
            ("admission_controller_limits", self.test_admission_controller_limits),
            ("admission_counter_integrity", self.test_admission_counter_integrity),
            ("burst_traffic_handling", self.test_burst_traffic_handling),
            
            # Stress and load tests
            ("system_stress_test", self.test_system_stress_test),
            ("memory_pressure_test", self.test_memory_pressure_test),
            ("mixed_workload_patterns", self.test_mixed_workload_patterns),
            
            # Edge cases and error scenarios
            ("rapid_state_changes", self.test_rapid_state_changes),
            ("exception_propagation", self.test_exception_propagation),
            ("metrics_accuracy", self.test_metrics_accuracy),
            
            # Real-world scenarios
            ("production_burst_simulation", self.test_production_burst_simulation),
            ("degraded_system_behavior", self.test_degraded_system_behavior),
        ]
        
        passed = 0
        total = len(test_methods)
        
        for test_name, test_method in test_methods:
            print(f"\n🔬 Running: {test_name}")
            print("-" * 40)
            
            try:
                # Memory tracking for leak detection
                tracemalloc.start()
                start_memory = tracemalloc.get_traced_memory()[0]
                
                success = await test_method()
                
                end_memory = tracemalloc.get_traced_memory()[0]
                memory_growth = end_memory - start_memory
                tracemalloc.stop()
                
                if memory_growth > 10_000_000:  # 10MB threshold
                    print(f"  ⚠️  Memory growth detected: {memory_growth / 1_000_000:.1f}MB")
                    self.metrics.memory_leaks_detected += 1
                
                self.test_results[test_name] = success
                if success:
                    passed += 1
                    print(f"  ✅ PASSED")
                else:
                    print(f"  ❌ FAILED")
                    
            except Exception as e:
                print(f"  💥 EXCEPTION: {str(e)}")
                print(f"     {traceback.format_exc()}")
                self.test_results[test_name] = False
                tracemalloc.stop()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULTS: {passed}/{total} tests passed")
        print(f"🎯 Success Rate: {passed/total*100:.1f}%")
        
        if self.metrics.memory_leaks_detected > 0:
            print(f"⚠️  Memory leaks detected: {self.metrics.memory_leaks_detected}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - SYSTEM IS ROBUST!")
        else:
            print("⚠️  SOME TESTS FAILED - NEEDS ATTENTION")
            
        return self.test_results
    
    async def test_basic_request_isolation(self) -> bool:
        """Test basic request isolation without mix-ups"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=10,
            request_timeout_seconds=30
        )
        
        results = {}
        
        async def tracked_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(random.uniform(0.01, 0.1))
            return f"result_{request.workspace_id}_{request.code.split('_')[1]}"
        
        # Create 20 requests with unique identifiers
        tasks = []
        expected_results = {}
        
        for i in range(20):
            workspace_id = f"ws_{i % 5}"  # 5 different workspaces
            unique_id = f"req_{i}"
            request = ExecutionRequest(
                workspace_id=workspace_id,
                code=f"print('{unique_id}')",
                timeout=30
            )
            expected_results[unique_id] = f"result_{workspace_id}_{i}"
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, tracked_execution)
            )
            tasks.append((unique_id, task))
        
        # Wait for all completions
        for unique_id, task in tasks:
            try:
                result = await task
                results[unique_id] = result
                self.metrics.successful_requests += 1
            except Exception as e:
                print(f"    Request {unique_id} failed: {e}")
                self.metrics.failed_requests += 1
                
        self.metrics.total_requests += len(tasks)
        
        # Verify no mix-ups
        mix_ups = 0
        for unique_id, result in results.items():
            expected = expected_results[unique_id]
            if result != expected:
                print(f"    MIX-UP: {unique_id} got '{result}', expected '{expected}'")
                mix_ups += 1
                
        self.metrics.mix_ups_detected += mix_ups
        
        print(f"    Processed {len(results)}/{len(tasks)} requests")
        print(f"    Mix-ups detected: {mix_ups}")
        
        return mix_ups == 0 and len(results) == len(tasks)
    
    async def test_high_concurrency_isolation(self) -> bool:
        """Test isolation under high concurrency stress"""
        manager = ConcurrencyManager(
            max_concurrent_executions=5,
            max_concurrent_requests=50,
            request_timeout_seconds=30
        )
        
        # Create 100 concurrent requests
        num_requests = 100
        start_time = time.time()
        
        async def concurrent_execution(request: ExecutionRequest) -> str:
            # Simulate varying execution times
            delay = random.uniform(0.001, 0.05)
            await asyncio.sleep(delay)
            return f"{request.workspace_id}:{request.code.split(':')[1]}"
        
        tasks = []
        for i in range(num_requests):
            workspace_id = f"workspace_{i % 10}"  # 10 workspaces
            request = ExecutionRequest(
                workspace_id=workspace_id,
                code=f"process:{i}",
                timeout=30
            )
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, concurrent_execution)
            )
            tasks.append((i, workspace_id, task))
        
        # Wait for completion with timeout
        completed = 0
        timed_out = 0
        failed = 0
        
        for i, workspace_id, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=60)
                expected = f"{workspace_id}:{i}"
                if result == expected:
                    completed += 1
                else:
                    print(f"    Mismatch: expected {expected}, got {result}")
                    self.metrics.race_conditions_detected += 1
            except asyncio.TimeoutError:
                timed_out += 1
            except Exception as e:
                failed += 1
                print(f"    Request {i} failed: {e}")
        
        duration = time.time() - start_time
        print(f"    Completed: {completed}/{num_requests} in {duration:.2f}s")
        print(f"    Failed: {failed}, Timed out: {timed_out}")
        print(f"    Race conditions detected: {self.metrics.race_conditions_detected}")
        
        # Success if >90% completed without race conditions
        success_rate = completed / num_requests
        return success_rate > 0.9 and self.metrics.race_conditions_detected == 0
    
    async def test_workspace_collision_handling(self) -> bool:
        """Test handling of multiple requests to same workspace"""
        manager = ConcurrencyManager(
            max_concurrent_executions=10,
            max_concurrent_requests=20,
            request_timeout_seconds=30
        )
        
        workspace_id = "shared_workspace"
        execution_order = []
        order_lock = asyncio.Lock()
        
        async def ordered_execution(request: ExecutionRequest) -> str:
            async with order_lock:
                execution_order.append(f"start_{request.code}")
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            async with order_lock:
                execution_order.append(f"end_{request.code}")
            
            return f"completed_{request.code}"
        
        # Launch 10 requests to same workspace
        tasks = []
        for i in range(10):
            request = ExecutionRequest(
                workspace_id=workspace_id,
                code=f"task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, ordered_execution)
            )
            tasks.append(task)
        
        # Wait for all completions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify sequential execution (no overlapping start/end)
        stack = []
        sequential = True
        
        for event in execution_order:
            if event.startswith("start_"):
                stack.append(event.replace("start_", ""))
            elif event.startswith("end_"):
                task_id = event.replace("end_", "")
                if not stack or stack[-1] != task_id:
                    sequential = False
                    break
                stack.pop()
        
        successful_results = [r for r in results if isinstance(r, str) and r.startswith("completed_")]
        
        print(f"    Workspace collision test:")
        print(f"    Successful executions: {len(successful_results)}/10")
        print(f"    Sequential execution: {sequential}")
        print(f"    Execution order length: {len(execution_order)}")
        
        return len(successful_results) == 10 and sequential
    
    async def test_resource_exhaustion(self) -> bool:
        """Test system behavior when resources are exhausted"""
        # Very limited resources
        manager = ConcurrencyManager(
            max_concurrent_executions=2,
            max_concurrent_requests=5,
            request_timeout_seconds=5
        )
        
        async def slow_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(2)  # Tie up resources
            return f"done_{request.workspace_id}"
        
        # Launch more requests than can be handled
        tasks = []
        for i in range(10):
            request = ExecutionRequest(
                workspace_id=f"ws_{i}",
                code=f"slow_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, slow_execution)
            )
            tasks.append(task)
        
        # Wait for all to complete or fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, str))
        rejected = sum(1 for r in results if isinstance(r, Exception) and "overloaded" in str(r))
        timed_out = sum(1 for r in results if isinstance(r, Exception) and "timed out" in str(r))
        
        print(f"    Resource exhaustion test:")
        print(f"    Successful: {successful}")
        print(f"    Rejected: {rejected}")
        print(f"    Timed out: {timed_out}")
        
        # Should have some successful and some rejected/timed out
        return successful > 0 and (rejected > 0 or timed_out > 0)
    
    async def test_resource_leak_prevention(self) -> bool:
        """Test that resources are properly cleaned up and don't leak"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=10,
            request_timeout_seconds=5
        )
        
        initial_stats = manager.get_system_stats()
        initial_active = initial_stats["resource_manager"]["current_active"]
        
        async def resource_using_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(0.1)
            return f"resource_test_{request.workspace_id}"
        
        # Create multiple batches of requests
        for batch in range(3):
            tasks = []
            for i in range(10):
                request = ExecutionRequest(
                    workspace_id=f"leak_test_ws_{i}",
                    code=f"batch_{batch}_task_{i}",
                    timeout=30
                )
                task = asyncio.create_task(
                    manager.execute_with_concurrency_control(request, resource_using_execution)
                )
                tasks.append(task)
            
            # Wait for batch completion
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for resource leaks after each batch
            current_stats = manager.get_system_stats()
            current_active = current_stats["resource_manager"]["current_active"]
            
            if current_active > initial_active:
                print(f"    Resource leak detected after batch {batch}: {current_active} > {initial_active}")
                return False
        
        print(f"    No resource leaks detected across 3 batches")
        return True
    
    async def test_semaphore_integrity(self) -> bool:
        """Test semaphore counter integrity under concurrent access"""
        manager = ConcurrencyManager(
            max_concurrent_executions=5,
            max_concurrent_requests=20,
            request_timeout_seconds=30
        )
        
        integrity_check_results = []
        
        async def integrity_checking_execution(request: ExecutionRequest) -> str:
            # Check resource stats before and after execution
            before_stats = manager.get_system_stats()["resource_manager"]
            await asyncio.sleep(random.uniform(0.01, 0.05))
            after_stats = manager.get_system_stats()["resource_manager"]
            
            # Verify counter consistency
            if before_stats["current_active"] > before_stats["max_concurrent_executions"]:
                integrity_check_results.append(f"Counter overflow detected: {before_stats}")
            
            return f"integrity_ok_{request.workspace_id}"
        
        # Launch many concurrent requests
        tasks = []
        for i in range(50):
            request = ExecutionRequest(
                workspace_id=f"integrity_ws_{i % 8}",
                code=f"integrity_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, integrity_checking_execution)
            )
            tasks.append(task)
        
        # Wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if isinstance(r, str) and r.startswith("integrity_ok_"))
        
        print(f"    Semaphore integrity test: {successful}/{len(tasks)} completed")
        print(f"    Integrity violations: {len(integrity_check_results)}")
        
        return len(integrity_check_results) == 0 and successful > 40
    
    async def test_circuit_breaker_states(self) -> bool:
        """Test all circuit breaker state transitions"""
        manager = ConcurrencyManager(
            max_concurrent_executions=5,
            max_concurrent_requests=10,
            circuit_breaker_threshold=3,
            circuit_recovery_timeout=2,
            request_timeout_seconds=30
        )
        
        async def controllable_execution(request: ExecutionRequest) -> str:
            if "fail" in request.code:
                raise Exception("Controlled failure")
            await asyncio.sleep(0.01)
            return f"success_{request.workspace_id}"
        
        # Phase 1: Circuit should be CLOSED
        stats = manager.circuit_breaker.get_stats()
        if stats['state'] != 'closed':
            print(f"    Expected CLOSED, got {stats['state']}")
            return False
        
        # Phase 2: Cause failures to open circuit
        print("    Causing circuit to OPEN...")
        for i in range(4):  # Exceed threshold of 3
            try:
                request = ExecutionRequest(
                    workspace_id=f"fail_ws_{i}",
                    code=f"fail_task_{i}",
                    timeout=30
                )
                await manager.execute_with_concurrency_control(request, controllable_execution)
            except:
                pass  # Expected failures
        
        stats = manager.circuit_breaker.get_stats()
        if stats['state'] != 'open':
            print(f"    Expected OPEN after failures, got {stats['state']}")
            return False
        
        # Phase 3: Verify new requests are rejected
        try:
            request = ExecutionRequest(
                workspace_id="should_reject",
                code="success_task",
                timeout=30
            )
            await manager.execute_with_concurrency_control(request, controllable_execution)
            print("    Circuit should have rejected request")
            return False
        except Exception as e:
            if "circuit breaker" not in str(e).lower():
                print(f"    Wrong exception type: {e}")
                return False
        
        # Phase 4: Wait for recovery and test HALF_OPEN
        print("    Waiting for circuit recovery...")
        await asyncio.sleep(3)  # Wait for recovery timeout
        
        # Next request should transition to HALF_OPEN
        try:
            request = ExecutionRequest(
                workspace_id="recovery_test",
                code="success_task",
                timeout=30
            )
            result = await manager.execute_with_concurrency_control(request, controllable_execution)
            if not result.startswith("success_"):
                return False
        except Exception as e:
            print(f"    Recovery request failed: {e}")
            return False
        
        # Phase 5: Verify circuit is now CLOSED
        stats = manager.circuit_breaker.get_stats()
        print(f"    Final circuit state: {stats['state']}")
        
        return stats['state'] == 'closed'
    
    async def test_circuit_breaker_recovery(self) -> bool:
        """Test circuit breaker recovery scenarios"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=10,
            circuit_breaker_threshold=2,
            circuit_recovery_timeout=1,
            request_timeout_seconds=30
        )
        
        async def recovery_test_execution(request: ExecutionRequest) -> str:
            if "fail" in request.code:
                raise Exception("Recovery test failure")
            await asyncio.sleep(0.01)
            return f"recovery_success_{request.workspace_id}"
        
        # Phase 1: Open the circuit with failures
        for i in range(3):
            try:
                request = ExecutionRequest(
                    workspace_id=f"fail_ws_{i}",
                    code=f"fail_task_{i}",
                    timeout=30
                )
                await manager.execute_with_concurrency_control(request, recovery_test_execution)
            except:
                pass
        
        # Verify circuit is open
        if manager.circuit_breaker.get_stats()['state'] != 'open':
            print("    Circuit failed to open")
            return False
        
        # Phase 2: Wait for recovery period
        await asyncio.sleep(1.5)
        
        # Phase 3: Test recovery with successful requests
        recovery_attempts = []
        for i in range(5):
            try:
                request = ExecutionRequest(
                    workspace_id=f"recovery_ws_{i}",
                    code=f"success_task_{i}",
                    timeout=30
                )
                result = await manager.execute_with_concurrency_control(request, recovery_test_execution)
                recovery_attempts.append(("success", result))
            except Exception as e:
                recovery_attempts.append(("failed", str(e)))
        
        successful_recoveries = sum(1 for status, _ in recovery_attempts if status == "success")
        final_state = manager.circuit_breaker.get_stats()['state']
        
        print(f"    Recovery attempts: {successful_recoveries}/5 successful")
        print(f"    Final circuit state: {final_state}")
        
        return successful_recoveries >= 3 and final_state == 'closed'
    
    async def test_circuit_breaker_under_load(self) -> bool:
        """Test circuit breaker behavior under high load"""
        manager = ConcurrencyManager(
            max_concurrent_executions=4,
            max_concurrent_requests=15,
            circuit_breaker_threshold=5,
            request_timeout_seconds=30
        )
        
        # Mix of successful and failing requests under load
        failure_rate = 0.3  # 30% failure rate
        
        async def load_test_execution(request: ExecutionRequest) -> str:
            should_fail = random.random() < failure_rate
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
            if should_fail:
                raise Exception("Load test induced failure")
            return f"load_success_{request.workspace_id}"
        
        # Launch high load
        tasks = []
        for i in range(100):
            request = ExecutionRequest(
                workspace_id=f"load_ws_{i % 10}",
                code=f"load_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, load_test_execution)
            )
            tasks.append(task)
        
        # Track outcomes
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        failed = 0
        circuit_rejected = 0
        
        for result in results:
            if isinstance(result, str) and result.startswith("load_success_"):
                successful += 1
            elif isinstance(result, Exception):
                if "circuit breaker" in str(result).lower():
                    circuit_rejected += 1
                else:
                    failed += 1
        
        circuit_stats = manager.circuit_breaker.get_stats()
        
        print(f"    Load test results:")
        print(f"    Successful: {successful}")
        print(f"    Failed: {failed}")
        print(f"    Circuit rejected: {circuit_rejected}")
        print(f"    Final circuit state: {circuit_stats['state']}")
        
        # Circuit should have opened and rejected some requests
        return circuit_rejected > 0 and successful > 0
    
    async def test_timeout_scenarios(self) -> bool:
        """Test various timeout scenarios and cleanup"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=10,
            request_timeout_seconds=1,  # Very short timeout
        )
        
        async def variable_duration_execution(request: ExecutionRequest) -> str:
            duration = float(request.code.split('_')[1])
            await asyncio.sleep(duration)
            return f"completed_after_{duration}"
        
        # Test different timeout scenarios
        test_cases = [
            ("fast_0.1", True),   # Should complete
            ("medium_0.5", True), # Should complete
            ("slow_2.0", False),  # Should timeout
            ("very_slow_5.0", False), # Should timeout
        ]
        
        results = {}
        for code, should_succeed in test_cases:
            request = ExecutionRequest(
                workspace_id="timeout_test",
                code=code,
                timeout=30
            )
            
            start_time = time.time()
            try:
                result = await manager.execute_with_concurrency_control(request, variable_duration_execution)
                duration = time.time() - start_time
                results[code] = ("success", duration, result)
            except Exception as e:
                duration = time.time() - start_time
                results[code] = ("timeout" if "timed out" in str(e) else "error", duration, str(e))
        
        # Verify results
        all_correct = True
        for code, should_succeed in test_cases:
            result_type, duration, _ = results[code]
            actual_success = result_type == "success"
            
            print(f"    {code}: {result_type} in {duration:.2f}s (expected {'success' if should_succeed else 'timeout'})")
            
            if actual_success != should_succeed:
                all_correct = False
        
        return all_correct
    
    async def test_cancellation_edge_cases(self) -> bool:
        """Test edge cases in request cancellation"""
        manager = ConcurrencyManager(
            max_concurrent_executions=2,
            max_concurrent_requests=5,
            request_timeout_seconds=2
        )
        
        cancelled_cleanly = 0
        
        async def cancellable_execution(request: ExecutionRequest) -> str:
            try:
                # Long running task that should be cancelled
                await asyncio.sleep(5)
                return f"should_not_complete_{request.workspace_id}"
            except asyncio.CancelledError:
                nonlocal cancelled_cleanly
                cancelled_cleanly += 1
                raise
        
        # Start tasks that will timeout/cancel
        tasks = []
        for i in range(8):  # More than max_concurrent_requests
            request = ExecutionRequest(
                workspace_id=f"cancel_ws_{i}",
                code=f"cancel_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, cancellable_execution)
            )
            tasks.append(task)
        
        # Wait for results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        timeouts = sum(1 for r in results if isinstance(r, Exception) and "timed out" in str(r))
        rejected = sum(1 for r in results if isinstance(r, Exception) and "overloaded" in str(r))
        
        print(f"    Cancellation test:")
        print(f"    Timed out: {timeouts}")
        print(f"    Rejected: {rejected}")
        print(f"    Cancelled cleanly: {cancelled_cleanly}")
        
        return timeouts > 0 or rejected > 0  # Should have some timeouts or rejections
    
    async def test_timeout_resource_cleanup(self) -> bool:
        """Test resource cleanup after timeouts"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=8,
            request_timeout_seconds=1
        )
        
        initial_stats = manager.get_system_stats()
        
        async def timeout_prone_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(3)  # Will timeout
            return f"timeout_complete_{request.workspace_id}"
        
        # Launch requests that will timeout
        tasks = []
        for i in range(6):
            request = ExecutionRequest(
                workspace_id=f"timeout_cleanup_ws_{i}",
                code=f"timeout_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, timeout_prone_execution)
            )
            tasks.append(task)
        
        # Wait for timeouts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        timeouts = sum(1 for r in results if isinstance(r, Exception) and "timed out" in str(r))
        
        # Check resource cleanup
        await asyncio.sleep(0.5)  # Give time for cleanup
        final_stats = manager.get_system_stats()
        
        resources_cleaned = (initial_stats["resource_manager"]["current_active"] == 
                           final_stats["resource_manager"]["current_active"])
        
        print(f"    Timeout cleanup test:")
        print(f"    Timeouts: {timeouts}")
        print(f"    Resources cleaned up: {resources_cleaned}")
        
        return timeouts > 0 and resources_cleaned
    
    async def test_admission_controller_limits(self) -> bool:
        """Test admission controller boundary conditions"""
        manager = ConcurrencyManager(
            max_concurrent_executions=10,
            max_concurrent_requests=5,  # Very limited
            request_timeout_seconds=30
        )
        
        async def admission_test_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(0.1)
            return f"admission_ok_{request.workspace_id}"
        
        # Launch more requests than admission limit
        tasks = []
        for i in range(15):
            request = ExecutionRequest(
                workspace_id=f"admission_ws_{i}",
                code=f"admission_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, admission_test_execution)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, str))
        rejected = sum(1 for r in results if isinstance(r, Exception) and "overloaded" in str(r))
        
        print(f"    Admission limits test:")
        print(f"    Successful: {successful}")
        print(f"    Rejected: {rejected}")
        print(f"    Total: {len(results)}")
        
        # Should have some successful and some rejected
        return successful > 0 and rejected > 0 and (successful + rejected) == len(results)
    
    async def test_admission_counter_integrity(self) -> bool:
        """Test admission controller counter integrity"""
        manager = ConcurrencyManager(
            max_concurrent_executions=5,
            max_concurrent_requests=10,
            request_timeout_seconds=30
        )
        
        counter_violations = []
        
        async def counter_checking_execution(request: ExecutionRequest) -> str:
            stats = manager.get_system_stats()["admission_controller"]
            if stats["current_requests"] > stats["max_concurrent_requests"]:
                counter_violations.append(f"Counter violation: {stats}")
            
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return f"counter_ok_{request.workspace_id}"
        
        # Rapid fire requests
        tasks = []
        for i in range(50):
            request = ExecutionRequest(
                workspace_id=f"counter_ws_{i % 5}",
                code=f"counter_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, counter_checking_execution)
            )
            tasks.append(task)
            
            # Small delay to create contention
            if i % 10 == 0:
                await asyncio.sleep(0.001)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if isinstance(r, str))
        
        print(f"    Counter integrity test:")
        print(f"    Successful: {successful}")
        print(f"    Counter violations: {len(counter_violations)}")
        
        return len(counter_violations) == 0
    
    async def test_burst_traffic_handling(self) -> bool:
        """Test handling of sudden traffic bursts"""
        manager = ConcurrencyManager(
            max_concurrent_executions=4,
            max_concurrent_requests=12,
            request_timeout_seconds=30
        )
        
        async def burst_execution(request: ExecutionRequest) -> str:
            await asyncio.sleep(random.uniform(0.05, 0.2))
            return f"burst_handled_{request.workspace_id}"
        
        # Simulate burst: launch many requests very quickly
        burst_tasks = []
        burst_start = time.time()
        
        for i in range(30):  # 30 requests in quick succession
            request = ExecutionRequest(
                workspace_id=f"burst_ws_{i % 6}",
                code=f"burst_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, burst_execution)
            )
            burst_tasks.append(task)
            
            # Very small delay to simulate burst
            await asyncio.sleep(0.01)
        
        burst_duration = time.time() - burst_start
        
        # Wait for results
        results = await asyncio.gather(*burst_tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, str))
        rejected = sum(1 for r in results if isinstance(r, Exception) and "overloaded" in str(r))
        failed = len(results) - successful - rejected
        
        print(f"    Burst traffic test:")
        print(f"    Burst launched in {burst_duration:.3f}s")
        print(f"    Successful: {successful}")
        print(f"    Rejected: {rejected}")
        print(f"    Failed: {failed}")
        
        # System should handle burst gracefully
        return successful > 10 and (rejected > 0 or successful + rejected == len(results))
    
    async def test_system_stress_test(self) -> bool:
        """Comprehensive system stress test"""
        manager = ConcurrencyManager(
            max_concurrent_executions=8,
            max_concurrent_requests=50,
            request_timeout_seconds=30
        )
        
        print("    Starting system stress test...")
        start_time = time.time()
        
        # Mix of different request types
        request_types = [
            ("fast", 0.01, 0.95),    # Fast requests, 95% success expected
            ("medium", 0.1, 0.90),   # Medium requests, 90% success expected
            ("slow", 0.3, 0.80),     # Slow requests, 80% success expected
            ("variable", None, 0.85), # Variable duration, 85% success expected
        ]
        
        all_tasks = []
        
        # Create 200 mixed requests
        for i in range(200):
            request_type, base_duration, expected_success_rate = random.choice(request_types)
            workspace_id = f"stress_ws_{i % 20}"  # 20 different workspaces
            
            if request_type == "variable":
                duration = random.uniform(0.01, 0.5)
            else:
                duration = (base_duration or 0.1) + random.uniform(-0.005, 0.005)
            
            request = ExecutionRequest(
                workspace_id=workspace_id,
                code=f"{request_type}_{duration:.3f}",
                timeout=30
            )
            
            async def stress_execution(req: ExecutionRequest) -> str:
                parts = req.code.split('_')
                duration = float(parts[1])
                await asyncio.sleep(duration)
                return f"stress_result_{req.workspace_id}_{parts[0]}"
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, stress_execution)
            )
            all_tasks.append((i, request_type, task))
        
        # Wait for all tasks to complete
        outcomes = {"success": 0, "timeout": 0, "rejected": 0, "error": 0}
        
        for i, request_type, task in all_tasks:
            try:
                result = await task
                if result and result.startswith("stress_result_"):
                    outcomes["success"] += 1
                else:
                    outcomes["error"] += 1
            except Exception as e:
                error_msg = str(e).lower()
                if "timed out" in error_msg:
                    outcomes["timeout"] += 1
                elif "overloaded" in error_msg or "circuit breaker" in error_msg:
                    outcomes["rejected"] += 1
                else:
                    outcomes["error"] += 1
        
        duration = time.time() - start_time
        total_requests = len(all_tasks)
        success_rate = outcomes["success"] / total_requests
        
        print(f"    Stress test completed in {duration:.2f}s")
        print(f"    Total requests: {total_requests}")
        print(f"    Success: {outcomes['success']} ({success_rate:.1%})")
        print(f"    Timeout: {outcomes['timeout']}")
        print(f"    Rejected: {outcomes['rejected']}")
        print(f"    Error: {outcomes['error']}")
        
        # Get system stats
        stats = manager.get_system_stats()
        print(f"    Final system stats: {stats['system_health']}")
        
        # Success criteria: >70% success rate and system health
        return success_rate > 0.7 and duration < 60
    
    async def test_memory_pressure_test(self) -> bool:
        """Test system behavior under memory pressure"""
        # This is a simplified memory pressure test
        manager = ConcurrencyManager(
            max_concurrent_executions=6,
            max_concurrent_requests=20,
            request_timeout_seconds=30
        )
        
        # Track memory usage
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        memory_intensive_data = []
        
        async def memory_using_execution(request: ExecutionRequest) -> str:
            # Simulate memory usage
            local_data = [i for i in range(1000)]  # Small memory allocation
            await asyncio.sleep(0.05)
            memory_intensive_data.append(local_data)  # Keep reference
            return f"memory_test_{request.workspace_id}"
        
        # Launch memory-intensive requests
        tasks = []
        for i in range(50):
            request = ExecutionRequest(
                workspace_id=f"memory_ws_{i % 8}",
                code=f"memory_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, memory_using_execution)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = tracemalloc.get_traced_memory()[0]
        memory_growth = final_memory - initial_memory
        tracemalloc.stop()
        
        successful = sum(1 for r in results if isinstance(r, str))
        
        print(f"    Memory pressure test:")
        print(f"    Successful: {successful}")
        print(f"    Memory growth: {memory_growth / 1_000_000:.1f}MB")
        
        # Clean up
        memory_intensive_data.clear()
        gc.collect()
        
        # Should complete most requests without excessive memory growth
        return successful > 40 and memory_growth < 50_000_000  # Less than 50MB growth
    
    async def test_mixed_workload_patterns(self) -> bool:
        """Test system with mixed workload patterns"""
        manager = ConcurrencyManager(
            max_concurrent_executions=6,
            max_concurrent_requests=20,
            request_timeout_seconds=30
        )
        
        # Different workload types
        workload_types = [
            ("cpu_intensive", 0.1, 1.0),     # CPU intensive, longer duration
            ("io_bound", 0.05, 0.3),         # I/O bound, medium duration  
            ("quick_burst", 0.01, 0.8),      # Quick requests, high frequency
            ("mixed_duration", None, 0.6),   # Variable duration
        ]
        
        all_tasks = []
        workload_results: Dict[str, Dict[str, int]] = {wtype: {"success": 0, "failed": 0} for wtype, _, _ in workload_types}
        
        # Create mixed workload
        for i in range(80):
            workload_type, base_duration, frequency = random.choice(workload_types)
            
            if workload_type == "mixed_duration":
                duration = random.uniform(0.01, 0.2)
            else:
                duration = (base_duration or 0.1) + random.uniform(-0.01, 0.01)
            
            request = ExecutionRequest(
                workspace_id=f"mixed_ws_{i % 12}",
                code=f"{workload_type}_{duration:.3f}",
                timeout=30
            )
            
            async def mixed_execution(req: ExecutionRequest) -> str:
                parts = req.code.split('_')
                duration = float(parts[1])
                await asyncio.sleep(duration)
                return f"mixed_result_{req.workspace_id}_{parts[0]}"
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, mixed_execution)
            )
            all_tasks.append((workload_type, task))
        
        # Execute mixed workload
        for workload_type, task in all_tasks:
            try:
                result = await task
                if result and "mixed_result_" in result:
                    workload_results[workload_type]["success"] += 1
                else:
                    workload_results[workload_type]["failed"] += 1
            except Exception:
                workload_results[workload_type]["failed"] += 1
        
        # Analyze results
        print(f"    Mixed workload results:")
        overall_success = True
        total_success = 0
        total_requests = 0
        
        for workload_type, results in workload_results.items():
            total = results["success"] + results["failed"]  
            success_rate = results["success"] / total if total > 0 else 0
            print(f"      {workload_type}: {results['success']}/{total} ({success_rate:.1%})")
            
            total_success += results["success"]
            total_requests += total
            
            if success_rate < 0.7:  # Expect at least 70% success per workload type
                overall_success = False
        
        overall_rate = total_success / total_requests if total_requests > 0 else 0
        print(f"    Overall success rate: {overall_rate:.1%}")
        
        return overall_success and overall_rate > 0.8
    
    async def test_rapid_state_changes(self) -> bool:
        """Test system behavior during rapid state changes"""
        manager = ConcurrencyManager(
            max_concurrent_executions=3,
            max_concurrent_requests=8,
            circuit_breaker_threshold=3,
            circuit_recovery_timeout=1,
            request_timeout_seconds=30
        )
        
        state_changes_detected = []
        
        async def state_changing_execution(request: ExecutionRequest) -> str:
            # Randomly succeed or fail to cause state changes
            if random.random() < 0.4:  # 40% failure rate
                raise Exception("State change test failure")
            
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return f"state_test_{request.workspace_id}"
        
        # Rapid succession of requests to trigger state changes
        tasks = []
        for i in range(30):
            request = ExecutionRequest(
                workspace_id=f"state_ws_{i % 5}",
                code=f"state_task_{i}",
                timeout=30
            )
            
            # Monitor circuit state before each request
            current_state = manager.circuit_breaker.get_stats()['state']
            state_changes_detected.append(current_state)
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, state_changing_execution)
            )
            tasks.append(task)
            
            # Small delay to observe state changes
            await asyncio.sleep(0.02)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, str))
        failed = len(results) - successful
        
        # Count unique states encountered
        unique_states = set(state_changes_detected)
        
        print(f"    Rapid state changes test:")
        print(f"    Successful: {successful}")
        print(f"    Failed: {failed}")
        print(f"    States encountered: {unique_states}")
        
        # Should see multiple states and handle transitions gracefully
        return len(unique_states) >= 2 and successful > 0
    
    async def test_exception_propagation(self) -> bool:
        """Test proper exception handling and propagation"""
        manager = ConcurrencyManager(
            max_concurrent_executions=4,
            max_concurrent_requests=10,
            request_timeout_seconds=30
        )
        
        exception_types: Dict[str, int] = {}
        
        async def exception_test_execution(request: ExecutionRequest) -> str:
            exception_type = request.code.split('_')[1]
            
            if exception_type == "timeout":
                await asyncio.sleep(5)  # Will timeout
            elif exception_type == "runtime":
                raise RuntimeError("Test runtime error")
            elif exception_type == "value":
                raise ValueError("Test value error")
            elif exception_type == "custom":
                class CustomError(Exception):
                    pass
                raise CustomError("Test custom error")
            else:
                return f"success_{request.workspace_id}"
            
            # This line should never be reached due to the exception or return above
            return f"fallback_{request.workspace_id}"
        
        # Test different exception scenarios
        test_cases = [
            ("success", 5),
            ("runtime", 3),
            ("value", 3),
            ("custom", 2),
            ("timeout", 2),
        ]
        
        tasks = []
        for exception_type, count in test_cases:
            for i in range(count):
                request = ExecutionRequest(
                    workspace_id=f"exception_ws_{i}",
                    code=f"test_{exception_type}_{i}",
                    timeout=30
                )
                task = asyncio.create_task(
                    manager.execute_with_concurrency_control(request, exception_test_execution)
                )
                tasks.append((exception_type, task))
        
        # Collect results and categorize exceptions
        for exception_type, task in tasks:
            try:
                result = await task
                if isinstance(result, str):
                    exception_types.setdefault("success", 0)
                    exception_types["success"] += 1
            except Exception as e:
                error_category = "unknown"
                error_msg = str(e).lower()
                
                if "timed out" in error_msg:
                    error_category = "timeout"
                elif "runtime" in error_msg:
                    error_category = "runtime"
                elif "value" in error_msg:
                    error_category = "value"
                elif "custom" in error_msg:
                    error_category = "custom"
                
                exception_types.setdefault(error_category, 0)
                exception_types[error_category] += 1
        
        print(f"    Exception propagation test:")
        for exc_type, count in exception_types.items():
            print(f"      {exc_type}: {count}")
        
        # Should properly handle all exception types
        expected_categories = {"success", "timeout", "runtime", "value", "custom"}
        actual_categories = set(exception_types.keys())
        
        return expected_categories.issubset(actual_categories)
    
    async def test_metrics_accuracy(self) -> bool:
        """Test accuracy of system metrics under load"""
        manager = ConcurrencyManager(
            max_concurrent_executions=4,
            max_concurrent_requests=20,
            request_timeout_seconds=30
        )
        
        # Track our own metrics
        our_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "active_workspaces": set()
        }
        
        async def metric_tracked_execution(request: ExecutionRequest) -> str:
            active_workspaces = our_metrics["active_workspaces"]
            assert isinstance(active_workspaces, set)
            active_workspaces.add(request.workspace_id)
            await asyncio.sleep(random.uniform(0.01, 0.1))
            return f"metrics_test_{request.workspace_id}"
        
        # Create varied workload
        tasks = []
        for i in range(50):
            workspace_id = f"metrics_ws_{i % 8}"
            request = ExecutionRequest(
                workspace_id=workspace_id,
                code=f"metrics_task_{i}",
                timeout=30
            )
            total_requests = our_metrics["total_requests"]
            assert isinstance(total_requests, int)
            our_metrics["total_requests"] = total_requests + 1
            
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, metric_tracked_execution)
            )
            tasks.append(task)
        
        # Execute and track results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failed_count = our_metrics["failed"]
                assert isinstance(failed_count, int)
                our_metrics["failed"] = failed_count + 1
            else:
                successful_count = our_metrics["successful"]
                assert isinstance(successful_count, int)
                our_metrics["successful"] = successful_count + 1
        
        # Compare with system metrics
        system_stats = manager.get_system_stats()
        admission_stats = system_stats["admission_controller"]
        workspace_stats = system_stats["workspace_locks"]
        
        print(f"    Our metrics: {our_metrics}")
        print(f"    System admission stats: {admission_stats}")
        print(f"    System workspace stats: {workspace_stats}")
        
        # Verify metrics consistency
        metrics_accurate = True
        
        # Check if system tracked similar number of requests
        if abs(admission_stats["total_requests"] - our_metrics["total_requests"]) > 5:
            print(f"    Request count mismatch!")
            metrics_accurate = False
        
        # Check workspace tracking
        if workspace_stats["total_workspace_locks"] == 0:
            print(f"    No workspace locks recorded!")
            metrics_accurate = False
        
        return metrics_accurate
    
    async def test_production_burst_simulation(self) -> bool:
        """Simulate production burst traffic patterns"""
        manager = ConcurrencyManager(
            max_concurrent_executions=6,
            max_concurrent_requests=30,
            request_timeout_seconds=60
        )
        
        print("    Simulating production burst patterns...")
        
        # Simulate realistic burst pattern
        burst_phases = [
            ("warmup", 5, 0.1),      # 5 requests, 0.1s apart
            ("normal", 10, 0.05),    # 10 requests, 0.05s apart  
            ("burst", 50, 0.01),     # 50 requests, 0.01s apart (burst!)
            ("recovery", 15, 0.2),   # 15 requests, 0.2s apart
        ]
        
        all_tasks = []
        
        for phase_name, count, interval in burst_phases:
            print(f"      Phase: {phase_name} ({count} requests)")
            phase_start = time.time()
            
            for i in range(count):
                workspace_id = f"burst_ws_{i % 5}"
                request = ExecutionRequest(
                    workspace_id=workspace_id,
                    code=f"{phase_name}_task_{i}",
                    timeout=30
                )
                
                async def burst_execution(req: ExecutionRequest) -> str:
                    # Simulate realistic work duration
                    work_time = random.uniform(0.05, 0.3)
                    await asyncio.sleep(work_time)
                    return f"burst_result_{req.workspace_id}_{req.code}"
                
                task = asyncio.create_task(
                    manager.execute_with_concurrency_control(request, burst_execution)
                )
                all_tasks.append((phase_name, task))
                
                # Wait before next request in this phase
                await asyncio.sleep(interval)
            
            phase_duration = time.time() - phase_start
            print(f"        Launched {count} requests in {phase_duration:.2f}s")
        
        # Wait for all phases to complete
        print("    Waiting for all phases to complete...")
        phase_outcomes: Dict[str, Dict[str, int]] = {phase: {"success": 0, "failed": 0} for phase, _, _ in burst_phases}
        
        for phase_name, task in all_tasks:
            try:
                result = await task
                if result and "burst_result_" in result:
                    phase_outcomes[phase_name]["success"] += 1
                else:
                    phase_outcomes[phase_name]["failed"] += 1
            except Exception as e:
                phase_outcomes[phase_name]["failed"] += 1
                if "overloaded" not in str(e) and "circuit breaker" not in str(e):
                    print(f"        Unexpected error in {phase_name}: {e}")
        
        # Analyze results
        print("    Phase Results:")
        overall_success = True
        
        for phase_name, outcomes in phase_outcomes.items():
            total = outcomes["success"] + outcomes["failed"]
            success_rate = outcomes["success"] / total if total > 0 else 0
            print(f"      {phase_name}: {outcomes['success']}/{total} ({success_rate:.1%})")
            
            # Different success rate expectations per phase
            expected_rates = {
                "warmup": 0.95,
                "normal": 0.90,
                "burst": 0.60,    # Expect some rejections during burst
                "recovery": 0.85
            }
            
            if success_rate < expected_rates.get(phase_name, 0.8):
                overall_success = False
        
        # Check system health after burst
        final_stats = manager.get_system_stats()
        system_healthy = manager.is_system_healthy()
        
        print(f"    System healthy after burst: {system_healthy}")
        print(f"    Final system utilization: {final_stats['system_health']}")
        
        return overall_success and system_healthy
    
    async def test_degraded_system_behavior(self) -> bool:
        """Test system behavior under degraded conditions"""
        manager = ConcurrencyManager(
            max_concurrent_executions=2,  # Very limited
            max_concurrent_requests=4,   # Very limited
            circuit_breaker_threshold=2,
            request_timeout_seconds=3,   # Short timeout
        )
        
        print("    Testing degraded system conditions...")
        
        async def degraded_execution(request: ExecutionRequest) -> str:
            # Simulate degraded performance
            degradation_factor = random.uniform(1.5, 3.0)  # 1.5x to 3x slower
            base_time = 0.1
            await asyncio.sleep(base_time * degradation_factor)
            
            # Occasional failures due to degradation
            if random.random() < 0.2:  # 20% failure rate
                raise Exception("Degraded system failure")
            
            return f"degraded_success_{request.workspace_id}"
        
        # Launch requests under degraded conditions
        tasks = []
        for i in range(20):
            request = ExecutionRequest(
                workspace_id=f"degraded_ws_{i % 3}",
                code=f"degraded_task_{i}",
                timeout=30
            )
            task = asyncio.create_task(
                manager.execute_with_concurrency_control(request, degraded_execution)
            )
            tasks.append(task)
        
        # Execute under degraded conditions
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        successful = sum(1 for r in results if isinstance(r, str))
        failed = sum(1 for r in results if isinstance(r, Exception) and "degraded system" in str(r))
        rejected = sum(1 for r in results if isinstance(r, Exception) and "overloaded" in str(r))
        timed_out = sum(1 for r in results if isinstance(r, Exception) and "timed out" in str(r))
        circuit_blocked = sum(1 for r in results if isinstance(r, Exception) and "circuit breaker" in str(r))
        
        print(f"    Degraded system test results:")
        print(f"    Duration: {duration:.2f}s")
        print(f"    Successful: {successful}")
        print(f"    Failed: {failed}")
        print(f"    Rejected: {rejected}")
        print(f"    Timed out: {timed_out}")
        print(f"    Circuit blocked: {circuit_blocked}")
        
        # System should still function but with reduced throughput
        total_handled = successful + failed + rejected + timed_out + circuit_blocked
        system_responsive = total_handled == len(tasks)
        some_success = successful > 0
        
        # Final system health check
        final_health = manager.is_system_healthy()
        print(f"    System health after degradation: {final_health}")
        
        return system_responsive and some_success

# Execute comprehensive tests
async def main():
    """Run comprehensive concurrency tests"""
    tester = ConcurrencyTester()
    results = await tester.run_all_tests()
    
    # Additional summary
    print("\n" + "🔍" + " DETAILED ANALYSIS " + "🔍")
    print("=" * 60)
    
    failed_tests = [name for name, passed in results.items() if not passed]
    if failed_tests:
        print("❌ Failed Tests:")
        for test_name in failed_tests:
            print(f"   - {test_name}")
    
    print(f"\n📈 Overall Metrics:")
    print(f"   Total Requests Processed: {tester.metrics.total_requests}")
    print(f"   Success Rate: {tester.metrics.success_rate():.1%}")
    print(f"   Mix-ups Detected: {tester.metrics.mix_ups_detected}")
    print(f"   Race Conditions: {tester.metrics.race_conditions_detected}")
    print(f"   Memory Leaks: {tester.metrics.memory_leaks_detected}")
    
    if len(failed_tests) == 0:
        print("\n🎉 SYSTEM IS PRODUCTION READY!")
        print("   All concurrency scenarios handled correctly")
        print("   No race conditions or data corruption detected")
        print("   System degrades gracefully under load")
    else:
        print(f"\n⚠️  SYSTEM NEEDS ATTENTION ({len(failed_tests)} issues)")
        print("   Review failed tests before production deployment")

if __name__ == "__main__":
    asyncio.run(main())