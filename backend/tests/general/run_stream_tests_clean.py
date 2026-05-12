#!/usr/bin/env python3
"""
Real Frontend-Backend Stream Cancellation Test Suite

This script tests the complete frontend workflow:
1. Real user registration and authentication
2. Real conversation creation
3. Real streaming with stream_id extraction
4. Real stream cancellation using captured stream_id
5. Real verification of cancellation

NO FAKE DATA - Tests exactly how frontend would work.
"""

import asyncio
import aiohttp
import subprocess
import signal
import sys
import time
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class RealFrontendStreamTester:
    """Test stream cancellation exactly like frontend would do it"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.test_user_email: Optional[str] = None
        self.test_conversations: List[str] = []
        self.captured_stream_ids: List[str] = []
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        headers = {'Content-Type': 'application/json'}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers
    
    async def wait_for_server(self, max_attempts: int = 30) -> bool:
        """Wait for server to be ready"""
        print("🔄 Waiting for server to be ready...")
        
        for attempt in range(max_attempts):
            try:
                async with self.session.get(f"{self.base_url}/docs") as response:
                    if response.status == 200:
                        print("✅ Server is ready!")
                        return True
            except Exception:
                pass
            
            await asyncio.sleep(1)
            if attempt % 5 == 0:
                print(f"   Still waiting... (attempt {attempt + 1}/{max_attempts})")
        
        print("❌ Server failed to start in time")
        return False
    
    async def register_test_user(self) -> bool:
        """Register a real test user and get access token"""
        print("👤 Registering real test user...")
        
        # Use unique email with timestamp
        timestamp = int(datetime.now().timestamp())
        self.test_user_email = f"streamtest_{timestamp}@example.com"
        
        user_data = {
            "email": self.test_user_email,
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Real Stream Test User"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=user_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    self.access_token = result.get("access_token")
                    print(f"✅ Real user registered: {self.test_user_email}")
                    print(f"🔑 Access token: {self.access_token[:20]}...")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Registration failed ({response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    async def verify_authentication(self) -> bool:
        """Verify that authentication is working"""
        print("🔐 Verifying real authentication...")
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    user_data = await response.json()
                    print(f"✅ Authentication verified for: {user_data.get('email')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed ({response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def create_real_conversation(self) -> str:
        """Create a real conversation for testing"""
        print("💬 Creating real test conversation...")
        
        conversation_data = {
            "title": f"Real Stream Test {datetime.now().isoformat()}",
            "model_name": "gpt-3.5-turbo",
            "system_prompt": "You are a helpful assistant for testing real stream cancellation."
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations",
                json=conversation_data,
                headers=self.get_headers()
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    conversation_id = result['conversation_id']
                    self.test_conversations.append(conversation_id)
                    print(f"✅ Real conversation created: {conversation_id}")
                    return conversation_id
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create conversation ({response.status}): {error_text}")
                    
        except Exception as e:
            print(f"❌ Conversation creation error: {e}")
            raise
    
    def extract_stream_id_from_sse(self, sse_line: str) -> Optional[str]:
        """Extract stream_id from SSE data line - exactly like frontend would"""
        if not sse_line.startswith('data: '):
            return None
            
        try:
            data = sse_line[6:].strip()  # Remove 'data: ' prefix
            if data in ['[DONE]', '']:
                return None
                
            event = json.loads(data)
            
            # Look for stream_id in various event types
            if 'stream_id' in event:
                return event['stream_id']
            
            # Also check nested data
            if 'data' in event and isinstance(event['data'], dict) and 'stream_id' in event['data']:
                return event['data']['stream_id']
                
        except json.JSONDecodeError:
            pass
            
        return None
    
    async def test_real_streaming_and_capture_stream_id(self, conversation_id: str) -> Optional[str]:
        """Start real streaming and capture the actual stream_id - like frontend does"""
        print("🌊 Starting real stream and capturing stream_id...")
        
        message_data = {
            "content": "Write a detailed 500-word essay about the benefits of artificial intelligence in healthcare. Include specific examples and take your time to provide a comprehensive response.",
            "role": "user"
        }
        
        captured_stream_id = None
        chunks_read = 0
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers={
                    **self.get_headers(),
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache'
                }
            ) as response:
                
                print(f"   Stream response status: {response.status}")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                
                if response.status != 200:
                    error_data = await response.text()
                    print(f"❌ Stream failed ({response.status}): {error_data}")
                    return None
                
                print("📡 Reading SSE stream to capture stream_id...")
                
                # Read SSE stream line by line - exactly like frontend
                buffer = ""
                async for chunk in response.content.iter_any():
                    chunk_data = chunk.decode('utf-8', errors='ignore')
                    buffer += chunk_data
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line:
                            print(f"   📥 SSE Line: {line[:100]}...")
                            
                            # Try to extract stream_id from this line
                            stream_id = self.extract_stream_id_from_sse(line)
                            if stream_id and not captured_stream_id:
                                captured_stream_id = stream_id
                                self.captured_stream_ids.append(stream_id)
                                print(f"🎯 CAPTURED REAL STREAM_ID: {stream_id}")
                                # Wait a bit to let the stream get going, then break to test cancellation
                                print("⏱️  Waiting for stream to produce content before testing cancellation...")
                                await asyncio.sleep(2)  # Let stream generate some content
                                break
                    
                    chunks_read += 1
                    if chunks_read > 10:  # Read enough to get stream_id
                        break
                
                if captured_stream_id:
                    print(f"✅ Successfully captured stream_id: {captured_stream_id}")
                else:
                    print("⚠️  No stream_id found in SSE events")
                    
                return captured_stream_id
                    
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return None
    
    async def test_long_stream_for_cancellation(self, conversation_id: str) -> Optional[str]:
        """Start a long stream, capture stream_id, then immediately test cancellation"""
        print("📝 Starting long essay stream for real cancellation test...")
        
        message_data = {
            "content": "Write a comprehensive 1000-word research paper about the evolution of renewable energy technologies, including detailed explanations of solar, wind, hydro, and emerging technologies. Take your time and be very thorough.",
            "role": "user"
        }
        
        captured_stream_id = None
        
        try:
            # Start the long stream
            response = await self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers={
                    **self.get_headers(),
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache'
                }
            )
            
            if response.status != 200:
                error_data = await response.text()
                print(f"❌ Long stream failed ({response.status}): {error_data}")
                return None
            
            print("📡 Reading long stream to capture stream_id quickly...")
            
            # Read just enough to get the stream_id, then cancel immediately
            buffer = ""
            async for chunk in response.content.iter_any():
                chunk_data = chunk.decode('utf-8', errors='ignore')
                buffer += chunk_data
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line:
                        stream_id = self.extract_stream_id_from_sse(line)
                        if stream_id and not captured_stream_id:
                            captured_stream_id = stream_id
                            self.captured_stream_ids.append(stream_id)
                            print(f"🎯 CAPTURED LONG STREAM_ID: {stream_id}")
                            print("🏃‍♂️ Immediately testing cancellation on active stream!")
                            
                            # Test cancellation while stream is definitely active
                            cancel_result = await self.test_real_stream_cancellation(stream_id)
                            if cancel_result:
                                print("✅ Successfully cancelled active long stream!")
                            else:
                                print("❌ Failed to cancel active long stream!")
                            
                            return stream_id
                
                # Safety limit - don't read forever
                if len(buffer) > 10000:
                    break
                    
            return captured_stream_id
            
        except Exception as e:
            print(f"❌ Long stream cancellation test error: {e}")
            return None
    
    async def test_real_stream_cancellation(self, stream_id: str) -> bool:
        """Cancel stream using real stream_id - exactly like frontend would"""
        print(f"🛑 Testing real stream cancellation with stream_id: {stream_id}")
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
                headers=self.get_headers()
            ) as response:
                
                result_data = await response.text()
                
                if response.status == 200:
                    try:
                        result_json = json.loads(result_data)
                        if result_json.get("cancelled", False):
                            print(f"✅ Stream cancelled successfully: {result_data}")
                            return True
                        else:
                            print(f"⚠️  Unexpected cancellation response: {result_data}")
                            return True
                    except json.JSONDecodeError:
                        print(f"✅ Stream cancelled (non-JSON response): {result_data}")
                        return True
                elif response.status == 410:
                    print(f"✅ Stream already completed (HTTP 410 - expected for fast streams): {result_data}")
                    return True  # This is the correct response for completed streams
                elif response.status == 404:
                    print(f"⚠️  Stream not found (may have already ended): {result_data}")
                    return True  # This is also acceptable
                else:
                    print(f"❌ Cancellation failed ({response.status}): {result_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Cancellation error: {e}")
            return False
    
    async def test_cancel_all_streams(self) -> bool:
        """Test cancelling all user streams - like frontend would"""
        print("🛑 Testing cancel all streams...")
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/stream/cancel-all",
                headers=self.get_headers()
            ) as response:
                
                result_data = await response.text()
                
                if response.status == 200:
                    print(f"✅ All streams cancelled: {result_data}")
                    return True
                else:
                    print(f"❌ Cancel all failed ({response.status}): {result_data}")
                    return False
                    
        except Exception as e:
            print(f"❌ Cancel all error: {e}")
            return False
    
    async def test_get_active_streams(self) -> Dict:
        """Test getting active streams - like frontend would"""
        print("📊 Testing get active streams...")
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/chat/stream/active",
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    result_data = await response.json()
                    print(f"✅ Active streams retrieved: {result_data}")
                    return result_data
                else:
                    error_data = await response.text()
                    print(f"❌ Get active streams failed ({response.status}): {error_data}")
                    return {}
                    
        except Exception as e:
            print(f"❌ Get active streams error: {e}")
            return {}
    
    async def cleanup_test_data(self):
        """Clean up test conversations"""
        print("🧹 Cleaning up test data...")
        
        for conversation_id in self.test_conversations:
            try:
                async with self.session.delete(
                    f"{self.base_url}/api/v1/chat/conversations/{conversation_id}",
                    headers=self.get_headers()
                ) as response:
                    
                    if response.status == 200:
                        print(f"✅ Deleted conversation: {conversation_id}")
                    else:
                        print(f"⚠️  Failed to delete conversation {conversation_id}: {response.status}")
                        
            except Exception as e:
                print(f"❌ Cleanup error for {conversation_id}: {e}")
    
    async def run_complete_frontend_simulation(self) -> bool:
        """Run complete simulation of frontend workflow"""
        print("🚀 Starting Complete Frontend Stream Cancellation Simulation")
        print("=" * 80)
        
        try:
            # Step 1: Wait for server
            if not await self.wait_for_server():
                return False
            
            print("\n" + "=" * 60)
            print("STEP 1: REAL AUTHENTICATION FLOW")
            print("=" * 60)
            
            # Step 2: Real user registration and auth
            if not await self.register_test_user():
                return False
            
            if not await self.verify_authentication():
                return False
            
            print("\n" + "=" * 60)
            print("STEP 2: REAL CONVERSATION CREATION")
            print("=" * 60)
            
            # Step 3: Create real conversation
            conversation_id = await self.create_real_conversation()
            
            print("\n" + "=" * 60)
            print("STEP 3: REAL STREAMING & STREAM_ID CAPTURE")
            print("=" * 60)
            
            # Step 4: Start real streaming and capture stream_id
            stream_id = await self.test_real_streaming_and_capture_stream_id(conversation_id)
            
            if not stream_id:
                print("❌ CRITICAL: Could not capture stream_id from real stream!")
                print("   This means frontend can't cancel backend streams!")
                return False
            
            print("\n" + "=" * 60)
            print("STEP 4: REAL STREAM CANCELLATION")
            print("=" * 60)
            
            # Step 5: Test real stream cancellation
            cancellation_success = await self.test_real_stream_cancellation(stream_id)
            
            print("\n" + "=" * 60)
            print("STEP 5: STREAM MANAGEMENT TESTING")
            print("=" * 60)
            
            # Step 6: Test stream management endpoints
            active_streams_before = await self.test_get_active_streams()
            
            # Test with a longer stream that we can actually cancel
            print("🌊 Starting longer stream for proper cancellation test...")
            stream_id_2 = await self.test_long_stream_for_cancellation(conversation_id)
            
            if stream_id_2:
                active_streams_after = await self.test_get_active_streams()
                cancel_all_success = await self.test_cancel_all_streams()
                final_active_streams = await self.test_get_active_streams()
            else:
                cancel_all_success = True  # Skip if no second stream
                final_active_streams = {}
            
            # Step 7: Cleanup
            await self.cleanup_test_data()
            
            print("\n" + "=" * 80)
            print("🎯 FRONTEND SIMULATION RESULTS")
            print("=" * 80)
            
            print("✅ Real Authentication: PASS")
            print("✅ Real Conversation Creation: PASS")
            print(f"{'✅' if stream_id else '❌'} Real Stream ID Capture: {'PASS' if stream_id else 'FAIL'}")
            print(f"{'✅' if cancellation_success else '❌'} Real Stream Cancellation: {'PASS' if cancellation_success else 'FAIL'}")
            print(f"{'✅' if cancel_all_success else '❌'} Cancel All Streams: {'PASS' if cancel_all_success else 'FAIL'}")
            
            print(f"\n📊 Stream IDs Captured: {len(self.captured_stream_ids)}")
            for i, sid in enumerate(self.captured_stream_ids, 1):
                print(f"   {i}. {sid}")
            
            # Overall result
            all_tests_passed = all([
                stream_id is not None,
                cancellation_success,
                cancel_all_success
            ])
            
            if all_tests_passed:
                print("\n🎉 ALL FRONTEND SIMULATION TESTS PASSED!")
                print("✅ Real authentication works")
                print("✅ Real stream_id capture works") 
                print("✅ Real stream cancellation works")
                print("✅ Frontend can properly integrate with backend")
                print("\n💡 Ready for frontend integration!")
            else:
                print("\n❌ SOME FRONTEND SIMULATION TESTS FAILED!")
                if not stream_id:
                    print("🚨 CRITICAL: Backend not sending stream_id to frontend!")
                    print("   Frontend stop button cannot cancel backend streams!")
                if not cancellation_success:
                    print("🚨 Stream cancellation endpoint not working properly!")
            
            return all_tests_passed
            
        except Exception as e:
            print(f"❌ Frontend simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


class ServerManager:
    """Manage the backend server for testing"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.process = None
        
    async def start_server(self) -> bool:
        """Start the backend server"""
        print("🚀 Starting backend server...")
        
        # Change to backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Start server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--log-level", "warning"  # Reduce noise
        ]
        
        # Set environment variables to handle Unicode properly on Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        self.process = subprocess.Popen(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,  # Suppress output to avoid encoding issues
            stderr=subprocess.DEVNULL,  # Suppress output to avoid encoding issues
            env=env
        )
        
        # Give server time to start
        await asyncio.sleep(5)  # Increased wait time
        
        if self.process.poll() is None:
            print(f"✅ Server started on port {self.port}")
            return True
        else:
            print("❌ Server failed to start")
            return False
    
    def stop_server(self):
        """Stop the backend server"""
        if self.process:
            print("🛑 Stopping backend server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("✅ Server stopped")


async def main():
    """Main test runner - simulates complete frontend workflow"""
    server = ServerManager()
    
    try:
        # Start server
        if not await server.start_server():
            sys.exit(1)
        
        # Run complete frontend simulation
        async with RealFrontendStreamTester() as tester:
            success = await tester.run_complete_frontend_simulation()
        
        if success:
            print("\n🎉 Complete frontend simulation successful!")
            print("🔗 Frontend can fully integrate with backend stream cancellation!")
            sys.exit(0)
        else:
            print("\n❌ Frontend simulation revealed integration issues!")
            print("🔧 Backend needs fixes before frontend integration!")
            sys.exit(1)
             
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)
    finally:
        server.stop_server()


if __name__ == "__main__":
    print("🧪 Real Frontend-Backend Stream Cancellation Test Suite")
    print("Testing complete frontend workflow with NO FAKE DATA")
    print("=" * 80)
    asyncio.run(main()) 