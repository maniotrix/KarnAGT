# User Memory System Implementation Plan

## Overview

Implementation of ChatGPT-style user memory system using a 6-bucket categorization approach, leveraging existing backend infrastructure.

## Current Architecture Assessment

### ✅ Existing Assets
- `ConversationContextBuilder` - Context management and summarization
- `MemoryPreference` model - Sophisticated preference system  
- `User` model - Basic user management with memory settings
- Database infrastructure - SQLAlchemy setup
- Message/Conversation models - Chat history storage

### 🔧 What We're Adding
- `UserMemory` model - Core memory storage
- `MemoryService` - Memory extraction and retrieval
- Memory-aware context building
- Memory management APIs
- Basic memory UI/dashboard

## Memory Bucket System

### 6 Core Memory Buckets

| Bucket | Content | TTL Strategy | Priority |
|--------|---------|--------------|----------|
| **Identity/Profile** | Name, pronouns, timezone, bio, device info | Permanent (user-controlled) | High |
| **Stable Preferences** | Communication style, diet, tool preferences | Version-controlled updates | High |
| **Long-term Goals** | Projects, learning goals, objectives | Archive when complete | Medium |
| **Workflows/Habits** | Daily routines, coding patterns, schedules | Decay after 90-180 days inactivity | Medium |
| **Capabilities/Constraints** | Hardware specs, budgets, skill levels | Event-triggered updates | Low |
| **Social/Contact Graph** | Colleagues, collaborators, relationships | Confidence decay over time | Low |

## Implementation Phases

---

## Phase 1: Core Foundation (Week 1-2)

### 1.1 Database Models

#### Create `UserMemory` Model
```python
# backend/app/models/database/user_memory.py
class UserMemory(Base):
    __tablename__ = "user_memories"
    
    # Primary keys
    id = Column(Integer, primary_key=True)
    memory_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Memory categorization
    bucket = Column(String(50), nullable=False)  # identity, preferences, goals, workflows, capabilities, social
    memory_type = Column(String(50), nullable=False)  # fact, preference, goal, workflow, capability, contact
    
    # Content
    content = Column(Text, nullable=False)
    structured_data = Column(JSON, default=dict)  # For complex data
    
    # Scoring and confidence
    importance = Column(Float, default=0.5)
    confidence = Column(Float, default=1.0)
    
    # Lifecycle management
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)  # NULL = permanent
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Bucket-specific fields
    status = Column(String(50), nullable=True)  # For goals: active, completed, paused
    last_activity = Column(DateTime, nullable=True)  # For workflows
    relationship_strength = Column(String(20), nullable=True)  # For social
    
    # Source tracking
    source_conversation_id = Column(String(36), nullable=True)
    source_message_id = Column(String(36), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="memories")
```

#### Update User Model
```python
# Add to backend/app/models/database/user.py
# In User class relationships section:
memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
```

#### Database Migration
```bash
# Create migration
alembic revision --autogenerate -m "Add user_memories table"
alembic upgrade head
```

### 1.2 Memory Service Foundation

#### Create Memory Service
```python
# backend/app/services/memory/__init__.py
# backend/app/services/memory/memory_service.py

class MemoryService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
    # Core CRUD operations
    async def store_memory(self, user_id: int, bucket: str, content: str, **kwargs) -> UserMemory
    async def get_memories_by_bucket(self, user_id: int, bucket: str, limit: int = 10) -> List[UserMemory]
    async def get_relevant_memories(self, user_id: int, query: str, limit: int = 5) -> List[UserMemory]
    async def update_memory(self, memory_id: str, **updates) -> UserMemory
    async def archive_memory(self, memory_id: str) -> bool
    async def get_user_memory_stats(self, user_id: int) -> Dict[str, Any]
```

### 1.3 Memory Preference Integration

#### Setup Default Memory Buckets
```python
# backend/app/services/memory/memory_setup.py

MEMORY_BUCKET_CONFIGS = {
    "identity": {
        "retention_days": None,  # Permanent
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True
    },
    "preferences": {
        "retention_days": None,  # Permanent until changed
        "importance_threshold": 0.7,
        "auto_categorization": True,
        "capture_enabled": True
    },
    "goals": {
        "retention_days": 730,  # 2 years
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True
    },
    # ... other buckets
}

async def create_default_memory_preferences(user_id: int):
    """Create default memory preferences for all buckets"""
    for bucket, config in MEMORY_BUCKET_CONFIGS.items():
        pref = MemoryPreference(
            user_id=user_id,
            topic=bucket,
            **config
        )
        # Save to database
```

---

## Phase 2: Memory Extraction (Week 3-4)

### 2.1 Memory Extraction Service

#### LLM-Powered Memory Extraction
```python
# backend/app/services/memory/memory_extractor.py

class MemoryExtractor:
    BUCKET_EXTRACTION_PROMPTS = {
        "identity": """
        Extract basic identity information from this conversation:
        - Name, pronouns, role/job title
        - Location, timezone
        - Basic biographical info
        Return as JSON list of memories.
        """,
        
        "preferences": """
        Extract user preferences and communication style:
        - Communication preferences (formal/casual, detail level)
        - Tool preferences, workflow likes/dislikes
        - Format preferences
        Return as JSON list of memories.
        """,
        
        "goals": """
        Extract goals, projects, or objectives mentioned:
        - Short-term and long-term goals
        - Active projects
        - Learning objectives
        Return as JSON list with goal status.
        """
    }
    
    async def extract_memories_from_conversation(
        self, 
        conversation_messages: List[Dict],
        user_id: int,
        conversation_id: str
    ) -> Dict[str, List[UserMemory]]:
        """Extract memories by bucket from conversation"""
        
        extracted_memories = {}
        
        for bucket, prompt in self.BUCKET_EXTRACTION_PROMPTS.items():
            # Check if user has this bucket enabled
            if await self.is_bucket_enabled(user_id, bucket):
                memories = await self.extract_bucket_memories(
                    conversation_messages, 
                    bucket, 
                    prompt,
                    user_id,
                    conversation_id
                )
                extracted_memories[bucket] = memories
                
        return extracted_memories
    
    async def extract_bucket_memories(
        self, 
        messages: List[Dict], 
        bucket: str, 
        prompt: str,
        user_id: int,
        conversation_id: str
    ) -> List[UserMemory]:
        """Extract memories for a specific bucket"""
        
        # Format conversation for LLM
        conversation_text = self.format_messages_for_extraction(messages)
        
        # Call LLM for extraction
        extraction_result = await self.llm_extract(prompt, conversation_text)
        
        # Convert to UserMemory objects
        memories = []
        for item in extraction_result:
            memory = UserMemory(
                user_id=user_id,
                bucket=bucket,
                content=item["content"],
                memory_type=item.get("type", "fact"),
                importance=item.get("importance", 0.5),
                confidence=item.get("confidence", 0.8),
                source_conversation_id=conversation_id,
                structured_data=item.get("metadata", {})
            )
            memories.append(memory)
            
        return memories
```

### 2.2 Automatic Memory Trigger

#### Integration with Message Processing
```python
# backend/app/services/chat/chat_service.py (or wherever you process messages)

class ChatService:
    def __init__(self):
        self.memory_extractor = MemoryExtractor()
        self.memory_service = MemoryService()
    
    async def process_conversation_completion(
        self, 
        user_id: int, 
        conversation_id: str,
        messages: List[Dict]
    ):
        """Called after conversation completes - extract memories"""
        
        # Check if user has memory enabled
        user = await self.get_user(user_id)
        if not user.memory_enabled:
            return
            
        # Extract memories from recent messages
        recent_messages = messages[-10:]  # Last 10 messages
        extracted_memories = await self.memory_extractor.extract_memories_from_conversation(
            recent_messages, user_id, conversation_id
        )
        
        # Store extracted memories
        for bucket, memories in extracted_memories.items():
            for memory in memories:
                await self.memory_service.store_memory_if_worthy(memory)
```

---

## Phase 3: Context Enhancement (Week 5-6)

### 3.1 Memory-Aware Context Builder

#### Extend ConversationContextBuilder
```python
# backend/app/services/context/memory_aware_context_builder.py

class MemoryAwareContextBuilder(ConversationContextBuilder):
    def __init__(self, config: ConversationContextConfig, db_session: AsyncSession, conversation_id: str, user_id: int):
        super().__init__(config, db_session, conversation_id)
        self.user_id = user_id
        self.memory_service = MemoryService(db_session)
    
    async def build_context_dict(self, latest_user_message: str) -> Dict[str, Any]:
        """Enhanced context building with user memories"""
        
        # Get base context from parent
        context_dict = await super().build_context_dict(latest_user_message)
        
        # Add user memories if enabled
        if await self.is_memory_enabled():
            memory_context = await self.build_memory_context(latest_user_message)
            context_dict["user_memories"] = memory_context
            
        return context_dict
    
    async def build_memory_context(self, user_message: str) -> Dict[str, Any]:
        """Build memory context for current query"""
        
        memory_context = {}
        
        # Always include identity (if available)
        identity_memories = await self.memory_service.get_memories_by_bucket(
            self.user_id, "identity", limit=3
        )
        if identity_memories:
            memory_context["identity"] = [m.content for m in identity_memories]
        
        # Get relevant preferences
        relevant_preferences = await self.memory_service.get_relevant_memories(
            self.user_id, user_message, bucket="preferences", limit=2
        )
        if relevant_preferences:
            memory_context["preferences"] = [m.content for m in relevant_preferences]
        
        # Get active goals (if query seems goal-related)
        if self.is_goal_related_query(user_message):
            active_goals = await self.memory_service.get_memories_by_bucket(
                self.user_id, "goals", status="active", limit=2
            )
            if active_goals:
                memory_context["active_goals"] = [m.content for m in active_goals]
        
        # Get relevant workflows/capabilities if needed
        # ... additional memory retrieval logic
        
        return memory_context
    
    def format_memory_context_for_llm(self, memory_context: Dict[str, Any]) -> str:
        """Format memory context for LLM consumption"""
        
        if not memory_context:
            return ""
            
        sections = []
        
        if "identity" in memory_context:
            sections.append(f"USER IDENTITY: {'; '.join(memory_context['identity'])}")
            
        if "preferences" in memory_context:
            sections.append(f"USER PREFERENCES: {'; '.join(memory_context['preferences'])}")
            
        if "active_goals" in memory_context:
            sections.append(f"ACTIVE GOALS: {'; '.join(memory_context['active_goals'])}")
        
        return "\n".join(sections)
```

### 3.2 Update Context Usage

#### Modify Agent Integration
```python
# backend/aicore/ai_agents/configurable_code_agent.py

# Update the _get_dynamic_instructions method
def _get_dynamic_instructions(self) -> str:
    """Enhanced with memory context"""
    
    # Get base instructions
    base_instructions = self.instruction_builder.build_instructions(context)
    
    # Get memory context if available
    memory_context = ""
    if hasattr(self, 'memory_context') and self.memory_context:
        memory_context = f"""
        
## USER MEMORY CONTEXT
{self.memory_context}

Remember these details about the user when providing responses.
        """
    
    return f"{base_instructions}{memory_context}"
```

---

## Phase 4: Memory Management APIs (Week 7-8)

### 4.1 Memory APIs

#### Create Memory Endpoints
```python
# backend/app/api/memory.py

from fastapi import APIRouter, Depends, HTTPException
from app.services.memory.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])

@router.get("/")
async def get_user_memories(
    bucket: Optional[str] = None,
    limit: int = 20,
    memory_service: MemoryService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Get user memories, optionally filtered by bucket"""
    if bucket:
        memories = await memory_service.get_memories_by_bucket(
            current_user.id, bucket, limit
        )
    else:
        memories = await memory_service.get_all_user_memories(
            current_user.id, limit
        )
    
    return {"memories": memories}

@router.get("/stats")
async def get_memory_stats(
    memory_service: MemoryService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Get user memory statistics"""
    stats = await memory_service.get_user_memory_stats(current_user.id)
    return stats

@router.put("/{memory_id}")
async def update_memory(
    memory_id: str,
    updates: MemoryUpdateRequest,
    memory_service: MemoryService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Update a specific memory"""
    memory = await memory_service.update_memory(memory_id, **updates.dict())
    return {"memory": memory}

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    memory_service: MemoryService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific memory"""
    success = await memory_service.archive_memory(memory_id)
    return {"deleted": success}

@router.post("/extract")
async def trigger_memory_extraction(
    conversation_id: str,
    memory_service: MemoryService = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger memory extraction for a conversation"""
    # Implementation for manual extraction
    pass
```

### 4.2 Memory Settings APIs

#### Memory Preference Management
```python
# backend/app/api/memory_settings.py

@router.get("/preferences")
async def get_memory_preferences(
    current_user: User = Depends(get_current_user)
):
    """Get user's memory preferences by bucket"""
    preferences = await get_user_memory_preferences(current_user.id)
    return {"preferences": preferences}

@router.put("/preferences/{bucket}")
async def update_memory_preferences(
    bucket: str,
    settings: MemoryPreferenceUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update memory preferences for a specific bucket"""
    # Update MemoryPreference for this bucket
    pass

@router.post("/preferences/reset")
async def reset_memory_preferences(
    current_user: User = Depends(get_current_user)
):
    """Reset all memory preferences to defaults"""
    # Reset to default MEMORY_BUCKET_CONFIGS
    pass
```

---

## Phase 5: Memory Maintenance (Week 9-10)

### 5.1 Memory Lifecycle Management

#### Memory Cleanup Service
```python
# backend/app/services/memory/memory_maintenance.py

class MemoryMaintenanceService:
    
    async def cleanup_expired_memories(self):
        """Remove or archive expired memories"""
        # Find memories past their expiration date
        # Archive or delete based on bucket policy
        pass
    
    async def decay_memory_confidence(self):
        """Reduce confidence of old memories"""
        # Apply confidence decay based on age and access patterns
        pass
    
    async def consolidate_duplicate_memories(self, user_id: int):
        """Find and merge similar memories"""
        # Use semantic similarity to find duplicates
        # Merge or mark as duplicates
        pass
    
    async def update_memory_importance(self, user_id: int):
        """Recalculate memory importance based on usage"""
        # Boost frequently accessed memories
        # Reduce importance of never-accessed memories
        pass
```

#### Scheduled Tasks
```python
# backend/app/workers/memory_tasks.py

from celery import Celery

@celery.task
def daily_memory_maintenance():
    """Daily memory cleanup and maintenance"""
    maintenance_service = MemoryMaintenanceService()
    
    # Run cleanup tasks
    await maintenance_service.cleanup_expired_memories()
    await maintenance_service.decay_memory_confidence()

@celery.task
def weekly_memory_consolidation():
    """Weekly memory consolidation"""
    # Run for all users or batch process
    pass
```

### 5.2 Memory Analytics

#### Memory Usage Analytics
```python
# backend/app/services/memory/memory_analytics.py

class MemoryAnalytics:
    
    async def get_memory_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive memory usage statistics"""
        return {
            "total_memories": await self.count_user_memories(user_id),
            "memories_by_bucket": await self.count_memories_by_bucket(user_id),
            "memory_access_patterns": await self.get_access_patterns(user_id),
            "memory_effectiveness": await self.calculate_effectiveness(user_id),
            "storage_usage": await self.calculate_storage_usage(user_id)
        }
    
    async def get_memory_recommendations(self, user_id: int) -> List[str]:
        """Generate recommendations for memory optimization"""
        # Analyze usage patterns and suggest improvements
        pass
```

---

## Phase 6: Frontend Integration (Week 11-12)

### 6.1 Memory Dashboard

#### Basic Memory Management UI
```typescript
// frontend/src/components/memory/MemoryDashboard.tsx

interface MemoryDashboardProps {
  userId: string;
}

export const MemoryDashboard = ({ userId }: MemoryDashboardProps) => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  
  // Component implementation
  return (
    <div className="memory-dashboard">
      <MemoryStats stats={memoryStats} />
      <MemoryBucketFilter 
        selectedBucket={selectedBucket}
        onBucketChange={setSelectedBucket}
      />
      <MemoryList 
        memories={memories}
        onMemoryUpdate={handleMemoryUpdate}
        onMemoryDelete={handleMemoryDelete}
      />
    </div>
  );
};
```

#### Memory Settings Component
```typescript
// frontend/src/components/memory/MemorySettings.tsx

export const MemorySettings = () => {
  const [preferences, setPreferences] = useState<MemoryPreferences>({});
  
  return (
    <div className="memory-settings">
      <div className="memory-toggle">
        <Toggle 
          label="Enable Memory"
          checked={preferences.memory_enabled}
          onChange={handleMemoryToggle}
        />
      </div>
      
      <div className="bucket-settings">
        {MEMORY_BUCKETS.map(bucket => (
          <MemoryBucketSettings 
            key={bucket}
            bucket={bucket}
            preferences={preferences[bucket]}
            onChange={handleBucketPreferenceChange}
          />
        ))}
      </div>
    </div>
  );
};
```

---

## Technical Considerations

### Performance Optimization

#### Database Indexing
```sql
-- Essential indexes for memory queries
CREATE INDEX idx_user_memories_user_bucket ON user_memories(user_id, bucket);
CREATE INDEX idx_user_memories_user_active ON user_memories(user_id, is_active, expires_at);
CREATE INDEX idx_user_memories_last_accessed ON user_memories(last_accessed);
CREATE INDEX idx_user_memories_importance ON user_memories(importance DESC);
```

#### Caching Strategy
```python
# Redis caching for frequently accessed memories
class MemoryCacheService:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    async def cache_user_identity(self, user_id: int, identity_data: Dict):
        """Cache user identity memories for fast access"""
        key = f"memory:identity:{user_id}"
        await self.redis.setex(key, self.cache_ttl, json.dumps(identity_data))
    
    async def get_cached_identity(self, user_id: int) -> Optional[Dict]:
        """Get cached identity data"""
        key = f"memory:identity:{user_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
```

### Security & Privacy

#### Data Encryption
```python
# Encrypt sensitive memory content
from cryptography.fernet import Fernet

class MemoryEncryption:
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt_memory_content(self, content: str) -> str:
        """Encrypt memory content before storage"""
        return self.cipher.encrypt(content.encode()).decode()
    
    def decrypt_memory_content(self, encrypted_content: str) -> str:
        """Decrypt memory content for use"""
        return self.cipher.decrypt(encrypted_content.encode()).decode()
```

#### Privacy Controls
```python
# Memory privacy levels
class MemoryPrivacyLevel(Enum):
    PUBLIC = "public"      # Can be shared/analyzed
    PRIVATE = "private"    # User-only access
    SENSITIVE = "sensitive" # Encrypted storage
    TEMPORARY = "temporary" # Auto-delete after use
```

---

## Testing Strategy

### Unit Tests
```python
# tests/services/memory/test_memory_service.py
class TestMemoryService:
    async def test_store_memory(self):
        # Test memory storage with different buckets
        pass
    
    async def test_memory_expiration(self):
        # Test TTL logic for different buckets
        pass
    
    async def test_memory_retrieval(self):
        # Test relevance-based memory retrieval
        pass
```

### Integration Tests
```python
# tests/integration/test_memory_context.py
class TestMemoryContext:
    async def test_memory_enhanced_context(self):
        # Test memory integration with context building
        pass
    
    async def test_conversation_memory_extraction(self):
        # Test end-to-end memory extraction from conversations
        pass
```

---

## Deployment Checklist

### Database
- [ ] Create and run migrations
- [ ] Add database indexes
- [ ] Set up backup strategy for memory data

### Services  
- [ ] Deploy memory service
- [ ] Configure memory extraction LLM calls
- [ ] Set up memory maintenance tasks

### Configuration
- [ ] Configure memory bucket settings
- [ ] Set up encryption keys
- [ ] Configure cache settings

### Monitoring
- [ ] Memory usage metrics
- [ ] Memory extraction success rates
- [ ] Performance monitoring for memory queries

---

## Success Metrics

### User Experience
- Memory relevance in conversations (user feedback)
- Context improvement (A/B testing)
- Memory management engagement

### Technical Performance  
- Memory extraction accuracy (>80%)
- Memory retrieval latency (<100ms)
- Storage efficiency (optimal bucket distribution)

### Business Impact
- User retention improvement
- Conversation quality scores
- User satisfaction with personalization

---

## Future Enhancements

### Phase 7+ (Advanced Features)
- **Semantic Memory Search**: Vector embeddings for memory content
- **Memory Relationships**: Graph connections between memories
- **Cross-Session Learning**: Learning patterns across conversations
- **Memory Sharing**: Team/workspace shared memories
- **Advanced Analytics**: Memory effectiveness insights
- **Memory Import/Export**: Data portability features

---

## Risk Mitigation

### Privacy Risks
- Explicit user consent for memory storage
- Clear data retention policies
- Easy memory deletion/export

### Technical Risks  
- Gradual rollout with feature flags
- Fallback to non-memory mode if service fails
- Regular memory data backups

### Performance Risks
- Memory query optimization
- Caching for frequently accessed memories
- Asynchronous memory processing

---

This implementation plan provides a comprehensive roadmap for building a sophisticated user memory system while leveraging your existing architecture effectively. 