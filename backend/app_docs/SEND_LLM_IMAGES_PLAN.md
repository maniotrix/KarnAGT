# **Final Implementation Plan: Staging → Commit → LLM Inference**

## **Overview**
Implement the commit phase that converts staging files to OpenAI files during message send, then build LLM context with images.

---

## **Phase 1: Complete Staging Storage Service**

### **File: `backend/app/services/storage/staging_storage.py`**

**Implement missing methods:**

```python
async def commit_staged_files(self, file_ids: List[str], user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Commit staged files to OpenAI Files API and update state
    
    Process:
    1. Validate staging files belong to user
    2. Download from S3 and upload to OpenAI
    3. Update S3 metadata: state="staging" → state="committed"
    4. Create UploadedImage + OpenAIFile database records
    5. Return both s3_key + openai_file_id for message attachments
    """

async def _download_file_from_s3(self, s3_key: str) -> bytes:
    """Download file content from S3 for OpenAI upload"""

async def _update_s3_object_metadata(self, s3_key: str, new_metadata: Dict[str, Any]) -> bool:
    """Update S3 object metadata (already implemented in test file)"""
```

---

## **Phase 2: Create Attachment Service**

### **File: `backend/app/services/chat/attachment_service.py` (NEW)**

```python
"""
Attachment Service for Chat Message Integration
Bridges staging system with chat messages and LLM context
"""

from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage.staging_storage import staging_service
from app.services.storage.openai_storage import openai_storage_service

class AttachmentService:
    """Service for managing message attachments and image commitments"""
    
    async def commit_and_build_attachments(
        self, 
        staging_file_ids: List[str], 
        user_id: str, 
        db: AsyncSession
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Convert staging files to committed files and build message attachments
        
        Returns:
            (message_attachments, openai_file_ids)
        """
        
    async def get_openai_file_ids_from_attachments(
        self, 
        attachments: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract OpenAI file IDs from message attachments for context building"""
        
    async def validate_staging_files(
        self, 
        staging_file_ids: List[str], 
        user_id: str
    ) -> Dict[str, Any]:
        """Validate that staging files exist and belong to user"""
```

---

## **Phase 3: Extend Chat Schemas**

### **File: `backend/app/models/schemas/chat_schemas.py`**

**Add to existing `MessageCreate` class:**

```python
class MessageCreate(BaseSchema):
    content: str = Field(..., min_length=1, max_length=32000)
    role: MessageRole = Field(MessageRole.USER)
    parent_message_id: Optional[int] = Field(None)
    attachments: Optional[List[Dict[str, Any]]] = Field(None)  # EXISTS
    status: Optional[str] = Field("completed")  # EXISTS
    
    # ADD THIS FIELD
    staging_file_ids: Optional[List[str]] = Field(
        None, 
        description="List of staging file IDs to commit with this message"
    )
```

---

## **Phase 4: Extend Context Builder**

### **File: `backend/app/services/context/conversation_context_builder.py`**

**Modify existing `build_context` method:**

```python
async def build_context(
    self, 
    latest_user_message: str, 
    openai_file_ids: Optional[List[str]] = None  # ADD THIS PARAMETER
) -> List[Dict[str, Any]]:
    """
    Build conversation context with optional image support
    """
    # ... existing logic for conversation history ...
    
    # MODIFY: Build final user message with images
    if openai_file_ids and len(openai_file_ids) > 0:
        # Multimodal content
        content_parts = [{"type": "text", "text": latest_user_message}]
        
        for file_id in openai_file_ids:
            content_parts.append({
                "type": "image_file", 
                "image_file": {"file_id": file_id}
            })
        
        latest_message = {
            "role": "user",
            "content": content_parts
        }
    else:
        # Text-only content
        latest_message = {
            "role": "user", 
            "content": latest_user_message
        }
    
    context_messages.append(latest_message)
    return context_messages
```

**Update the helper function:**

```python
async def get_context_for_conversation(
    conversation_id: str, 
    db_session: AsyncSession, 
    latest_user_message: str,
    openai_file_ids: Optional[List[str]] = None  # ADD THIS
) -> List[Dict[str, Any]]:  # CHANGE RETURN TYPE
    """Get context for conversation with optional images"""
    
    builder = ConversationContextBuilder(
        get_default_conversation_context_config(), 
        db_session, 
        conversation_id
    )
    
    return await builder.build_context(latest_user_message, openai_file_ids)
```

---

## **Phase 5: Extend Chat Service**

### **File: `backend/app/services/chat/chat_service.py`**

**Modify existing methods to support images:**

```python
async def send_message(
    self,
    conversation_id: str,
    content: str,
    message_type: str = "text",
    model: Optional[str] = None,
    staging_file_ids: Optional[List[str]] = None  # ADD THIS
) -> MessageResponse:
    """Send a message with optional image attachments"""
    
    # ADD: Process staging files if provided
    message_attachments = []
    openai_file_ids = []
    
    if staging_file_ids:
        from app.services.chat.attachment_service import AttachmentService
        attachment_service = AttachmentService()
        
        message_attachments, openai_file_ids = await attachment_service.commit_and_build_attachments(
            staging_file_ids, self.user_id, self.db
        )
    
    # MODIFY: Create user message with attachments
    user_message_data = MessageCreate(
        content=content,
        role="user",
        attachments=message_attachments,  # Store s3_key + openai_file_id pairs
        parent_message_id=None,
        status="completed"
    )
    
    # ... existing message creation logic ...
    
    # MODIFY: Build context with images
    llm_context = await get_context_for_conversation(
        conversation_id, 
        self.db, 
        content,
        openai_file_ids=openai_file_ids  # Pass OpenAI file IDs for LLM
    )
    
    # MODIFY: Send to LLM with multimodal context
    ai_response_data = await assistant_client.send_message(
        llm_context,  # Now contains images
        message_type=message_type,
        metadata={
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "model": model_name,
            "has_images": len(openai_file_ids) > 0,
            "image_count": len(openai_file_ids)
        }
    )
    
    # ... rest of existing logic unchanged ...
```

**Apply same pattern to streaming methods:**

```python
async def send_message_streaming(
    self,
    conversation_id: str,
    content: str,
    streaming_callback: Callable[[str], None],
    message_type: str = "text",
    model: Optional[str] = None,
    staging_file_ids: Optional[List[str]] = None  # ADD THIS
) -> MessageResponse:
    # Same pattern as send_message
```

---

## **Phase 6: Extend Chat API Endpoints**

### **File: `backend/app/api/v1/endpoints/chat.py`**

**Modify existing endpoints to extract staging_file_ids:**

```python
@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,  # Already supports staging_file_ids
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Send a message with optional image attachments"""
    
    try:
        chat_service = ChatService(db, current_user)
        
        # Extract staging_file_ids from message_data
        staging_file_ids = getattr(message_data, 'staging_file_ids', None)
        
        response = await chat_service.send_message(
            conversation_id=conversation_id,
            content=message_data.content,
            message_type="text",
            staging_file_ids=staging_file_ids  # Pass to service
        )
        
        return response
        
    except Exception as e:
        # ... existing error handling ...
```

**Apply same pattern to streaming endpoint:**

```python
@router.post("/conversations/{conversation_id}/stream")
async def stream_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    # Same pattern - extract staging_file_ids and pass to streaming service
```

---

## **Phase 7: Fix Linter Errors**

### **File: `backend/app/services/chat/chat_service.py`**

**Fix MessageCreate instantiation:**

```python
# Current (causes linter errors):
user_message_data = MessageCreate(
    content=content,
    role="user"
)

# Fixed (provide all required fields):
user_message_data = MessageCreate(
    content=content,
    role="user",
    parent_message_id=None,
    attachments=message_attachments,  # Now populated
    status="completed"
)
```

---

## **Implementation Order**

### **Step 1: Complete Staging Service** 
- Implement `commit_staged_files()` method
- Add helper methods for S3 download and metadata update

### **Step 2: Create Attachment Service**
- New service to bridge staging → chat messages
- Handles validation, commitment, and attachment building

### **Step 3: Extend Context Builder**
- Add `openai_file_ids` parameter to build multimodal context
- Update helper function signature

### **Step 4: Update Chat Schemas**
- Add `staging_file_ids` field to `MessageCreate`

### **Step 5: Extend Chat Service**
- Modify `send_message()` and `send_message_streaming()` methods
- Add attachment processing logic

### **Step 6: Update Chat API**
- Extract `staging_file_ids` from request and pass to service

### **Step 7: Fix Linter Errors**
- Provide all required fields in schema instantiations

---

## **Testing Strategy**

### **Unit Tests**
1. Test `commit_staged_files()` with valid/invalid staging files
2. Test `AttachmentService` commitment and validation
3. Test context building with images

### **Integration Tests**
1. End-to-end: staging upload → message send → LLM response
2. Test with multiple images
3. Test mixed text + image messages
4. Test streaming with images

### **Expected Flow After Implementation**

```
1. Frontend: Upload images → GET staging_file_ids
2. Frontend: Send message with staging_file_ids
3. Backend: Commit staging files → get openai_file_ids  
4. Backend: Build multimodal context with images
5. Backend: Send to LLM (GPT-4 Vision)
6. Backend: Return AI response about images
7. Backend: Store message with attachments [s3_key + openai_file_id]
```

**Result**: Full image support in chat with proper state management, cost optimization, and database tracking.