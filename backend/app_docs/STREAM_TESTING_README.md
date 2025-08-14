# Stream Cancellation Testing

This document explains how to test the stream cancellation functionality in the backend.

## 🎯 What We're Testing

The stream cancellation functionality includes:

1. **Explicit Stream Cancellation** - User clicks "stop generating" button
2. **Client Disconnection Handling** - User closes browser/tab during streaming
3. **Partial Message Saving** - Incomplete messages saved with "cancelled" status
4. **Stream Management** - Tracking and cleaning up active streams

## 🚀 Running the Tests

### Prerequisites

Make sure you have the required dependencies:

```bash
pip install aiohttp uvicorn
```

### Option 1: Run All Tests Automatically

```bash
cd backend
python run_stream_tests.py
```

This will:
1. Start the backend server
2. Run all stream cancellation tests
3. Run client disconnection tests
4. Stop the backend server

### Option 2: Run Tests Manually

1. **Start the backend:**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **Run stream cancellation tests:**
```bash
python test_stream_cancellation.py
```

3. **Run client disconnection tests:**
```bash
python test_client_disconnection.py
```

## 🧪 Test Scenarios

### 1. Explicit Stream Cancellation Test

**What it tests:**
- Starting a stream
- Getting the stream ID from SSE events
- Calling the cancel API endpoint
- Verifying the stream is cancelled

**Expected behavior:**
- Stream starts normally
- Stream ID is captured
- Cancel API returns success
- Partial message is saved with "cancelled" status

### 2. Client Disconnection Tests

**What it tests:**
- Abrupt connection closing
- Graceful timeouts
- Network interruptions
- Backend cleanup after disconnection

**Expected behavior:**
- Backend detects client disconnection
- Active streams are cleaned up
- Partial messages are saved appropriately

### 3. Stream Management Tests

**What it tests:**
- Getting active streams
- Cancelling all user streams
- Stream cleanup verification

## 📡 API Endpoints Tested

### Stream Management Endpoints

1. **Cancel Specific Stream**
   ```http
   POST /api/v1/chat/stream/cancel/{stream_id}
   ```

2. **Cancel All User Streams**
   ```http
   POST /api/v1/chat/stream/cancel-all
   ```

3. **Get Active Streams**
   ```http
   GET /api/v1/chat/stream/active
   ```

### Streaming Endpoint (Enhanced)

```http
POST /api/v1/chat/conversations/{conversation_id}/stream
```

Now includes:
- Client disconnection detection
- Automatic stream cleanup
- Partial message saving on cancellation

## 🔍 What to Look For

### Successful Test Indicators

✅ **Stream starts successfully**
✅ **Stream ID is captured from SSE events**
✅ **Cancel API responds with success**
✅ **Client disconnection is detected**
✅ **Active streams are cleaned up**
✅ **Partial messages are saved with correct status**

### Backend Logs to Monitor

When running tests, check backend logs for:

```
INFO: StreamingHandler initialized for user ...
INFO: Starting stream for user ...
INFO: Cancelling stream for user ... reason: user_requested
INFO: Client disconnected for stream ...
INFO: Saved partial message ... with status 'cancelled'
```

## 🗃️ Database Changes

### Message Status Field

Messages now support these statuses:
- `pending` - Message being processed
- `streaming` - Currently streaming
- `completed` - Fully delivered
- `error` - Failed processing
- `cancelled` - User stopped generation

### Partial Message Fields

When a stream is cancelled, the message is saved with:
- `status = "cancelled"`
- `stream_completed = False`
- `is_streaming = False`
- `content = partial_content_received`

## 🐛 Troubleshooting

### Common Issues

1. **Backend won't start**
   - Check if port 8000 is available
   - Verify all dependencies are installed
   - Check database connection

2. **Tests fail with connection errors**
   - Ensure backend is running on localhost:8000
   - Check firewall settings
   - Verify no other services on port 8000

3. **Stream cancellation doesn't work**
   - Check if stream ID is being captured correctly
   - Verify cancel API endpoint is accessible
   - Look for backend errors in logs

### Debug Mode

For more detailed logging, set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## 📊 Test Results Interpretation

### Successful Test Run

```
🎉 ALL TESTS COMPLETED SUCCESSFULLY!
✅ Explicit cancellation test completed
✅ Client disconnection test completed
✅ Cancel all streams test completed
✅ Stream management test completed
```

### Failed Test Indicators

```
❌ Stream {stream_id} not found for cancellation
❌ Failed to cancel stream: 500
⚠️  No stream ID found to cancel
⚠️  {count} streams still active
```

## 🔧 Development Notes

### Adding New Tests

To add new stream cancellation tests:

1. Create a new method in `StreamCancellationTester`
2. Follow the pattern: setup → action → verify
3. Add appropriate logging and assertions
4. Include cleanup in finally blocks

### Backend Enhancements

The backend now includes:
- Enhanced `StreamingHandler` with cancellation support
- `StreamingService` with partial message saving
- Client disconnection detection in streaming endpoint
- New API endpoints for stream management

## 🚀 Next Steps

After successful testing, you can:

1. **Integrate with Frontend** - Add AbortController to frontend
2. **Add UI Indicators** - Show partial messages in chat history
3. **Enhance Error Handling** - Better error messages for users
4. **Add Metrics** - Track cancellation rates and reasons
5. **Implement Retry Logic** - Allow resuming cancelled conversations 