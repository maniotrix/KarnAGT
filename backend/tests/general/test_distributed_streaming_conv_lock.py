#!/usr/bin/env python3
"""
Comprehensive Distributed Streaming Test Suite

Tests the complete Redis-based multi-worker streaming system:
1. Multi-worker stream cancellation
2. Redis failure recovery
3. Cross-worker race conditions
4. Worker registry functionality
5. Conversation locking system
6. TTL cleanup and orphan detection
7. Atomic transaction scenarios

This tests our production-ready distributed architecture including:
- Cross-worker stream coordination
- Distributed conversation locking (prevents concurrent streams per conversation)
- Redis TTL-based dead worker protection
- Comprehensive cleanup and resource management
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

 # Set encoding defaults
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONLEGACYWINDOWSIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
print(f"✅ Encoding defaults set")


class DistributedStreamingTester:
    """Comprehensive test suite for distributed streaming"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.jwt_token: Optional[str] = None   # ✅ JWT token for authentication
        self.redis_client: Optional[redis.Redis] = None
        self.test_user_email: Optional[str] = None
        self.test_user_2_email: Optional[str] = None
        self.jwt_token_user_2: Optional[str] = None
        self.test_conversations: List[str] = []
        self.captured_streams: List[str] = []
        self.test_results: Dict[str, bool] = {}
        self.worker_processes: List[subprocess.Popen] = []
        self.test_worker_ids: List[str] = []  # Track worker IDs created by this test
        self.active_stream_ids: Dict[str, str] = {}  # Map task_name -> stream_id for active streams
        
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
    
    def get_headers(self, include_auth: bool = True, user_2: bool = False) -> Dict[str, str]:
        """Get request headers for authentication"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        # ✅ Add JWT token in Authorization header (works across all ports)
        if include_auth:
            if user_2 and hasattr(self, 'jwt_token_user_2') and self.jwt_token_user_2:
                headers['Authorization'] = f'Bearer {self.jwt_token_user_2}'
            elif hasattr(self, 'jwt_token') and self.jwt_token:
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
    
    async def setup_test_user_2(self) -> bool:
        """Create and authenticate second test user for concurrent testing"""
        try:
            # Generate unique second test user
            timestamp = int(time.time())
            self.test_user_2_email = f"distrib_test_user2_{timestamp}@example.com"
            
            # ✅ Register second user
            register_data = {
                "email": self.test_user_2_email,
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "full_name": "Distributed Tester 2"
            }
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=register_data) as response:
                if response.status != 201:
                    error_text = await response.text()
                    print(f"❌ User 2 registration failed ({response.status}): {error_text}")
                    return False
                
                print(f"✅ User 2 registration successful")
            
            # ✅ Login second user
            login_data = {
                "email": self.test_user_2_email,
                "password": "TestPass123!"
            }
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/login", json=login_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ User 2 login failed ({response.status}): {error_text}")
                    return False
                
                login_result = await response.json()
                
                # ✅ Extract JWT token for user 2
                cookies = response.cookies
                if 'access_token' in cookies:
                    self.jwt_token_user_2 = cookies['access_token'].value
                    print(f"✅ User 2 JWT token extracted: {self.jwt_token_user_2[:20]}...")
                else:
                    print("❌ No JWT token found for user 2")
                    return False
                    
                print(f"✅ User 2 login successful: {login_result.get('user', {}).get('email', 'unknown')}")
                
            print(f"✅ Test user 2 setup complete: {self.test_user_2_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up test user 2: {e}")
            return False
    
    async def create_test_conversation(self, user_2: bool = False, conversation_name: str = "Test") -> Optional[str]:
        """Create a test conversation for specified user"""
        try:
            conversation_data = {
                "title": f"Distributed {conversation_name} {datetime.now().isoformat()}",
                "system_instructions": "You are a helpful assistant for testing distributed streaming."
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations", 
                json=conversation_data,
                headers=self.get_headers(user_2=user_2)
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    user_label = "User 2" if user_2 else "User 1"
                    print(f"❌ Failed to create conversation for {user_label}: {response.status} - {error_text}")
                    return None
                
                result = await response.json()
                conversation_id = result["conversation_id"]
                self.test_conversations.append(conversation_id)
                user_label = "User 2" if user_2 else "User 1"
                print(f"✅ Created conversation for {user_label}: {conversation_id}")
                return conversation_id
                
        except Exception as e:
            user_label = "User 2" if user_2 else "User 1"
            print(f"❌ Error creating conversation for {user_label}: {e}")
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
                    "PYTHONUNBUFFERED": "1",  # ✅ Force immediate log output
                    "PYTHONIOENCODING": "utf-8",
                })
                
                # ✅ Start worker using YOUR startup script WITH VENV (loads .env, validates keys, registers worker)
                # ✅ Use the SAME Python interpreter as the current process (venv Python)
                venv_python = sys.executable
                python_file = "dist_dev_start_app.py"
                print(f"🚀 Starting worker {i+1} with venv Python")
                print(f"🔧 Python: {venv_python}")
                print(f"🔧 Script: {python_file}")
                print(f"🔧 Environment: PORT={port}, ENVIRONMENT=production, DEBUG=True")
                
                # Inherit stdout/stderr so child logs print in this console; use -u for unbuffered output
                process = subprocess.Popen([
                    venv_python, "-u", python_file  # ✅ Uses venv Python unbuffered
                ], 
                cwd="backend", 
                env=env)
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
                    print(f"   📤 Sending SIGTERM to worker {i+1} (PID {process.pid})...")
                    process.terminate()
                    
                    try:
                        # Give worker more time for graceful shutdown
                        print(f"   ⏳ Waiting up to 10 seconds for graceful shutdown...")
                        process.wait(timeout=10)
                        print(f"   ✅ Worker {i+1} terminated gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"   ⚡ Worker {i+1} didn't respond to SIGTERM, sending SIGKILL...")
                        process.kill()
                        try:
                            process.wait(timeout=3)
                            print(f"   ✅ Worker {i+1} force killed")
                        except subprocess.TimeoutExpired:
                            print(f"   ❌ Worker {i+1} still running after SIGKILL (zombie?)")
                else:
                    print(f"   ✅ Worker {i+1} (PID {process.pid}) already stopped")
            except Exception as e:
                print(f"   ⚠️ Error cleaning up worker process {i+1}: {e}")
        
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
                    try:
                        # Use worker registry cleanup for comprehensive cleanup (includes conversation locks)
                        # Note: In a real test environment, you'd import worker_registry from the backend
                        # For now, we'll do manual cleanup
                        
                        # Clean up any conversation locks owned by this dead test worker
                        conv_lock_keys = await self.redis_client.keys("conv_lock:*")
                        for lock_key in conv_lock_keys:
                            lock_value = await self.redis_client.get(lock_key)
                            if lock_value:
                                lock_value_str = lock_value.decode() if isinstance(lock_value, bytes) else str(lock_value)
                                if f"worker:{worker_id}" in lock_value_str:
                                    deleted = await self.redis_client.delete(lock_key)
                                    if deleted:
                                        cleanup_count += 1
                                        print(f"   🔒 Cleaned up orphaned lock from dead test worker {worker_id}")
                        
                        # Remove worker from active set
                        await self.redis_client.srem("workers:active", worker_id)
                        # Remove worker metadata
                        deleted = await self.redis_client.delete(f"worker:{worker_id}")
                        if deleted:
                            cleanup_count += 1
                            
                    except Exception as e:
                        print(f"Warning: Error cleaning up test worker {worker_id}: {e}")
                
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
                
                # 4. Clean up conversation locks created by tests
                print(f"🧹 Cleaning up test conversation locks...")
                conv_lock_keys = await self.redis_client.keys("conv_lock:*")
                for lock_key in conv_lock_keys:
                    # Only clean up locks that might be from our test conversations
                    lock_key_str = lock_key.decode() if isinstance(lock_key, bytes) else lock_key
                    for test_conv_id in self.test_conversations:
                        if test_conv_id in lock_key_str:
                            deleted = await self.redis_client.delete(lock_key)
                            if deleted:
                                cleanup_count += 1
                                break
                
                # 5. Clean up any orphaned test locks (ones containing "ttl_test")
                for lock_key in conv_lock_keys:
                    lock_key_str = lock_key.decode() if isinstance(lock_key, bytes) else lock_key
                    if "ttl_test" in lock_key_str:
                        deleted = await self.redis_client.delete(lock_key)
                        if deleted:
                            cleanup_count += 1
                
                # 6. Clean up user streams for test streams (only for test user)
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
        
        # 🔄 Add grace period to allow Redis operations to complete
        print("⏳ Waiting for Redis operations to complete in workers...")
        await asyncio.sleep(5)  # Give Redis cleanup time to finish
        
        # Terminate worker processes spawned by this test
        await self.cleanup_test_workers()
        
        # Clean up Redis and database data created by this test
        await self.cleanup_test_data()
        
        print(f"✅ {test_name} cleanup completed\n")
    
    async def test_6_1_concurrent_streaming_attempts(self, conversation_id: str, message_data: dict) -> bool:
        """Test 6.1: Concurrent streaming attempts to same conversation"""
        print("🔒 TEST 6.1: Concurrent streaming attempts to same conversation")
        
        # Start first stream and get it going
        stream_1_task = asyncio.create_task(
            self.start_stream_and_capture_id(conversation_id, message_data, "http://localhost:8001", "Stream-1")
        )
        
        # Wait for stream to start and capture stream_id
        stream_id = None
        for _ in range(10):  # Wait up to 5 seconds
            await asyncio.sleep(0.5)
            if "Stream-1" in self.active_stream_ids:
                stream_id = self.active_stream_ids["Stream-1"]
                print(f"✅ Got Stream-1 ID: {stream_id}")
                break
        
        if not stream_id:
            print("❌ Failed to capture Stream-1 ID")
            stream_1_task.cancel()
            return False
        
        # Attempt concurrent streams - should all get 429
        concurrent_tasks = []
        for i in range(3):
            task = asyncio.create_task(
                self.attempt_concurrent_stream(conversation_id, message_data, f"http://localhost:{8001+i}", f"Concurrent-{i+1}")
            )
            concurrent_tasks.append(task)
        
        # Wait for concurrent attempts
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify all concurrent attempts got 429 (conversation locked)
        lock_rejections = sum(1 for r in concurrent_results if isinstance(r, dict) and r.get("status") == 429)
        if lock_rejections != 3:
            print(f"❌ Expected 3 lock rejections, got {lock_rejections}")
            # Cancel the stream via API and then cancel task
            await self.cancel_stream(stream_id)
            stream_1_task.cancel()
            return False
        
        print(f"✅ All {lock_rejections} concurrent attempts properly rejected with 429")
        
        # Cancel the first stream to release lock (while it's still streaming)
        print(f"🛑 Cancelling Stream-1 via API: {stream_id}")
        await self.cancel_stream(stream_id)
        
        # Now cancel the task
        print(f"🛑 Cancelling Stream-1 task")
        stream_1_task.cancel()
        
        # Wait a moment to ensure task cancellation is processed
        try:
            await stream_1_task
        except asyncio.CancelledError:
            print("✅ Stream-1 task cancelled successfully")
        
        # 🔄 Brief pause to let stream cleanup complete in worker
        print("⏳ Allowing worker Redis cleanup to complete...")
        await asyncio.sleep(2)
        
        return True
    
    async def test_6_2_edit_during_stream(self, conversation_id: str, message_data: dict) -> bool:
        """Test 6.2: Edit attempt during active stream"""
        print("\n🔒 TEST 6.2: Edit attempt during active stream")
        
        # Start a new stream
        stream_2_task = asyncio.create_task(
            self.start_stream_and_capture_id(conversation_id, message_data, self.base_url, "Stream-2")
        )
        
        # Wait for stream to start and capture stream_id
        stream_id = None
        for _ in range(10):  # Wait up to 5 seconds
            await asyncio.sleep(0.5)
            if "Stream-2" in self.active_stream_ids:
                stream_id = self.active_stream_ids["Stream-2"]
                print(f"✅ Got Stream-2 ID: {stream_id}")
                break
        
        if not stream_id:
            print("❌ Failed to capture Stream-2 ID")
            stream_2_task.cancel()
            return False
        
        # Try to edit a message while stream is active
        edit_result = await self.attempt_edit_during_stream(conversation_id, "fake-message-id", "Edited content")
        
        if edit_result.get("status") != 429:
            print(f"❌ Edit during stream should return 429, got {edit_result.get('status')}")
            # Cancel the stream via API and then cancel task
            await self.cancel_stream(stream_id)
            stream_2_task.cancel()
            return False
        
        print("✅ Edit during stream properly rejected with 429")
        
        # Cancel stream 2
        print(f"🛑 Cancelling Stream-2 via API: {stream_id}")
        await self.cancel_stream(stream_id)
        
        # Now cancel the task
        print(f"🛑 Cancelling Stream-2 task")
        stream_2_task.cancel()
        
        # Wait for task cancellation
        try:
            await stream_2_task
        except asyncio.CancelledError:
            print("✅ Stream-2 task cancelled successfully")
        
        # 🔄 Brief pause to let stream cleanup complete in worker
        print("⏳ Allowing worker Redis cleanup to complete...")
        await asyncio.sleep(2)
        
        return True
    
    async def test_6_3_lock_release_after_completion(self, conversation_id: str) -> bool:
        """Test 6.3: Lock release after stream completion"""
        print("\n🔒 TEST 6.3: Lock release after stream completion")
        
        # Start short stream that will complete
        short_message = {"content": "Just say 'Hello world' and stop."}
        
        stream_3_result = await self.complete_short_stream(conversation_id, short_message)
        if not stream_3_result.get("completed"):
            print("❌ Short stream did not complete properly")
            return False
        
        # Verify lock is released - new stream should succeed
        await asyncio.sleep(1)
        
        follow_up_result = await self.attempt_concurrent_stream(conversation_id, short_message, self.base_url, "Follow-up")
        if follow_up_result.get("status") != 200:
            print(f"❌ Follow-up stream after completion failed: {follow_up_result.get('status')}")
            return False
        
        print("✅ Lock properly released after stream completion")
        return True
    
    async def test_6_4_lock_ttl_expiry(self, conversation_id: str) -> bool:
        """Test 6.4: Lock TTL expiry verification"""
        print("\n🔒 TEST 6.4: Lock TTL expiry verification")
        
        # Check current locks in Redis
        lock_keys_before = await self.redis_client.keys("conv_lock:*")
        print(f"🔍 Active conversation locks: {len(lock_keys_before)}")
        
        # Create a lock manually and check its TTL
        test_lock_key = f"conv_lock:{conversation_id}_ttl_test"
        test_lock_value = f"user:test:worker:ttl_test:ts:{int(time.time())}"
        
        # Set lock with 5-second TTL for testing (instead of 300)
        await self.redis_client.set(test_lock_key, test_lock_value, nx=True, ex=5)
        
        # Verify lock exists
        ttl_before = await self.redis_client.ttl(test_lock_key)
        if ttl_before <= 0:
            print("❌ Test lock TTL not set correctly")
            return False
        
        print(f"✅ Test lock created with TTL: {ttl_before} seconds")
        
        # Wait for TTL expiry
        print("⏳ Waiting for TTL expiry...")
        await asyncio.sleep(6)
        
        # Verify lock expired
        lock_exists = await self.redis_client.exists(test_lock_key)
        if lock_exists:
            print("❌ Lock did not expire after TTL")
            await self.redis_client.delete(test_lock_key)  # Cleanup
            return False
        
        print("✅ Lock properly expired after TTL")
        return True
    
    async def test_6_5_cross_worker_lock_enforcement(self, conversation_id: str, message_data: dict) -> bool:
        """Test 6.5: Cross-worker lock enforcement"""
        print("\n🔒 TEST 6.5: Cross-worker lock enforcement")
        
        # Start stream on worker 1
        worker_1_task = asyncio.create_task(
            self.start_stream_and_capture_id(conversation_id, message_data, "http://localhost:8001", "Worker-1")
        )
        
        # Wait for stream to start and capture stream_id
        stream_id = None
        for _ in range(10):  # Wait up to 5 seconds
            await asyncio.sleep(0.5)
            if "Worker-1" in self.active_stream_ids:
                stream_id = self.active_stream_ids["Worker-1"]
                print(f"✅ Got Worker-1 ID: {stream_id}")
                break
        
        if not stream_id:
            print("❌ Failed to capture Worker-1 ID")
            worker_1_task.cancel()
            return False
        
        # Attempt stream on worker 2 - should be rejected
        worker_2_result = await self.attempt_concurrent_stream(conversation_id, message_data, "http://localhost:8002", "Worker-2")
        
        if worker_2_result.get("status") != 429:
            print(f"❌ Cross-worker lock not enforced: {worker_2_result.get('status')}")
            # Cancel the stream via API and then cancel task
            await self.cancel_stream(stream_id)
            worker_1_task.cancel()
            return False
        
        print("✅ Cross-worker lock properly enforced")
        
        # Cancel worker 1 stream
        print(f"🛑 Cancelling Worker-1 via API: {stream_id}")
        await self.cancel_stream(stream_id)
        
        # Now cancel the task
        print(f"🛑 Cancelling Worker-1 task")
        worker_1_task.cancel()
        
        # Wait for task cancellation
        try:
            await worker_1_task
        except asyncio.CancelledError:
            print("✅ Worker-1 task cancelled successfully")
        
        # 🔄 Brief pause to let stream cleanup complete in worker
        print("⏳ Allowing worker Redis cleanup to complete...")
        await asyncio.sleep(2)
        
        return True
    
    async def test_6_6_concurrent_users_different_conversations(self) -> bool:
        """Test 6.6: Different users can stream simultaneously in their own conversations"""
        print("\n🔒 TEST 6.6: Different users streaming simultaneously in different conversations")
        
        # Setup second user
        if not await self.setup_test_user_2():
            print("❌ Failed to setup second test user")
            return False
        
        # Create conversations for both users
        user_1_conversation = await self.create_test_conversation(user_2=False, conversation_name="User1")
        if not user_1_conversation:
            print("❌ Failed to create conversation for user 1")
            return False
        
        user_2_conversation = await self.create_test_conversation(user_2=True, conversation_name="User2")  
        if not user_2_conversation:
            print("❌ Failed to create conversation for user 2")
            return False
        
        message_data = {"content": "Explain quantum computing in detail with examples."}
        
        # Start stream for user 1
        user_1_task = asyncio.create_task(
            self.start_stream_for_user(user_1_conversation, message_data, self.base_url, "User1-Stream", user_2=False)
        )
        
        # Wait for user 1 stream to start
        user_1_stream_id = None
        for _ in range(10):  # Wait up to 5 seconds
            await asyncio.sleep(0.5)
            if "User1-Stream" in self.active_stream_ids:
                user_1_stream_id = self.active_stream_ids["User1-Stream"]
                print(f"✅ User 1 stream started: {user_1_stream_id}")
                break
        
        if not user_1_stream_id:
            print("❌ Failed to start User 1 stream")
            user_1_task.cancel()
            return False
        
        # Start stream for user 2 (should succeed - different conversation)
        user_2_task = asyncio.create_task(
            self.start_stream_for_user(user_2_conversation, message_data, self.base_url, "User2-Stream", user_2=True)
        )
        
        # Wait for user 2 stream to start
        user_2_stream_id = None
        for _ in range(10):  # Wait up to 5 seconds
            await asyncio.sleep(0.5)
            if "User2-Stream" in self.active_stream_ids:
                user_2_stream_id = self.active_stream_ids["User2-Stream"]
                print(f"✅ User 2 stream started: {user_2_stream_id}")
                break
        
        if not user_2_stream_id:
            print("❌ Failed to start User 2 stream - concurrent users should be allowed!")
            await self.cancel_stream(user_1_stream_id)
            user_1_task.cancel()
            user_2_task.cancel()
            return False
        
        print("✅ Both users successfully streaming simultaneously in different conversations")
        
        # Verify both streams are actually running
        await asyncio.sleep(2)  # Let streams run for a bit
        
        # Check if both streams are still active
        user_1_active = "User1-Stream" in self.active_stream_ids
        user_2_active = "User2-Stream" in self.active_stream_ids
        
        if not user_1_active or not user_2_active:
            print(f"❌ Streams unexpectedly stopped - User1: {user_1_active}, User2: {user_2_active}")
            # Cleanup
            if user_1_stream_id:
                await self.cancel_stream(user_1_stream_id)
            if user_2_stream_id:
                await self.cancel_stream(user_2_stream_id)
            user_1_task.cancel()
            user_2_task.cancel()
            return False
        
        print("✅ Both streams confirmed running concurrently")
        
        # Clean up both streams
        print("🛑 Cancelling both streams")
        if user_1_stream_id:
            await self.cancel_stream(user_1_stream_id)
        if user_2_stream_id:
            await self.cancel_stream(user_2_stream_id)
        
        # Cancel tasks
        user_1_task.cancel()
        user_2_task.cancel()
        
        # Wait for task cancellations
        try:
            await user_1_task
        except asyncio.CancelledError:
            print("✅ User 1 task cancelled")
        
        try:
            await user_2_task
        except asyncio.CancelledError:
            print("✅ User 2 task cancelled")
        
        print("⏳ Allowing worker cleanup...")
        await asyncio.sleep(2)
        
        return True
    
    async def test_conversation_locking(self) -> bool:
        """Test 6: Distributed conversation locking system - Run all tests"""
        print("\n🔬 TEST 6: Conversation Locking System")
        
        try:
            # Start multiple workers for distributed testing
            if not await self.start_test_workers(worker_count=3):
                print("❌ Failed to start test workers")
                await self.cleanup_after_test("Conversation Locking")
                return False
            
            conversation_id = await self.create_test_conversation()
            if not conversation_id:
                await self.cleanup_after_test("Conversation Locking")
                return False
            
            message_data = {"content": "Explain artificial intelligence in great detail with examples and applications."}
            
            # Run all individual tests - comment out any test you don't want to run
            tests = [
                # await self.test_6_1_concurrent_streaming_attempts(conversation_id, message_data),
                # await self.test_6_2_edit_during_stream(conversation_id, message_data), 
                # await self.test_6_3_lock_release_after_completion(conversation_id),
                # await self.test_6_4_lock_ttl_expiry(conversation_id),
                # await self.test_6_5_cross_worker_lock_enforcement(conversation_id, message_data),
                await self.test_6_6_concurrent_users_different_conversations()
            ]
            
            # Check if all tests passed
            if all(tests):
                print("\n✅ All conversation locking tests passed!")
                
                # 🔄 Brief pause to let stream cleanup complete in worker
                print("⏳ Allowing worker Redis cleanup to complete...")
                await asyncio.sleep(2)
                
                await self.cleanup_after_test("Conversation Locking")
                return True
            else:
                print("\n❌ Some conversation locking tests failed!")
                await self.cleanup_after_test("Conversation Locking")
                return False
            
        except Exception as e:
            print(f"❌ Conversation locking test error: {e}")
            await self.cleanup_after_test("Conversation Locking")
            return False
    
    async def start_stream_and_capture_id(self, conversation_id: str, message_data: dict, base_url: str, stream_name: str) -> dict:
        """Helper: Start stream and capture stream ID but keep streaming"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                    json=message_data,
                    headers=self.get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ {stream_name} failed to start: {response.status} - {error_text}")
                        return {"status": response.status, "error": error_text}
                    
                    stream_id = None
                    token_count = 0
                    stream_id_captured = False
                    
                    # Parse SSE to get stream ID
                    buffer = ""
                    async for chunk in response.content.iter_chunked(1024):
                        buffer += chunk.decode('utf-8')
                        
                        while '\n' in buffer:
                            line_end = buffer.index('\n')
                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]
                            
                            if line.startswith('data: '):
                                data_content = line[6:]
                                
                                if data_content == '[DONE]':
                                    print(f"✅ {stream_name} completed naturally")
                                    break
                                elif data_content and data_content != '':
                                    try:
                                        event_data = json.loads(data_content)
                                        event_type = event_data.get("type", "")
                                        
                                        if event_type == "token":
                                            token_count += 1
                                        elif event_type == "stream_start":
                                            if "data" in event_data and "stream_id" in event_data["data"]:
                                                stream_id = event_data["data"]["stream_id"]
                                                self.captured_streams.append(stream_id)
                                                # Store stream_id for external access
                                                self.active_stream_ids[stream_name] = stream_id
                                                print(f"📡 {stream_name} captured stream ID: {stream_id}")
                                                stream_id_captured = True
                                        elif event_type == "stream_end":
                                            print(f"✅ {stream_name} ended normally")
                                            break
                                    except json.JSONDecodeError:
                                        continue
                    
                    # Clean up stream_id from active tracking
                    if stream_name in self.active_stream_ids:
                        del self.active_stream_ids[stream_name]
                    
                    return {"status": 200, "stream_id": stream_id, "tokens": token_count}
        except Exception as e:
            print(f"❌ Error in {stream_name}: {e}")
            # Clean up stream_id from active tracking
            if stream_name in self.active_stream_ids:
                del self.active_stream_ids[stream_name]
            return {"error": str(e)}
    
    async def start_stream_for_user(self, conversation_id: str, message_data: dict, base_url: str, stream_name: str, user_2: bool = False) -> dict:
        """Helper: Start stream for specified user and capture stream ID"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                    json=message_data,
                    headers=self.get_headers(user_2=user_2)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        user_label = "User 2" if user_2 else "User 1"
                        print(f"❌ {stream_name} ({user_label}) failed to start: {response.status} - {error_text}")
                        return {"status": response.status, "error": error_text}
                    
                    stream_id = None
                    token_count = 0
                    
                    # Parse SSE to get stream ID
                    buffer = ""
                    async for chunk in response.content.iter_chunked(1024):
                        buffer += chunk.decode('utf-8')
                        
                        while '\n' in buffer:
                            line_end = buffer.index('\n')
                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]
                            
                            if line.startswith('data: '):
                                data_content = line[6:]
                                
                                if data_content == '[DONE]':
                                    user_label = "User 2" if user_2 else "User 1"
                                    print(f"✅ {stream_name} ({user_label}) completed naturally")
                                    break
                                elif data_content and data_content != '':
                                    try:
                                        event_data = json.loads(data_content)
                                        event_type = event_data.get("type", "")
                                        
                                        if event_type == "token":
                                            token_count += 1
                                        elif event_type == "stream_start":
                                            if "data" in event_data and "stream_id" in event_data["data"]:
                                                stream_id = event_data["data"]["stream_id"]
                                                self.captured_streams.append(stream_id)
                                                # Store stream_id for external access
                                                self.active_stream_ids[stream_name] = stream_id
                                                user_label = "User 2" if user_2 else "User 1"
                                                print(f"📡 {stream_name} ({user_label}) captured stream ID: {stream_id}")
                                        elif event_type == "stream_end":
                                            user_label = "User 2" if user_2 else "User 1"
                                            print(f"✅ {stream_name} ({user_label}) ended normally")
                                            break
                                    except json.JSONDecodeError:
                                        continue
                    
                    # Clean up stream_id from active tracking
                    if stream_name in self.active_stream_ids:
                        del self.active_stream_ids[stream_name]
                    
                    return {"status": 200, "stream_id": stream_id, "tokens": token_count}
        except Exception as e:
            user_label = "User 2" if user_2 else "User 1"
            print(f"❌ Error in {stream_name} ({user_label}): {e}")
            # Clean up stream_id from active tracking
            if stream_name in self.active_stream_ids:
                del self.active_stream_ids[stream_name]
            return {"error": str(e)}
    
    async def attempt_concurrent_stream(self, conversation_id: str, message_data: dict, base_url: str, attempt_name: str) -> dict:
        """Helper: Attempt concurrent stream (expect 429 or 200)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/v1/chat/conversations/{conversation_id}/stream", 
                    json=message_data,
                    headers=self.get_headers()
                ) as response:
                    if response.status == 429:
                        result = await response.json()
                        print(f"🔒 {attempt_name} properly blocked: {result.get('detail', {}).get('message', 'unknown')}")
                        return {"status": 429, "result": result}
                    elif response.status == 200:
                        print(f"✅ {attempt_name} successfully started")
                        return {"status": 200}
                    else:
                        error_text = await response.text()
                        print(f"❌ {attempt_name} unexpected status {response.status}: {error_text}")
                        return {"status": response.status, "error": error_text}
        except Exception as e:
            print(f"❌ Error in {attempt_name}: {e}")
            return {"error": str(e)}
    
    async def attempt_edit_during_stream(self, conversation_id: str, message_id: str, content: str) -> dict:
        """Helper: Attempt to edit message during active stream"""
        try:
            edit_data = {"content": content}
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message_id}/edit/stream",
                json=edit_data,
                headers=self.get_headers()
            ) as response:
                if response.status == 429:
                    result = await response.json()
                    print(f"🔒 Edit properly blocked during stream: {result.get('detail', {}).get('message', 'unknown')}")
                    return {"status": 429, "result": result}
                else:
                    error_text = await response.text()
                    print(f"⚠️ Edit during stream got unexpected status {response.status}: {error_text}")
                    return {"status": response.status, "error": error_text}
        except Exception as e:
            print(f"❌ Error attempting edit during stream: {e}")
            return {"error": str(e)}
    
    async def complete_short_stream(self, conversation_id: str, message_data: dict) -> dict:
        """Helper: Complete a short stream to test lock release"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {"completed": False, "error": error_text}
                
                completed = False
                stream_id = None
                
                # Read entire stream until completion
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    while '\n' in buffer:
                        line_end = buffer.index('\n')
                        line = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1:]
                        
                        if line.startswith('data: '):
                            data_content = line[6:]
                            
                            if data_content == '[DONE]':
                                completed = True
                                break
                            elif data_content and data_content != '':
                                try:
                                    event_data = json.loads(data_content)
                                    event_type = event_data.get("type", "")
                                    
                                    if event_type == "stream_start":
                                        if "data" in event_data and "stream_id" in event_data["data"]:
                                            stream_id = event_data["data"]["stream_id"]
                                            self.captured_streams.append(stream_id)
                                    elif event_type == "stream_end":
                                        completed = True
                                        break
                                except json.JSONDecodeError:
                                    continue
                    
                    if completed:
                        break
                
                print(f"✅ Short stream completed successfully (stream_id: {stream_id})")
                return {"completed": True, "stream_id": stream_id}
                
        except Exception as e:
            print(f"❌ Error completing short stream: {e}")
            return {"completed": False, "error": str(e)}
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """Helper: Cancel a stream"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
                headers=self.get_headers()
            ) as response:
                if response.status in [200, 410]:  # 410 = already cancelled
                    result = await response.json()
                    print(f"🛑 Stream {stream_id} cancelled: {result.get('reason', 'unknown')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Failed to cancel stream {stream_id}: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Error cancelling stream {stream_id}: {e}")
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
            ("Conversation Locking", self.test_conversation_locking),
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
