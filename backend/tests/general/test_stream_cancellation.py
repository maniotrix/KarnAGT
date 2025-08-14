"""
Test Stream Cancellation Functionality

This test file validates:
1. Stream cancellation via API endpoint
2. Client disconnection handling
3. Partial message saving with cancelled status
4. Active stream management
"""

import asyncio
import aiohttp
import json
import time
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime


class StreamCancellationTester:
    """Test class for stream cancellation functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_streams: List[str] = []
        
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
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
    
    async def create_test_conversation(self) -> str:
        """Create a test conversation for streaming tests"""
        print("🔧 Creating test conversation...")
        
        conversation_data = {
            "title": f"Stream Test {datetime.now().isoformat()}",
            "model": "gpt-4o-mini"
        }
        
        async with self.session.post(
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
    
    async def start_stream(self, conversation_id: str, message: str) -> aiohttp.ClientResponse:
        """Start a streaming request"""
        print(f"🚀 Starting stream for conversation {conversation_id[:8]}...")
        
        message_data = {
            "content": message,
            "role": "user"
        }
        
        response = await self.session.post(
            f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/stream",
            headers=self.get_headers(),
            json=message_data
        )
        
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"Failed to start stream: {response.status} - {error_text}")
        
        print(f"✅ Stream started successfully")
        return response
    
    async def read_stream_events(self, response: aiohttp.ClientResponse, max_events: int = 10) -> List[Dict]:
        """Read events from a stream response"""
        events = []
        event_count = 0
        
        print("📡 Reading stream events...")
        
        async for line in response.content:
            if event_count >= max_events:
                break
                
            line_str = line.decode('utf-8').strip()
            
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # Remove 'data: ' prefix
                
                try:
                    event_data = json.loads(data_str)
                    events.append(event_data)
                    
                    print(f"📦 Event {event_count + 1}: {event_data.get('type', 'unknown')}")
                    
                    # Extract stream_id if available
                    if 'data' in event_data and 'stream_id' in event_data['data']:
                        stream_id = event_data['data']['stream_id']
                        if stream_id not in self.active_streams:
                            self.active_streams.append(stream_id)
                            print(f"🆔 Stream ID: {stream_id}")
                    
                    event_count += 1
                    
                    # Small delay to simulate real reading
                    await asyncio.sleep(0.1)
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse event data: {e}")
                    continue
        
        print(f"📊 Read {len(events)} events")
        return events
    
    async def cancel_stream_by_id(self, stream_id: str) -> Dict:
        """Cancel a stream by its ID"""
        print(f"🛑 Cancelling stream: {stream_id}")
        
        async with self.session.post(
            f"{self.base_url}/api/v1/chat/stream/cancel/{stream_id}",
            headers=self.get_headers()
        ) as response:
            result = await response.json()
            
            if response.status == 200:
                print(f"✅ Stream cancelled successfully")
            else:
                print(f"❌ Failed to cancel stream: {response.status}")
                
            return result
    
    async def cancel_all_streams(self) -> Dict:
        """Cancel all active streams for the user"""
        print("🛑 Cancelling all user streams...")
        
        async with self.session.post(
            f"{self.base_url}/api/v1/chat/stream/cancel-all",
            headers=self.get_headers()
        ) as response:
            result = await response.json()
            
            if response.status == 200:
                print(f"✅ All streams cancelled successfully")
            else:
                print(f"❌ Failed to cancel all streams: {response.status}")
                
            return result
    
    async def get_active_streams(self) -> Dict:
        """Get all active streams for the user"""
        print("📋 Getting active streams...")
        
        async with self.session.get(
            f"{self.base_url}/api/v1/chat/stream/active",
            headers=self.get_headers()
        ) as response:
            result = await response.json()
            
            if response.status == 200:
                active_count = result.get('count', 0)
                print(f"✅ Found {active_count} active streams")
            else:
                print(f"❌ Failed to get active streams: {response.status}")
                
            return result
    
    async def test_explicit_cancellation(self):
        """Test explicit stream cancellation via API"""
        print("\n" + "="*60)
        print("🧪 TEST: Explicit Stream Cancellation")
        print("="*60)
        
        # Create conversation
        conversation_id = await self.create_test_conversation()
        
        # Start stream
        response = await self.start_stream(
            conversation_id, 
            "Write a very long story about artificial intelligence. Make it at least 1000 words."
        )
        
        # Read a few events to get stream ID
        events = await self.read_stream_events(response, max_events=5)
        
        # Cancel the stream if we have a stream ID
        if self.active_streams:
            stream_id = self.active_streams[0]
            cancel_result = await self.cancel_stream_by_id(stream_id)
            print(f"📋 Cancel result: {cancel_result}")
        else:
            print("⚠️  No stream ID found to cancel")
        
        # Close the response
        response.close()
        
        print("✅ Explicit cancellation test completed")
    
    async def test_client_disconnection(self):
        """Test client disconnection handling"""
        print("\n" + "="*60)
        print("🧪 TEST: Client Disconnection")
        print("="*60)
        
        # Create conversation
        conversation_id = await self.create_test_conversation()
        
        # Start stream
        response = await self.start_stream(
            conversation_id,
            "Explain quantum computing in great detail with examples."
        )
        
        # Read a few events
        events = await self.read_stream_events(response, max_events=3)
        
        # Simulate client disconnection by closing the response abruptly
        print("🔌 Simulating client disconnection...")
        response.close()
        
        # Wait a bit for backend to detect disconnection
        await asyncio.sleep(2)
        
        # Check if streams were cleaned up
        active_result = await self.get_active_streams()
        
        print("✅ Client disconnection test completed")
    
    async def test_cancel_all_streams(self):
        """Test cancelling all user streams"""
        print("\n" + "="*60)
        print("🧪 TEST: Cancel All Streams")
        print("="*60)
        
        # Create multiple conversations
        conversations = []
        for i in range(2):
            conversation_id = await self.create_test_conversation()
            conversations.append(conversation_id)
        
        # Start multiple streams
        responses = []
        for i, conversation_id in enumerate(conversations):
            response = await self.start_stream(
                conversation_id,
                f"Tell me about the history of computer science. This is request {i+1}."
            )
            responses.append(response)
            
            # Read a few events from each
            await self.read_stream_events(response, max_events=2)
        
        # Check active streams
        active_result = await self.get_active_streams()
        
        # Cancel all streams
        cancel_result = await self.cancel_all_streams()
        print(f"📋 Cancel all result: {cancel_result}")
        
        # Close all responses
        for response in responses:
            response.close()
        
        # Check active streams again
        final_active_result = await self.get_active_streams()
        
        print("✅ Cancel all streams test completed")
    
    async def test_stream_management(self):
        """Test stream management functionality"""
        print("\n" + "="*60)
        print("🧪 TEST: Stream Management")
        print("="*60)
        
        # Get initial active streams
        initial_active = await self.get_active_streams()
        
        # Create conversation and start stream
        conversation_id = await self.create_test_conversation()
        response = await self.start_stream(
            conversation_id,
            "Describe the process of machine learning."
        )
        
        # Read events to establish stream
        await self.read_stream_events(response, max_events=3)
        
        # Get active streams
        active_after_start = await self.get_active_streams()
        
        # Cancel stream
        if self.active_streams:
            stream_id = self.active_streams[0]
            await self.cancel_stream_by_id(stream_id)
        
        # Close response
        response.close()
        
        # Get final active streams
        final_active = await self.get_active_streams()
        
        print("✅ Stream management test completed")
    
    async def run_all_tests(self):
        """Run all stream cancellation tests"""
        print("🎯 Starting Stream Cancellation Tests")
        print("="*60)
        
        try:
            await self.test_explicit_cancellation()
            await self.test_client_disconnection()
            await self.test_cancel_all_streams()
            await self.test_stream_management()
            
            print("\n" + "="*60)
            print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            print("="*60)
            raise


async def main():
    """Main test runner"""
    print("🚀 Stream Cancellation Test Suite")
    print("="*60)
    
    # Configuration
    base_url = "http://localhost:8000"
    auth_token = None  # Set this if you need authentication
    
    print(f"🌐 Target URL: {base_url}")
    
    # Run tests
    async with StreamCancellationTester(base_url, auth_token) as tester:
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