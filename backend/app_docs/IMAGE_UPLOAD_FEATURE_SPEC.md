# Image Upload Feature Implementation Specification

## Overview
This document outlines the complete implementation plan for adding image support to the ChatGPT Clone backend, enabling users to upload and send images in chat conversations with LLM vision capabilities.

## Architecture Decision

### Storage Strategy: Dual Storage Approach
- **Primary Storage**: MinIO (development) / S3 (production) for reliable image serving
- **LLM Integration**: OpenAI Files API for vision inference
- **Message Storage**: Leverage existing `message.attachments` JSON field

### Key Design Principles
1. **S3 Compatibility**: Seamless transition from MinIO to AWS S3
2. **Message-Centric**: Images stored as message attachments, not separate entities
3. **Separation of Concerns**: Display URLs ≠ LLM file IDs
4. **Production Ready**: Industry standard storage abstraction pattern

## Technical Architecture

### File Flow Diagram
```
User Upload → MinIO/S3 Storage → OpenAI Files API → Message Attachments → LLM Context → Response
     ↓              ↓                    ↓                ↓               ↓            ↓
   Validate    Generate URLs     Get file_id      Save metadata    Vision API    Store result
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **FileService** | Handle upload, validation, storage operations |
| **ChatService** | Integrate images into conversation flow |
| **ContextBuilder** | Transform attachments into LLM-compatible format |
| **MessageService** | Store/retrieve message attachment metadata |

## Docker Configuration

### MinIO Service Addition
```yaml
# Add to existing docker-compose.yml
services:
  minio:
    image: minio/minio:latest
    container_name: chatgpt-minio
    ports:
      - "9000:9000"    # API
      - "9001:9001"    # Web Console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
      MINIO_DEFAULT_BUCKETS: minio-files
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  createbuckets:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      /usr/bin/mc alias set myminio http://minio:9000 minioadmin minioadmin123;
      /usr/bin/mc mb myminio/minio-files --ignore-existing;
      /usr/bin/mc policy set public myminio/minio-files;
      exit 0;
      "

volumes:
  minio_data:
    driver: local
```

## Configuration Updates

### Environment Configuration
```python
# backend/app/core/config.py additions

from enum import Enum

class StorageBackend(str, Enum):
    MINIO = "minio"
    S3 = "s3"

class Settings(BaseSettings):
    # ... existing settings
    
    # Image Storage Configuration
    STORAGE_BACKEND: StorageBackend = StorageBackend.MINIO
    
    # File Upload Settings
    MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20MB (OpenAI limit)
    ALLOWED_IMAGE_TYPES: str = ".png,.jpg,.jpeg,.gif,.webp"
    IMAGE_QUALITY: int = 85  # JPEG quality for optimization
    THUMBNAIL_SIZE: tuple = (300, 300)  # Max thumbnail dimensions
    
    # S3/MinIO Configuration
    S3_BUCKET_NAME: str = "minio-files"
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"  # MinIO endpoint
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin123"
    
    # OpenAI Files API
    OPENAI_FILES_EXPIRE_HOURS: int = 24
    OPENAI_MAX_FILE_SIZE: int = 20 * 1024 * 1024
    
    # Image serving
    IMAGE_BASE_URL: str = "http://localhost:8000/api/images"
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600  # 1 hour
```

### Environment Variables (.env)
```bash
# Image Storage
STORAGE_BACKEND=minio
S3_BUCKET_NAME=minio-files
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin123

# Image Processing
MAX_IMAGE_SIZE=20971520
ALLOWED_IMAGE_TYPES=.png,.jpg,.jpeg,.gif,.webp
```

## Database Schema

### Message Model Enhancement
**No schema changes needed** - leveraging existing `attachments` JSON field:

```python
# message.attachments structure for images:
[
  {
    "type": "image",
    "file_id": "img_7f9e2b4c",           # Our internal ID
    "openai_file_id": "file-abc123xyz",  # OpenAI Files API ID
    "filename": "diagram.png",
    "original_filename": "my_diagram.png",
    "content_type": "image/png",
    "size": 1024000,
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "urls": {
      "display": "http://localhost:8000/api/images/img_7f9e2b4c",
      "thumbnail": "http://localhost:8000/api/images/img_7f9e2b4c/thumbnail"
    },
    "s3_key": "images/2024/01/15/img_7f9e2b4c.png",
    "openai_expires_at": "2024-01-16T12:00:00Z",
    "detail_level": "high",  # For OpenAI Vision API
    "uploaded_at": "2024-01-15T12:00:00Z"
  }
]
```

## API Specifications

### Image Upload Endpoint
```python
# backend/app/api/v1/endpoints/images.py

@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_verified_user)
) -> ImageUploadResponse:
    """
    Upload image for chat usage
    
    - **file**: Image file (PNG, JPEG, GIF, WebP)
    - **conversation_id**: Optional conversation context
    - Returns: Image metadata including display URLs and OpenAI file ID
    """
```

### Image Serving Endpoints
```python
@router.get("/{image_id}")
async def serve_image(image_id: str):
    """Serve full-size image"""

@router.get("/{image_id}/thumbnail")
async def serve_thumbnail(image_id: str):
    """Serve optimized thumbnail"""

@router.get("/{image_id}/metadata")
async def get_image_metadata(image_id: str):
    """Get image metadata without file content"""
```

### Enhanced Message Endpoints
```python
# backend/app/api/v1/endpoints/chat.py enhancements

class MessageCreateEnhanced(BaseSchema):
    content: str = Field(..., min_length=1, max_length=32000)
    role: MessageRole = Field(MessageRole.USER)
    image_ids: Optional[List[str]] = Field(None, max_items=10, description="Uploaded image IDs")
    # Keep existing attachments for backward compatibility
    attachments: Optional[List[Dict[str, Any]]] = None

@router.post("/conversations/{conversation_id}/messages")
async def send_message_with_images(
    conversation_id: str,
    message_data: MessageCreateEnhanced,
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db)
):
    """Send message with optional image attachments"""
```

## Service Layer Implementation

### File Storage Service
```python
# backend/app/services/files/storage_service.py

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import boto3
from PIL import Image
import io

class StorageBackend(ABC):
    @abstractmethod
    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        """Upload file and return URL"""
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    async def generate_presigned_url(self, key: str, expire_seconds: int) -> str:
        """Generate presigned URL for secure access"""
        pass

class S3StorageBackend(StorageBackend):
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION
        )
    
    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        self.s3_client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=file_data,
            ContentType=content_type
        )
        return f"{settings.IMAGE_BASE_URL}/{key.split('/')[-1]}"

class ImageService:
    def __init__(self):
        self.storage = S3StorageBackend()
        self.openai_client = OpenAI()
    
    async def process_and_upload_image(
        self, 
        file: UploadFile, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Complete image processing pipeline
        """
        # 1. Validate image
        await self._validate_image(file)
        
        # 2. Generate unique ID and S3 key
        image_id = self._generate_image_id()
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"images/{date_prefix}/{image_id}.{self._get_file_extension(file.filename)}"
        
        # 3. Process image (resize if needed, optimize)
        processed_image_data, dimensions = await self._process_image(file)
        
        # 4. Upload to our storage (MinIO/S3)
        display_url = await self.storage.upload_file(
            processed_image_data, 
            s3_key, 
            file.content_type
        )
        
        # 5. Create thumbnail
        thumbnail_data = await self._create_thumbnail(processed_image_data)
        thumbnail_key = f"thumbnails/{date_prefix}/{image_id}_thumb.jpg"
        thumbnail_url = await self.storage.upload_file(
            thumbnail_data, 
            thumbnail_key, 
            "image/jpeg"
        )
        
        # 6. Upload to OpenAI Files API
        file.file.seek(0)  # Reset file pointer
        openai_file = self.openai_client.files.create(
            file=file.file,
            purpose="vision"
        )
        
        # 7. Return complete metadata
        return {
            "file_id": image_id,
            "openai_file_id": openai_file.id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(processed_image_data),
            "dimensions": dimensions,
            "s3_key": s3_key,
            "urls": {
                "display": display_url,
                "thumbnail": thumbnail_url
            },
            "openai_expires_at": datetime.now() + timedelta(hours=24),
            "uploaded_at": datetime.now().isoformat()
        }
    
    async def _validate_image(self, file: UploadFile):
        """Validate image file"""
        if file.size > settings.MAX_IMAGE_SIZE:
            raise HTTPException(400, f"File too large. Max size: {settings.MAX_IMAGE_SIZE} bytes")
        
        if not any(file.filename.lower().endswith(ext) for ext in settings.get_allowed_image_types()):
            raise HTTPException(400, f"Invalid file type. Allowed: {settings.ALLOWED_IMAGE_TYPES}")
        
        # Validate actual image content
        try:
            file.file.seek(0)
            with Image.open(file.file) as img:
                img.verify()
        except Exception:
            raise HTTPException(400, "Invalid image file")
        finally:
            file.file.seek(0)
```

### Enhanced Chat Service
```python
# backend/app/services/chat/chat_service.py additions

class ChatService:
    # ... existing methods
    
    async def send_message_with_images(
        self,
        conversation_id: str,
        content: str,
        image_ids: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> MessageResponse:
        """
        Send message with image attachments
        """
        logger.info(f"Sending message with {len(image_ids or [])} images to conversation {conversation_id}")
        
        # 1. Process image attachments
        attachments = []
        if image_ids:
            image_service = ImageService()
            for image_id in image_ids:
                # Retrieve image metadata (from your storage/cache)
                image_metadata = await image_service.get_image_metadata(image_id)
                if image_metadata:
                    attachments.append({
                        "type": "image",
                        **image_metadata
                    })
        
        # 2. Save user message with attachments
        user_message = await self.message_service.create_message(
            conversation_id=conversation_id,
            content=content,
            role="user",
            attachments=attachments
        )
        
        # 3. Build context with images
        context = await self._build_multimodal_context(conversation_id, content, attachments)
        
        # 4. Generate AI response
        assistant_client = self._get_assistant_client_with_memory(conversation_id)
        
        try:
            response = await assistant_client.create_response(
                messages=context,
                model=model or "gpt-4o-mini-2024-07-18"
            )
            
            # 5. Save AI response
            ai_message = await self.message_service.create_message(
                conversation_id=conversation_id,
                content=response.content,
                role="assistant",
                model_name=response.model,
                total_tokens=response.usage.total_tokens,
                cost_usd=response.cost_usd
            )
            
            return MessageResponse.from_orm(ai_message)
            
        except Exception as e:
            logger.error(f"Error generating AI response with images: {e}")
            raise MessageProcessingException(f"Failed to process message with images: {str(e)}")
    
    async def _build_multimodal_context(
        self, 
        conversation_id: str, 
        latest_message: str, 
        attachments: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Build conversation context including images
        """
        # Get base conversation context
        context_builder = ConversationContextBuilder(
            config=get_default_conversation_context_config(),
            db_session=self.db,
            conversation_id=conversation_id
        )
        
        # Build text-only context first
        base_context = await context_builder.build_context(latest_message)
        
        # Enhance last message with images if present
        if attachments:
            image_attachments = [att for att in attachments if att.get("type") == "image"]
            
            if image_attachments:
                # Transform last message to multimodal format
                last_message = base_context[-1]  # Should be user message
                
                # Convert to multimodal content
                multimodal_content = [
                    {"type": "text", "text": last_message["content"]}
                ]
                
                # Add images with OpenAI file IDs
                for img_att in image_attachments:
                    multimodal_content.append({
                        "type": "image",
                        "file_id": img_att["openai_file_id"]
                    })
                
                # Replace last message content
                base_context[-1]["content"] = multimodal_content
        
        return base_context
```

### Enhanced Context Builder
```python
# backend/app/services/context/conversation_context_builder.py additions

class ConversationContextBuilder:
    # ... existing methods
    
    async def build_context_with_images(
        self, 
        latest_user_message: str,
        image_attachments: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build context optimized for vision models
        """
        # Start with base context
        context = await self.build_context(latest_user_message)
        
        # Apply image-specific optimizations
        if image_attachments:
            context = await self._optimize_context_for_images(context, image_attachments)
        
        return context
    
    async def _optimize_context_for_images(
        self, 
        context: List[Dict], 
        image_attachments: List[Dict]
    ) -> List[Dict]:
        """
        Optimize context window for image token usage
        """
        # Calculate image token consumption
        estimated_image_tokens = len(image_attachments) * 765  # Average vision tokens
        
        # If images consume too many tokens, be more aggressive with text summarization
        if estimated_image_tokens > 2000:
            # Reduce text context, prioritize recent messages
            context = await self._compress_text_context(context, target_reduction=estimated_image_tokens)
        
        return context
    
    async def _get_message_attachments(self, message_id: int) -> List[Dict]:
        """
        Retrieve attachments for a specific message
        """
        result = await self.db_session.execute(
            select(Message.attachments).where(Message.id == message_id)
        )
        row = result.first()
        return row[0] if row and row[0] else []
```

## Frontend Integration Points

### API Response Format
```typescript
// TypeScript interfaces for frontend
interface ImageAttachment {
  type: 'image';
  file_id: string;
  filename: string;
  content_type: string;
  size: number;
  dimensions: {
    width: number;
    height: number;
  };
  urls: {
    display: string;
    thumbnail: string;
  };
  uploaded_at: string;
}

interface MessageWithImages {
  id: number;
  message_id: string;
  content: string;
  role: 'user' | 'assistant';
  attachments: ImageAttachment[];
  created_at: string;
}
```

### Upload Flow Integration
```javascript
// Frontend upload flow example
const uploadImages = async (files) => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await fetch('/api/images/upload', {
    method: 'POST',
    body: formData,
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json(); // Returns image metadata
};

const sendMessageWithImages = async (content, imageIds) => {
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      content,
      image_ids: imageIds
    })
  });
  
  return response.json();
};
```

## Error Handling & Security

### Validation Rules
```python
class ImageValidationRules:
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
    MAX_DIMENSION = 4096  # pixels
    MAX_IMAGES_PER_MESSAGE = 10
    
    @staticmethod
    async def validate_image_upload(file: UploadFile, user: User):
        # File size validation
        if file.size > ImageValidationRules.MAX_FILE_SIZE:
            raise HTTPException(413, "File too large")
        
        # Content type validation
        if file.content_type not in ImageValidationRules.ALLOWED_TYPES:
            raise HTTPException(415, "Unsupported file type")
        
        # Image content validation
        try:
            with Image.open(file.file) as img:
                width, height = img.size
                if width > ImageValidationRules.MAX_DIMENSION or height > ImageValidationRules.MAX_DIMENSION:
                    raise HTTPException(413, f"Image dimensions too large. Max: {ImageValidationRules.MAX_DIMENSION}px")
        except Exception as e:
            raise HTTPException(400, "Invalid image file")
        finally:
            file.file.seek(0)
        
        # User quota validation
        quota_service = QuotaService()
        if not await quota_service.check_image_quota(user.id):
            raise HTTPException(429, "Image upload quota exceeded")
```

### Security Measures
```python
class ImageSecurityService:
    async def scan_image_content(self, image_data: bytes) -> bool:
        """
        Content moderation for uploaded images
        """
        # Implement content scanning (e.g., Azure Content Moderator, AWS Rekognition)
        # For now, basic checks
        return True
    
    async def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize uploaded filename
        """
        import re
        # Remove potentially dangerous characters
        safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
        return safe_filename[:100]  # Limit length
    
    async def verify_image_integrity(self, file_data: bytes) -> bool:
        """
        Verify image is not corrupted and contains valid image data
        """
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                img.verify()
            return True
        except:
            return False
```

## Cost Management

### Vision API Cost Tracking
```python
class VisionCostCalculator:
    # OpenAI Vision API pricing
    TOKEN_COSTS = {
        "gpt-4o-mini": {
            "input": 0.00015,  # per 1K tokens
            "output": 0.0006
        }
    }
    
    def estimate_image_tokens(self, dimensions: Tuple[int, int], detail: str = "high") -> int:
        """
        Estimate tokens for image based on OpenAI's formula
        """
        width, height = dimensions
        
        if detail == "low":
            return 85
        
        # High detail calculation
        # Scale image to fit 2048x2048, then count 512x512 tiles
        scale = min(2048 / width, 2048 / height, 1)
        scaled_width = int(width * scale)
        scaled_height = int(height * scale)
        
        tiles_width = (scaled_width + 511) // 512
        tiles_height = (scaled_height + 511) // 512
        
        return 85 + (170 * tiles_width * tiles_height)
    
    def calculate_vision_cost(self, image_tokens: int, model: str = "gpt-4o-mini") -> float:
        """
        Calculate cost for vision API usage
        """
        cost_per_1k = self.TOKEN_COSTS[model]["input"]
        return (image_tokens / 1000) * cost_per_1k
```

## Testing Strategy

### Unit Tests
```python
# backend/tests/test_image_service.py
import pytest
from app.services.files.image_service import ImageService

class TestImageService:
    async def test_image_upload_validation(self):
        """Test image validation logic"""
        pass
    
    async def test_image_processing_pipeline(self):
        """Test complete image processing flow"""
        pass
    
    async def test_openai_integration(self):
        """Test OpenAI Files API integration"""
        pass
    
    async def test_s3_storage_backend(self):
        """Test S3/MinIO storage operations"""
        pass

# backend/tests/test_multimodal_chat.py
class TestMultimodalChat:
    async def test_send_message_with_single_image(self):
        """Test sending message with one image"""
        pass
    
    async def test_send_message_with_multiple_images(self):
        """Test sending message with multiple images"""
        pass
    
    async def test_context_building_with_images(self):
        """Test conversation context including images"""
        pass
```

### Integration Tests
```python
# backend/tests/test_image_api_integration.py
async def test_complete_image_upload_flow():
    """
    Test complete flow:
    1. Upload image
    2. Send message with image
    3. Receive AI response
    4. Verify attachments stored correctly
    """
    pass

async def test_image_serving_endpoints():
    """Test image serving and thumbnail generation"""
    pass
```

## Production Deployment Considerations

### Environment-Specific Configurations

#### Development (MinIO)
```bash
STORAGE_BACKEND=minio
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin123
```

#### Production (AWS S3)
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=  # Empty for AWS S3
S3_ACCESS_KEY_ID=AKIA...
S3_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=production-minio-files
```

### Monitoring & Metrics
```python
class ImageMetrics:
    """Metrics collection for image feature"""
    
    @staticmethod
    async def track_image_upload(user_id: str, file_size: int, processing_time: float):
        """Track image upload metrics"""
        pass
    
    @staticmethod
    async def track_vision_api_usage(tokens_used: int, cost: float):
        """Track OpenAI Vision API usage"""
        pass
    
    @staticmethod
    async def track_storage_usage(bucket_name: str, total_size: int):
        """Track storage utilization"""
        pass
```

## Implementation Timeline

### Phase 1: Foundation (Week 1)
- [ ] Docker MinIO setup
- [ ] Storage service abstraction
- [ ] Basic image upload endpoint
- [ ] Image validation and processing

### Phase 2: Integration (Week 2)
- [ ] Message attachment enhancement
- [ ] OpenAI Files API integration
- [ ] Context builder modifications
- [ ] Chat service integration

### Phase 3: API Enhancement (Week 3)
- [ ] Complete API endpoints
- [ ] Error handling and security
- [ ] Cost tracking integration
- [ ] Testing implementation

### Phase 4: Production Readiness (Week 4)
- [ ] S3 compatibility testing
- [ ] Performance optimization
- [ ] Monitoring and metrics
- [ ] Documentation completion

## Success Criteria

### Functional Requirements
- [ ] Users can upload images (PNG, JPEG, GIF, WebP)
- [ ] Images appear in chat messages
- [ ] AI responds to image content using vision capabilities
- [ ] Multiple images per message supported
- [ ] Images persist across conversation sessions

### Performance Requirements
- [ ] Image upload completes within 10 seconds
- [ ] Image serving has <2 second response time
- [ ] Context building with images <5 seconds
- [ ] Storage backend switchable without code changes

### Security Requirements
- [ ] File type validation prevents malicious uploads
- [ ] User can only access their own images
- [ ] Uploaded files scanned for content policy violations
- [ ] Secure presigned URLs for image access

## Maintenance & Operations

### Cleanup Jobs
```python
class ImageCleanupService:
    async def cleanup_expired_openai_files(self):
        """Remove references to expired OpenAI files"""
        pass
    
    async def cleanup_orphaned_images(self):
        """Remove images not referenced by any message"""
        pass
    
    async def optimize_storage_costs(self):
        """Move old images to cheaper storage tiers"""
        pass
```

### Monitoring Alerts
- Storage utilization > 80%
- Vision API costs exceed daily budget
- Image processing failures > 5%
- Average image upload time > 10 seconds

---

## Conclusion

This specification provides a complete, production-ready implementation plan for image upload functionality in the ChatGPT Clone backend. The design emphasizes:

1. **Industry Standards**: S3-compatible storage with seamless production migration
2. **Scalability**: Efficient storage patterns and cost optimization
3. **User Experience**: Fast uploads, reliable serving, rich multimodal conversations
4. **Maintainability**: Clean abstraction layers and comprehensive testing

The implementation leverages existing infrastructure while adding sophisticated image handling capabilities that integrate seamlessly with the current chat architecture. 