# Streaming Pipeline Multi-Worker Migration Guide

## Current State

**Status**: Single worker only (`workers=1`)  
**Limitation**: Stream cancellation fails across multiple workers due to process-local state management  
**Location**: `backend/start_app.py:456-465`

## Problem Analysis

### Current Architecture Issues

1. **Process-Local State**: `StreamingManager.streams` dict exists only in each worker process
2. **Object Serialization**: `StreamingHandler` and `assistant_client` objects cannot be shared between processes
3. **Cross-Worker Communication**: No mechanism for workers to coordinate stream operations
4. **State Inconsistency**: Stream exists in Worker A, but cancellation request hits Worker B

### What Happens Now

```
Worker 1: StreamingManager.streams = {"stream_123": handler_obj}
Worker 2: StreamingManager.streams = {"stream_456": handler_obj}
Worker 3: StreamingManager.streams = {}

Cancel Request for stream_123 → Load Balancer → Worker 2
Worker 2: "Stream stream_123 not found" ❌
Meanwhile: stream_123 continues running in Worker 1
```

## Migration Strategies

### Option 1: Sticky Sessions (Recommended - Low Risk)

**Implementation**: Configure load balancer to route requests from the same client to the same worker

#### Traefik Configuration
```yaml
# docker-compose.prod.yml
services:
  backend:
    labels:
      - "traefik.http.services.backend.loadbalancer.sticky.cookie.name=stream_worker"
      - "traefik.http.services.backend.loadbalancer.sticky.cookie.httpOnly=true"
      - "traefik.http.services.backend.loadbalancer.sticky.cookie.secure=true"
```

#### Pros
- ✅ Zero code changes required
- ✅ Immediate fix for stream cancellation
- ✅ Battle-tested by Netflix, GitHub, Discord
- ✅ Easy rollback if issues occur

#### Cons
- ❌ Uneven load distribution
- ❌ Session loss if worker crashes
- ❌ Doesn't solve the architectural problem

#### Implementation Steps
1. Update `docker-compose.prod.yml` with sticky session labels
2. Test stream cancellation with multiple workers
3. Monitor load distribution across workers
4. Set `workers=4` in `start_app.py`

---

### Option 2: Redis-Based Coordination (Medium Risk)

**Implementation**: Use Redis for stream ownership tracking and cross-worker messaging

#### Architecture
```
Redis: stream:{stream_id} → {owner_worker_id, user_id, status, created_at}
Worker 1: Local objects + Redis ownership
Worker 2: Local objects + Redis ownership  
Worker 3: Local objects + Redis ownership
```

#### Code Changes Required

##### 1. Worker ID Management
```python
# app/core/worker_id.py
import os
import socket

def get_worker_id() -> str:
    """Generate stable worker ID"""
    return f"{socket.gethostname()}:{os.getpid()}"
```

##### 2. StreamingManager Updates
```python
# app/integrations/openai/streaming_handler.py
class StreamingManager:
    def __init__(self):
        self.worker_id = get_worker_id()
        self.streams: Dict[str, StreamingHandler] = {}  # Local objects
        self.redis = get_redis()
        
    async def create_stream(self, user_id: str, conversation_id: Optional[str] = None):
        handler = StreamingHandler(user_id, conversation_id)
        
        # Store ownership in Redis
        await self.redis.hset(f"stream:{handler.stream_id}", mapping={
            "owner_worker_id": self.worker_id,
            "user_id": user_id,
            "conversation_id": conversation_id or "",
            "status": "active",
            "created_at": time.time()
        })
        
        # Keep object locally
        self.streams[handler.stream_id] = handler
        return handler
        
    async def cancel_stream(self, stream_id: str, reason: str = "user_requested"):
        # Check if we own it locally
        if stream_id in self.streams:
            self.streams[stream_id].cancel_streaming(reason)
            await self.redis.hset(f"stream:{stream_id}", "status", "cancelled")
            return True
            
        # Check Redis for owner
        stream_data = await self.redis.hgetall(f"stream:{stream_id}")
        if not stream_data:
            return False
            
        owner_worker_id = stream_data.get("owner_worker_id")
        if owner_worker_id:
            # Send cancellation message to owner worker
            await self.redis.publish(f"worker:{owner_worker_id}:cancel", json.dumps({
                "stream_id": stream_id,
                "reason": reason
            }))
            return True
            
        return False
```

##### 3. Cross-Worker Messaging
```python
# app/integrations/worker_messaging.py
class WorkerMessaging:
    def __init__(self, worker_id: str, streaming_manager):
        self.worker_id = worker_id
        self.streaming_manager = streaming_manager
        self.redis = get_redis()
        self.pubsub = None
        
    async def start_listening(self):
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(f"worker:{self.worker_id}:cancel")
        asyncio.create_task(self._listen_for_messages())
        
    async def _listen_for_messages(self):
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                stream_id = data['stream_id']
                reason = data['reason']
                
                if stream_id in self.streaming_manager.streams:
                    self.streaming_manager.streams[stream_id].cancel_streaming(reason)
```

#### Pros
- ✅ True multi-worker support
- ✅ Maintains object locality
- ✅ Scalable architecture
- ✅ Stream ownership tracking

#### Cons
- ❌ Complex implementation
- ❌ Redis pub/sub dependency
- ❌ Message delivery not guaranteed
- ❌ Requires extensive testing

---

### Option 3: Complete Stateless Architecture (High Risk)

**Implementation**: Move all streaming state to external systems

#### Required Changes

##### 1. Streaming State Externalization
```python
# Replace in-memory streaming with external coordination
class StatelessStreamingManager:
    async def create_stream(self, user_id: str):
        # Create stream record in database
        stream_record = await db.create_stream_session(user_id)
        
        # Store AI context in Redis
        await redis.hset(f"ai_context:{stream_record.id}", mapping={
            "messages": json.dumps(conversation_history),
            "model_state": json.dumps(model_config),
            "tool_calls": json.dumps([])
        })
        
        return stream_record.id
        
    async def process_stream_chunk(self, stream_id: str, chunk: str):
        # Stateless processing - load context from Redis
        context = await redis.hgetall(f"ai_context:{stream_id}")
        # Process chunk and update context
        # Store result back to Redis
```

##### 2. AI Client Refactoring
- Make `assistant_client` stateless
- Store conversation state in Redis/Database
- Implement context reconstruction for each request

##### 3. Database Schema Updates
```sql
-- Stream sessions table
CREATE TABLE stream_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_id UUID,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Stream context table  
CREATE TABLE stream_contexts (
    stream_id UUID REFERENCES stream_sessions(id),
    context_type VARCHAR(50), -- 'messages', 'model_state', 'tool_calls'
    context_data JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Pros
- ✅ Truly stateless and scalable
- ✅ No worker affinity required
- ✅ Crash-resistant
- ✅ Easy horizontal scaling

#### Cons
- ❌ Major architectural overhaul
- ❌ Performance overhead (context loading)
- ❌ Complex AI state management
- ❌ High development/testing effort

---

## Implementation Roadmap

### Phase 1: Quick Fix (1-2 days)
1. **Implement sticky sessions** with Traefik
2. **Test multi-worker setup** with `workers=4`
3. **Verify stream cancellation** works correctly
4. **Monitor performance** and load distribution

### Phase 2: Redis Coordination (1-2 weeks)
1. **Implement worker ID system**
2. **Add Redis ownership tracking**
3. **Build cross-worker messaging**
4. **Comprehensive testing** with multiple workers
5. **Gradual rollout** with feature flags

### Phase 3: Stateless Architecture (1-2 months)
1. **Design stateless streaming architecture**
2. **Refactor AI client for statelessness**
3. **Implement external state storage**
4. **Performance optimization**
5. **Full migration and testing**

## Testing Strategy

### Multi-Worker Stream Cancellation Test
```python
# tests/test_multi_worker_streaming.py
async def test_cross_worker_cancellation():
    # Start stream on worker 1
    stream_id = await create_stream_via_worker_1()
    
    # Cancel stream via worker 2  
    result = await cancel_stream_via_worker_2(stream_id)
    
    # Verify cancellation worked
    assert result.success == True
    assert stream_actually_cancelled(stream_id)
```

### Load Testing
```bash
# Test with multiple workers
wrk -t12 -c400 -d30s --script=stream_test.lua http://localhost:8000/api/v1/chat/stream
```

## Performance Considerations

### Current Single Worker Performance
- **Concurrent streams**: ~50-100 (memory limited)
- **CPU utilization**: Single core bound
- **Memory per stream**: ~5-10MB

### Multi-Worker Scaling Expectations
- **4 workers**: 4x concurrent capacity
- **Sticky sessions**: May create hot spots
- **Redis coordination**: ~1-2ms overhead per operation

## Risk Assessment

| Approach | Implementation Risk | Performance Risk | Operational Risk |
|----------|-------------------|------------------|------------------|
| Sticky Sessions | Low | Medium | Low |
| Redis Coordination | Medium | Low | Medium |
| Stateless Architecture | High | Medium | High |

## Monitoring and Observability

### Key Metrics to Track
1. **Stream cancellation success rate**
2. **Cross-worker message delivery time**
3. **Worker load distribution**
4. **Redis pub/sub message lag**
5. **Stream lifecycle completion rate**

### Alerting Thresholds
- Stream cancellation failure rate > 5%
- Cross-worker message delay > 500ms
- Worker load imbalance > 30%
- Redis connection failures

## Decision Matrix

**For immediate production needs**: Choose **Sticky Sessions**  
**For long-term scalability**: Plan **Redis Coordination**  
**For ultimate flexibility**: Consider **Stateless Architecture**

## Next Steps

1. **Immediate**: Implement sticky sessions to unblock multi-worker deployment
2. **Short-term**: Design and prototype Redis coordination system
3. **Long-term**: Evaluate business need for complete stateless architecture

---

*Last updated: Current Date*  
*Status: Planning Phase*  
*Owner: Development Team*
