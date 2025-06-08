"""
Test Client Disconnection Handling

This test specifically focuses on testing how the backend handles
client disconnections during streaming and ensures proper cleanup.
"""

import asyncio
import aiohttp
import json
import signal
import sys
from typing import Dict, Optional
from datetime import datetime


class ClientDisconnectionTester:
    """Test client disconnection scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        
    def get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
    
    async def create_conversation(self, session: aiohttp.ClientSession) -> str:
        """Create a test conversation"""
        print("🔧 Creating test conversation...")
        
        conversation_data = {
            "title": f"Disconnection Test {datetime.now().isoformat()}",
            "model": "gpt-4o-mini"
        }
        
        async with session.post(
            f"{self.base_url}/api/v1/chat/conversations",
            headers=self.get_headers(),
            json=conversation_data
        ) as response:
            if response.status == 201:
                result = await response.json()
                conversation_id = result['conversation_id']
                print(f"✅ Created conversation: {conversation_id}")
                return conversation_id
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create conversation: {response.status} - {error_text}")
    
    async def test_abrupt_disconnection(self):
        """Test abrupt client disconnection"""
        print("\n" + "="*60)
        print("🧪 TEST: Abrupt Client Disconnection")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            # Create conversation
            conversation_id = await self.create_conversation(session)
            
            print("🚀 Starting stream that will be abruptly disconnected...")
            
            # Start streaming request
            message_data = {
                "content": "Write a very detailed 2000-word essay about the future of artificial intelligence, covering multiple aspects like ethics, technology, society, and economics.",
                "role": "user"
            }
            
            response = await session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                headers=self.get_headers(),
                json=message_data
            )
            
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Failed to start stream: {response.status} - {error_text}")
            
            print("✅ Stream started, reading initial events...")
            
            # Read a few events to ensure stream is active
            event_count = 0
            stream_id = None
            
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    
                    try:
                        event_data = json.loads(data_str)
                        event_type = event_data.get('type', 'unknown')
                        
                        print(f"📦 Event {event_count + 1}: {event_type}")
                        
                        # Extract stream ID
                        if 'data' in event_data and 'stream_id' in event_data['data']:
                            stream_id = event_data['data']['stream_id']
                            print(f"🆔 Stream ID: {stream_id}")
                        
                        event_count += 1
                        
                        # After reading a few events, simulate disconnection
                        if event_count >= 3:
                            print("🔌 Simulating abrupt disconnection...")
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # Abruptly close the connection
            response.close()
            print("⚡ Connection closed abruptly")
            
            # Wait for backend to detect disconnection
            print("⏳ Waiting for backend to detect disconnection...")
            await asyncio.sleep(3)
            
            print("✅ Abrupt disconnection test completed")
            return stream_id
    
    async def test_graceful_disconnection(self):
        """Test graceful client disconnection"""
        print("\n" + "="*60)
        print("🧪 TEST: Graceful Client Disconnection")
        print("="*60)
        
        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Create conversation
            conversation_id = await self.create_conversation(session)
            
            print("🚀 Starting stream with timeout...")
            
            message_data = {
                "content": "Explain quantum mechanics in extreme detail with mathematical formulations.",
                "role": "user"
            }
            
            try:
                response = await session.post(
                    f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                    headers=self.get_headers(),
                    json=message_data
                )
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to start stream: {response.status} - {error_text}")
                
                print("✅ Stream started, will timeout in 5 seconds...")
                
                event_count = 0
                stream_id = None
                
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        
                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get('type', 'unknown')
                            
                            print(f"📦 Event {event_count + 1}: {event_type}")
                            
                            # Extract stream ID
                            if 'data' in event_data and 'stream_id' in event_data['data']:
                                stream_id = event_data['data']['stream_id']
                            
                            event_count += 1
                            
                        except json.JSONDecodeError:
                            continue
                
            except asyncio.TimeoutError:
                print("⏰ Connection timed out (graceful disconnection)")
            except aiohttp.ServerDisconnectedError:
                print("🔌 Server disconnected")
            
            print("✅ Graceful disconnection test completed")
    
    async def test_connection_interruption(self):
        """Test connection interruption scenarios"""
        print("\n" + "="*60)
        print("🧪 TEST: Connection Interruption")
        print("="*60)
        
        connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create conversation
            conversation_id = await self.create_conversation(session)
            
            print("🚀 Starting stream and then interrupting connection...")
            
            message_data = {
                "content": "Generate a comprehensive analysis of climate change impacts. Include detailed scientific data and projections.",
                "role": "user"
            }
            
            response = await session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
                headers=self.get_headers(),
                json=message_data
            )
            
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Failed to start stream: {response.status} - {error_text}")
            
            print("✅ Stream started...")
            
            # Read events for a short time
            event_count = 0
            
            try:
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    if line_str.startswith('data: '):
                        event_count += 1
                        print(f"📦 Event {event_count}")
                        
                        # Interrupt after a few events
                        if event_count >= 2:
                            print("⚡ Forcing connection interruption...")
                            # Force close the connector to simulate network interruption
                            await connector.close()
                            break
                            
            except Exception as e:
                print(f"🔌 Connection interrupted: {type(e).__name__}")
            
            print("✅ Connection interruption test completed")
    
    async def check_stream_cleanup(self):
        """Check if streams are properly cleaned up after disconnection"""
        print("\n" + "="*60)
        print("🧪 TEST: Stream Cleanup Verification")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            print("📋 Checking active streams after disconnection tests...")
            
            async with session.get(
                f"{self.base_url}/api/v1/chat/stream/active",
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    active_count = result.get('count', 0)
                    print(f"🔍 Active streams found: {active_count}")
                    
                    if active_count == 0:
                        print("✅ All streams properly cleaned up")
                    else:
                        print(f"⚠️  {active_count} streams still active")
                        print(f"📋 Active streams: {result.get('active_streams', [])}")
                else:
                    print(f"❌ Failed to check active streams: {response.status}")
    
    async def run_all_tests(self):
        """Run all disconnection tests"""
        print("🎯 Starting Client Disconnection Tests")
        print("="*60)
        
        try:
            await self.test_abrupt_disconnection()
            await asyncio.sleep(1)  # Brief pause between tests
            
            await self.test_graceful_disconnection()
            await asyncio.sleep(1)
            
            await self.test_connection_interruption()
            await asyncio.sleep(2)  # Wait for cleanup
            
            await self.check_stream_cleanup()
            
            print("\n" + "="*60)
            print("🎉 ALL DISCONNECTION TESTS COMPLETED!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            print("="*60)
            raise


async def main():
    """Main test runner"""
    print("🚀 Client Disconnection Test Suite")
    print("="*60)
    
    # Configuration
    base_url = "http://localhost:8000"
    auth_token = None  # Set if you need authentication
    
    print(f"🌐 Target URL: {base_url}")
    
    tester = ClientDisconnectionTester(base_url, auth_token)
    await tester.run_all_tests()


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\n🛑 Test interrupted by user")
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the tests
    asyncio.run(main()) 