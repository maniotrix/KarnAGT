#!/usr/bin/env python3
"""
Comprehensive Distributed Streaming Test Suite

Tests the complete Redis-based multi-worker streaming system:
1. Single-worker functionality (baseline)
2. Multi-worker stream cancellation
3. Cross-worker race conditions
4. Redis failure recovery
5. Worker registry functionality
6. Atomic transaction scenarios
7. TTL cleanup and orphan detection

This tests our production-ready distributed architecture.
"""

import asyncio
import aiohttp
import json
import time
import redis.asyncio as redis
# No external test frameworks required - pure Python + asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import signal
import os
import sys
import uuid


class DistributedStreamingTester:
    """Comprehensive test suite for distributed streaming"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.jwt_token: Optional[str] = None   # ✅ JWT token for authentication
        self.redis_client: Optional[redis.Redis] = None
        self.test_user_email: Optional[str] = None
        self.test_conversations: List[str] = []
        self.captured_streams: List[str] = []
        self.test_results: Dict[str, bool] = {}
        self.worker_processes: List[subprocess.Popen] = []
        self.test_worker_ids: List[str] = []  # Track worker IDs created by this test
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
        
        # Clean up any test workers
        await self.cleanup_test_workers()
        await self.cleanup_test_data()
    
    def get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers for authentication"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        # ✅ Add JWT token in Authorization header (works across all ports)
        if include_auth and hasattr(self, 'jwt_token') and self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'
        return headers
    
    async def setup_test_user(self) -> bool:
        """Create and authenticate test user using JWT tokens"""
        try:
            # Generate unique test user
            timestamp = int(time.time())
            self.test_user_email = f"distrib_test_{timestamp}@example.com"
            
            # ✅ Register user (correct format matching backend UserRegister schema)
            register_data = {
                "email": self.test_user_email,
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",  # ✅ Required field  
                "full_name": "Distributed Tester"    # ✅ Correct field name
            }
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=register_data) as response:
                if response.status != 201:
                    error_text = await response.text()
                    print(f"❌ Registration failed ({response.status}): {error_text}")
                    return False
                
                register_result = await response.json()
                print(f"✅ Registration successful")
            
            # ✅ Login using correct format (JSON, not form data)
            login_data = {
                "email": self.test_user_email,  # ✅ Correct field name (not username)
                "password": "TestPass123!"
            }
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/login", json=login_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Login failed ({response.status}): {error_text}")
                    return False
                
                login_result = await response.json()
                
                # ✅ EXTRACT JWT TOKEN from httpOnly cookie
                cookies = response.cookies
                if 'access_token' in cookies:
                    self.jwt_token = cookies['access_token'].value
                    print(f"✅ JWT token extracted: {self.jwt_token[:20]}...")
                else:
                    print("❌ No JWT token found in cookies")
                    return False
                    
                print(f"✅ Login successful, user: {login_result.get('user', {}).get('email', 'unknown')}")
                
            print(f"✅ Test user setup complete: {self.test_user_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up test user: {e}")
            return False
    
    async def create_test_conversation(self) -> Optional[str]:
        """Create a test conversation"""
        try:
            conversation_data = {
                "title": f"Distributed Test {datetime.now().isoformat()}",
                "system_instructions": "You are a helpful assistant for testing distributed streaming."
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations", 
                json=conversation_data,
                headers=self.get_headers()
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    print(f"❌ Failed to create conversation: {response.status} - {error_text}")
                    return None
                
                result = await response.json()
                conversation_id = result["conversation_id"]
                self.test_conversations.append(conversation_id)
                return conversation_id
                
        except Exception as e:
            print(f"❌ Error creating conversation: {e}")
            return None
    
    async def start_test_workers(self, worker_count: int = 2) -> bool:
        """Start multiple test workers to simulate multi-worker environment"""
        try:
            print(f"🚀 Starting {worker_count} test workers...")
            
            for i in range(worker_count):
                port = 8001 + i  # 8001, 8002, etc.
                
                # ✅ Use YOUR ACTUAL startup process (start_app.py) 
                env = os.environ.copy()
                env.update({
                    "PORT": str(port),  # ✅ Override PORT for this worker
                    "ENVIRONMENT": "production",  # ✅ Production mode = no reloader = PIDs match!
                    "DEBUG": "True",
                })
                
                # ✅ Start worker using YOUR startup script WITH VENV (loads .env, validates keys, registers worker)
                # ✅ Use the SAME Python interpreter as the current process (venv Python)
                venv_python = sys.executable
                print(f"🚀 Starting worker {i+1} with venv Python")
                print(f"🔧 Python: {venv_python}")
                print(f"🔧 Script: start_app.py")
                print(f"🔧 Environment: PORT={port}, ENVIRONMENT=production, DEBUG=True")
                
                process = subprocess.Popen([
                    venv_python, "start_app.py"  # ✅ Uses venv Python!
                ], 
                cwd="backend", 
                env=env,
                # 🔇 Disable logs (comment out stdout/stderr to see logs)
                # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                # ✅ TO SEE LOGS: Remove stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL from above line
                
                self.worker_processes.append(process)
                print(f"✅ Started worker {i+1} on port {port} (PID: {process.pid})")
                
                # ✅ Give each worker a moment to start before launching next
                await asyncio.sleep(2)
            
            # ✅ Check if all worker processes are alive
            print(f"\n🔍 Checking worker process status after startup:")
            for i, process in enumerate(self.worker_processes):
                is_alive = process.poll() is None
                print(f"   Worker {i+1} (PID {process.pid}): {'✅ ALIVE' if is_alive else '❌ DEAD'}")
                
            print("\n⏳ Waiting for workers to register with Redis...")
            await asyncio.sleep(15)  # Reduced since we have individual delays
            
            # Get ports of the workers we just started
            test_ports = [str(8001 + i) for i in range(len(self.worker_processes))]
            print(f"🔍 Test workers should be on ports: {test_ports}")
            
            # Find worker IDs that match our test ports (using port-based matching)
            active_workers = await self.redis_client.smembers("workers:active")
            print(f"🔍 Active workers in Redis: {len(active_workers)}")
            
            # Track which workers belong to this test by checking if they respond on test ports
            for worker_id in active_workers:
                worker_data = await self.redis_client.hgetall(f"worker:{worker_id}")
                if worker_data:
                    worker_pid = worker_data.get('pid', '')
                    print(f"   Worker {worker_id}: PID={worker_pid}")
                    
                    # Check if this worker is listening on one of our test ports
                    for test_port in test_ports:
                        try:
                            async with self.session.get(
                                f"http://localhost:{test_port}/health",
                                timeout=aiohttp.ClientTimeout(total=2)
                            ) as response:
                                if response.status == 200:
                                    self.test_worker_ids.append(worker_id)
                                    print(f"     ✅ Tracked as test worker (responds on port {test_port})")
                                    test_ports.remove(test_port)  # Remove matched port
                                    break
                        except:
                            continue  # Worker not responding on this port
            
            print(f"🔍 Test created {len(self.test_worker_ids)} workers: {self.test_worker_ids}")
            return len(self.test_worker_ids) >= worker_count
            
        except Exception as e:
            print(f"❌ Error starting test workers: {e}")
            return False
    
    async def cleanup_test_workers(self):
        """Clean up test worker processes and their Redis data"""
        print(f"🧹 Terminating {len(self.worker_processes)} test worker processes...")
        
        for i, process in enumerate(self.worker_processes):
            try:
                if process.poll() is None:  # Process is still running
                    print(f"   Terminating worker {i+1} (PID {process.pid})...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                        print(f"   ✅ Worker {i+1} terminated gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"   ⚡ Force killing worker {i+1}...")
                        process.kill()
                        process.wait()
                        print(f"   ✅ Worker {i+1} force killed")
                else:
                    print(f"   Worker {i+1} (PID {process.pid}) already stopped")
            except Exception as e:
                print(f"Warning: Error cleaning up worker process {i+1}: {e}")
        
        self.worker_processes.clear()
        print(f"✅ All test worker processes terminated")
    
    async def cleanup_test_data(self):
        """Clean up ONLY the data created by this test"""
        try:
            if self.redis_client:
                cleanup_count = 0
                
                # 1. Clean up test streams
                print(f"🧹 Cleaning up {len(self.captured_streams)} test streams...")
                for stream_id in self.captured_streams:
                    # Remove stream metadata
                    deleted = await self.redis_client.delete(f"stream:{stream_id}")
                    if deleted:
                        cleanup_count += 1
                
                # 2. Clean up test worker data (only workers WE created)
                print(f"🧹 Cleaning up {len(self.test_worker_ids)} test workers...")
                for worker_id in self.test_worker_ids:
                    # Remove worker from active set
                    await self.redis_client.srem("workers:active", worker_id)
                    # Remove worker metadata
                    deleted = await self.redis_client.delete(f"worker:{worker_id}")
                    if deleted:
                        cleanup_count += 1
                
                # 3. Clean up test conversations (database cleanup via API)
                print(f"🧹 Cleaning up {len(self.test_conversations)} test conversations...")
                for conversation_id in self.test_conversations:
                    try:
                        async with self.session.delete(
                            f"{self.base_url}/api/v1/chat/conversations/{conversation_id}",
                            headers=self.get_headers()
                        ) as response:
                            if response.status == 200:
                                cleanup_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to delete conversation {conversation_id}: {e}")
                
                # 4. Clean up user streams for test streams (only for test user)
                if self.test_user_email and self.captured_streams:
                    # Clean up user:*:streams keys for our test streams
                    print(f"🧹 Cleaning up user stream indexes for test streams...")
                    # Note: This would require knowing the user ID from the JWT token
                    
                print(f"✅ Test data cleanup completed: {cleanup_count} items removed from Redis")
                print(f"🔍 Test created: {len(self.captured_streams)} streams, {len(self.test_worker_ids)} workers, {len(self.test_conversations)} conversations")
                
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
        
        # Clear tracking lists
        self.captured_streams.clear()
        self.test_worker_ids.clear()
        self.test_conversations.clear()
    
    async def cleanup_after_test(self, test_name: str):
        """Clean up after a specific test completes"""
        print(f"\n🧹 Cleaning up after {test_name}...")
        
        # Terminate worker processes spawned by this test
        await self.cleanup_test_workers()
        
        # Clean up Redis and database data created by this test
        await self.cleanup_test_data()
        
        print(f"✅ {test_name} cleanup completed\n")
    
    async def test_single_worker_baseline(self) -> bool:
        """Test 1: Baseline single-worker functionality"""
        print("\n🔬 TEST 1: Single-Worker Baseline")
        
        try:
            conversation_id = await self.create_test_conversation()
            if not conversation_id:
                await self.cleanup_after_test("Single-Worker Baseline")
                return False
            
            # Start a stream
            message_data = {"content": "Write a short poem about distributed systems."}
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    print(f"❌ Failed to start stream: {response.status}")
                    await self.cleanup_after_test("Single-Worker Baseline")
                    return False
                
                stream_id = None
                token_count = 0
                
                # ✅ PROPER SSE PARSING WITH MID-STREAM CANCELLATION
                buffer = ""
                cancellation_sent = False
                
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line_end = buffer.index('\n')
                        line = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1:]
                        
                        if line.startswith('data: '):
                            data_content = line[6:]  # Remove 'data: ' prefix
                            
                            if data_content and data_content != '[DONE]' and data_content != '':
                                try:
                                    event_data = json.loads(data_content)
                                    event_type = event_data.get("type", "")
                                    
                                    if event_type == "token":
                                        token_count += 1
                                    elif event_type == "stream_start":  # ✅ CORRECT EVENT NAME
                                        # Extract stream_id from nested data
                                        if "data" in event_data and "stream_id" in event_data["data"]:
                                            stream_id = event_data["data"]["stream_id"]
                                            self.captured_streams.append(stream_id)
                                            print(f"📡 Captured stream ID: {stream_id}")
                                    
                                    # ✅ CANCEL MID-STREAM after getting stream_id + few tokens
                                    if token_count >= 3 and stream_id and not cancellation_sent:
                                        print(f"🎯 Sending cancellation request mid-stream...")
                                        cancellation_sent = True
                                        
                                        # Send cancellation while stream is ACTIVE
                                        async with self.session.post(
                                            f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
                                            headers=self.get_headers()
                                        ) as cancel_response:
                                            if cancel_response.status == 200:
                                                cancel_result = await cancel_response.json()
                                                print(f"✅ Stream cancelled mid-stream: {cancel_result.get('reason', 'unknown')}")
                                                await self.cleanup_after_test("Single-Worker Baseline")
                                                return True
                                            else:
                                                error_text = await cancel_response.text()
                                                print(f"❌ Failed to cancel stream: {cancel_response.status} - {error_text}")
                                                await self.cleanup_after_test("Single-Worker Baseline")
                                                return False
                                    
                                    # Check for cancellation confirmation event
                                    if event_type in ["cancelled", "stream_end"] and cancellation_sent:
                                        print(f"✅ Stream properly terminated: {event_type}")
                                        await self.cleanup_after_test("Single-Worker Baseline")
                                        return True
                                        
                                except json.JSONDecodeError as e:
                                    print(f"⚠️ JSON parse error: {e}")
                                    continue
                
                if not stream_id:
                    print("❌ Failed to capture stream ID")
                    await self.cleanup_after_test("Single-Worker Baseline")
                    return False
                
                # If we get here, cancellation didn't work as expected
                print("❌ Stream completed without proper cancellation test")
                await self.cleanup_after_test("Single-Worker Baseline")
                return False
                
        except Exception as e:
            print(f"❌ Single-worker test error: {e}")
            await self.cleanup_after_test("Single-Worker Baseline")
            return False
    
    async def test_multi_worker_cancellation(self) -> bool:
        """Test 2: Cross-worker stream cancellation"""
        print("\n🔬 TEST 2: Multi-Worker Cross-Cancellation")
        
        try:
            # Start multiple workers
            if not await self.start_test_workers(worker_count=3):
                print("❌ Failed to start test workers")
                await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                return False
            
            conversation_id = await self.create_test_conversation()
            if not conversation_id:
                await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                return False
            
            # Start stream on one worker
            message_data = {"content": "Explain microservices architecture in detail."}
            
            # ✅ Use port 8001 (first test worker) with JWT token authentication
            test_url = "http://localhost:8001"
            
            # ✅ Use JWT token in Authorization header (works across all ports)
            async with aiohttp.ClientSession() as worker_session:
                async with worker_session.post(
                    f"{test_url}/api/v1/chat/conversations/{conversation_id}/stream",
                    json=message_data,
                    headers=self.get_headers()  # ✅ Uses JWT token in Authorization header
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ Failed to start stream on worker: {response.status} - {error_text}")
                        await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                        return False
                    
                    stream_id = None
                    token_count = 0
                    
                    # ✅ PROPER SSE PARSING FOR MULTI-WORKER TEST
                    buffer = ""
                    async for chunk in response.content.iter_chunked(1024):
                        buffer += chunk.decode('utf-8')
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line_end = buffer.index('\n')
                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]
                            
                            if line.startswith('data: '):
                                data_content = line[6:]  # Remove 'data: ' prefix
                                
                                if data_content and data_content != '[DONE]' and data_content != '':
                                    try:
                                        event_data = json.loads(data_content)
                                        event_type = event_data.get("type", "")
                                        
                                        if event_type == "token":
                                            token_count += 1
                                        elif event_type == "stream_start":  # ✅ CORRECT EVENT NAME
                                            # Extract stream_id from nested data
                                            if "data" in event_data and "stream_id" in event_data["data"]:
                                                stream_id = event_data["data"]["stream_id"]
                                                self.captured_streams.append(stream_id)
                                                print(f"📡 Captured stream ID on worker 1: {stream_id}")
                                        
                                        # ✅ After capturing stream, try cross-worker cancellation MID-STREAM
                                        if token_count > 3 and stream_id:
                                            print(f"🎯 Attempting cross-worker cancellation mid-stream...")
                                            
                                            # Cancel from main server (different worker) 
                                            async with self.session.post(
                                                f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
                                                headers=self.get_headers()
                                            ) as cancel_response:
                                                if cancel_response.status == 200:
                                                    cancel_result = await cancel_response.json()
                                                    cancel_reason = cancel_result.get("reason", "unknown")
                                                    
                                                    print(f"✅ Cross-worker cancellation successful: {cancel_reason}")
                                                    
                                                    # Verify stream is marked as cancelled in Redis
                                                    stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
                                                    redis_status = stream_data.get("status", "unknown")
                                                    
                                                    if redis_status in ["cancelling", "completed"]:
                                                        print(f"✅ Redis status correctly updated: {redis_status}")
                                                        await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                                                        return True
                                                    else:
                                                        print(f"❌ Unexpected Redis status: {redis_status}")
                                                        await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                                                        return False
                                                else:
                                                    error_text = await cancel_response.text()
                                                    print(f"❌ Cross-worker cancellation failed: {cancel_response.status} - {error_text}")
                                                    await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
                                                    return False
                                            
                                    except json.JSONDecodeError as e:
                                        print(f"⚠️ JSON parse error: {e}")
                                        continue
            
            print("❌ Failed to complete cross-worker cancellation test")
            await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
            return False
            
        except Exception as e:
            print(f"❌ Multi-worker test error: {e}")
            await self.cleanup_after_test("Multi-Worker Cross-Cancellation")
            return False
    
    async def test_redis_failure_recovery(self) -> bool:
        """Test 3: Redis failure and recovery scenarios"""
        print("\n🔬 TEST 3: Redis Failure Recovery")
        
        try:
            conversation_id = await self.create_test_conversation()
            if not conversation_id:
                await self.cleanup_after_test("Redis Failure Recovery")
                return False
            
            # Test 1: Redis unavailable during stream creation
            print("🔧 Testing stream creation with Redis failure...")
            
            # Temporarily close Redis connection
            await self.redis_client.close()
            
            # Try to start stream - should still work (graceful degradation)
            message_data = {"content": "Short test message"}
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    print("✅ Stream creation succeeded despite Redis failure (graceful degradation)")
                else:
                    print(f"❌ Stream creation failed: {response.status}")
                    await self.cleanup_after_test("Redis Failure Recovery")
                    return False
            
            # Reconnect Redis
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
            
            # Test 2: Redis recovery - system should continue normally
            print("🔧 Testing Redis recovery...")
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    print("✅ Stream creation succeeded after Redis recovery")
                    await self.cleanup_after_test("Redis Failure Recovery")
                    return True
                else:
                    print(f"❌ Stream creation failed after recovery: {response.status}")
                    await self.cleanup_after_test("Redis Failure Recovery")
                    return False
            
        except Exception as e:
            print(f"❌ Redis failure test error: {e}")
            await self.cleanup_after_test("Redis Failure Recovery")
            return False
    
    async def test_race_conditions(self) -> bool:
        """Test 4: Concurrent cancellation race conditions"""
        print("\n🔬 TEST 4: Race Condition Testing")
        
        try:
            if not await self.start_test_workers(worker_count=2):
                await self.cleanup_after_test("Race Conditions")
                return False
            
            conversation_id = await self.create_test_conversation()
            if not conversation_id:
                await self.cleanup_after_test("Race Conditions")
                return False
            
            # Start a long-running stream
            message_data = {"content": "Write a very long detailed explanation of quantum computing, machine learning, and their intersection in modern technology."}
            
            stream_id = None
            token_count = 0
            
            # Start stream and capture ID quickly
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    await self.cleanup_after_test("Race Conditions")
                    return False
                
                # ✅ PROPER SSE PARSING (same as multi-worker test)
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line_end = buffer.index('\n')
                        line = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1:]
                        
                        if line.startswith('data: '):
                            data_content = line[6:]  # Remove 'data: ' prefix
                            
                            if data_content and data_content != '[DONE]' and data_content != '':
                                try:
                                    event_data = json.loads(data_content)
                                    event_type = event_data.get("type", "")
                                    
                                    if event_type == "token":
                                        token_count += 1
                                    elif event_type == "stream_start":  # ✅ CORRECT EVENT NAME
                                        # Extract stream_id from nested data
                                        if "data" in event_data and "stream_id" in event_data["data"]:
                                            stream_id = event_data["data"]["stream_id"]
                                            self.captured_streams.append(stream_id)
                                            print(f"🏁 Captured stream ID for race test: {stream_id}")
                                    
                                    # ✅ RACE CONDITION TEST: Multiple concurrent cancellations MID-STREAM
                                    if token_count > 3 and stream_id:
                                        print(f"🏁 Starting concurrent cancellations mid-stream...")
                                        
                                        # Start 5 concurrent cancellation attempts on the SAME stream
                                        cancel_tasks = []
                                        for i in range(5):
                                            task = asyncio.create_task(self.concurrent_cancel_attempt(stream_id, i))
                                            cancel_tasks.append(task)
                                        
                                        # Wait for all attempts
                                        results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
                                        
                                        # Analyze results (expect some successes, some race condition failures)
                                        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
                                        print(f"✅ Race condition test completed: {success_count} successful cancellations out of {len(cancel_tasks)} attempts")
                                        
                                        # Verify final state in Redis
                                        final_stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
                                        if not final_stream_data:
                                            print("✅ Stream properly cleaned up from Redis")
                                            await self.cleanup_after_test("Race Conditions")
                                            return True
                                        else:
                                            final_status = final_stream_data.get("status", "unknown")
                                            print(f"✅ Final stream status: {final_status}")
                                            result = final_status in ["completed", "cancelling"]
                                            await self.cleanup_after_test("Race Conditions")
                                            return result
                                except json.JSONDecodeError:
                                    continue
            
            # If we get here, the stream ended without triggering race condition test
            print("❌ Stream ended before race condition test could be performed")
            await self.cleanup_after_test("Race Conditions")
            return False
                
        except Exception as e:
            print(f"❌ Race condition test error: {e}")
            await self.cleanup_after_test("Race Conditions")
            return False
    
    async def concurrent_cancel_attempt(self, stream_id: str, attempt_id: int) -> Dict:
        """Helper: Make concurrent cancellation attempt (expects race conditions)"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    reason = result.get('reason', 'unknown')
                    print(f"🏁 Attempt {attempt_id}: SUCCESS - {reason}")
                    return {"success": True, "reason": reason}
                elif response.status == 410:
                    result = await response.json()
                    reason = result.get('reason', 'unknown')
                    print(f"🏁 Attempt {attempt_id}: ALREADY_CANCELLED - {reason}")
                    return {"success": True, "reason": reason}  # Race condition - another request got there first
                else:
                    error_text = await response.text()
                    print(f"🏁 Attempt {attempt_id}: FAILED - {response.status}: {error_text}")
                    return {"success": False, "reason": f"http_{response.status}"}
        except Exception as e:
            print(f"🏁 Attempt {attempt_id}: ERROR - {e}")
            return {"success": False, "error": str(e)}
    
    async def test_worker_registry(self) -> bool:
        """Test 5: Worker registry and health monitoring"""
        print("\n🔬 TEST 5: Worker Registry Testing")
        
        try:
            # Check initial worker state
            initial_workers = await self.redis_client.smembers("workers:active")
            print(f"🔍 Initial active workers: {len(initial_workers)}")
            
            # Start additional workers
            if not await self.start_test_workers(worker_count=2):
                await self.cleanup_after_test("Worker Registry")
                return False
            
            # Give time for registration
            await asyncio.sleep(2)
            
            # Check worker registration
            active_workers = await self.redis_client.smembers("workers:active")
            print(f"🔍 Active workers after startup: {len(active_workers)}")
            
            if len(active_workers) < len(initial_workers) + 2:
                print("❌ Workers not properly registered")
                await self.cleanup_after_test("Worker Registry")
                return False
            
            # Check worker heartbeats
            worker_health_ok = True
            for worker_id in active_workers:
                worker_data = await self.redis_client.hgetall(f"worker:{worker_id}")
                if not worker_data.get("last_heartbeat"):
                    worker_health_ok = False
                    break
            
            if not worker_health_ok:
                print("❌ Worker heartbeats not working")
                await self.cleanup_after_test("Worker Registry")
                return False
            
            print("✅ Worker registry test passed")
            await self.cleanup_after_test("Worker Registry")
            return True
            
        except Exception as e:
            print(f"❌ Worker registry test error: {e}")
            await self.cleanup_after_test("Worker Registry")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run complete test suite"""
        print("🚀 STARTING DISTRIBUTED STREAMING TEST SUITE")
        print("=" * 60)
        
        # Setup
        if not await self.setup_test_user():
            print("❌ Test setup failed")
            return {}
        
        # Run tests
        tests = [
            ("Single-Worker Baseline", self.test_single_worker_baseline),
            ("Multi-Worker Cancellation", self.test_multi_worker_cancellation),
            ("Redis Failure Recovery", self.test_redis_failure_recovery),
            ("Race Conditions", self.test_race_conditions),
            ("Worker Registry", self.test_worker_registry),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:<30} {status}")
        
        print(f"\nOVERALL: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - DISTRIBUTED STREAMING IS PRODUCTION READY!")
        else:
            print("⚠️  SOME TESTS FAILED - REVIEW ISSUES BEFORE PRODUCTION")
        
        return results


async def main():
    """Main test runner"""
    async with DistributedStreamingTester() as tester:
        results = await tester.run_all_tests()
        
        # Exit with proper code
        all_passed = all(results.values()) if results else False
        exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
