"""Knowledge file model for uploaded files and documents"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # File metadata
    original_filename = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=False)  # Sanitized filename
    file_path = Column(String(1000), nullable=False)  # Storage path
    file_size_bytes = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)  # pdf, docx, txt, md, etc.
    mime_type = Column(String(200), nullable=False)
    
    # Content metadata
    title = Column(String(500), nullable=True)  # Extracted or user-provided title
    description = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    language = Column(String(10), default="en")
    
    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    processing_progress = Column(Float, default=0.0)  # 0.0-1.0
    
    # Content extraction
    extracted_text = Column(Text, nullable=True)
    text_length = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    page_count = Column(Integer, nullable=True)
    
    # Chunking and embedding
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100), nullable=True)
    embedding_dimensions = Column(Integer, nullable=True)
    embeddings_generated = Column(Boolean, default=False)
    embeddings_stored = Column(Boolean, default=False)
    
    # Search and indexing
    indexed_in_vector_db = Column(Boolean, default=False)
    vector_collection_id = Column(String(100), nullable=True)
    search_enabled = Column(Boolean, default=True)
    
    # Quality and validation
    quality_score = Column(Float, nullable=True)  # 0.0-1.0
    content_type = Column(String(100), nullable=True)  # document, code, data, image, etc.
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(JSON, default=list)
    
    # Access and permissions
    is_public = Column(Boolean, default=False)
    access_level = Column(String(50), default="private")  # private, team, public
    share_token = Column(String(100), nullable=True, unique=True)
    
    # Organization and tagging
    folder = Column(String(200), default="/")
    tags = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    topics = Column(JSON, default=list)
    
    # Usage statistics
    view_count = Column(Integer, default=0)
    search_count = Column(Integer, default=0)
    reference_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Version control
    version = Column(Integer, default=1)
    parent_file_id = Column(Integer, ForeignKey("knowledge_files.id"), nullable=True)
    is_latest_version = Column(Boolean, default=True)
    
    # Content summary
    summary = Column(Text, nullable=True)  # AI-generated summary
    key_points = Column(JSON, default=list)  # Extracted key points
    entities = Column(JSON, default=list)   # Named entities found
    
    # Extra metadata
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="knowledge_files")
    parent_file = relationship("KnowledgeFile", remote_side=[id], backref="child_versions")
    
    def __repr__(self):
        return f"<KnowledgeFile(id={self.id}, filename='{self.filename}', status='{self.processing_status}')>"
    
    @property
    def is_processing(self) -> bool:
        """Check if file is currently being processed"""
        return self.processing_status in ["pending", "processing"]
    
    @property
    def is_processed(self) -> bool:
        """Check if file has been successfully processed"""
        return self.processing_status == "completed"
    
    @property
    def has_failed(self) -> bool:
        """Check if file processing failed"""
        return self.processing_status == "failed"
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)
    
    @property
    def processing_duration_seconds(self) -> float:
        """Get processing duration in seconds"""
        if not self.processing_started_at or not self.processing_completed_at:
            return 0.0
        delta = self.processing_completed_at - self.processing_started_at
        return delta.total_seconds()
    
    @property
    def is_recent(self) -> bool:
        """Check if file was uploaded recently (last 7 days)"""
        from datetime import datetime, timedelta
        return self.created_at > (datetime.utcnow() - timedelta(days=7))
    
    @property
    def file_extension(self) -> str:
        """Get file extension"""
        return self.original_filename.split('.')[-1].lower() if '.' in self.original_filename else ""
    
    def generate_share_token(self) -> str:
        """Generate a unique share token for public access"""
        if not self.share_token:
            self.share_token = str(uuid.uuid4())
        return self.share_token
    
    def add_tag(self, tag: str):
        """Add a tag to the file"""
        if not self.tags:
            self.tags = []
        if tag.lower() not in [t.lower() for t in self.tags]:
            self.tags.append(tag)
    
    def add_category(self, category: str):
        """Add a category to the file"""
        if not self.categories:
            self.categories = []
        if category.lower() not in [c.lower() for c in self.categories]:
            self.categories.append(category)
    
    def add_topic(self, topic: str):
        """Add a topic to the file"""
        if not self.topics:
            self.topics = []
        if topic.lower() not in [t.lower() for t in self.topics]:
            self.topics.append(topic)
    
    def add_entity(self, entity_type: str, entity_value: str, confidence: float = 1.0):
        """Add a named entity to the file"""
        if not self.entities:
            self.entities = []
        entity = {
            "type": entity_type,
            "value": entity_value,
            "confidence": confidence
        }
        self.entities.append(entity)
    
    def set_processing_status(self, status: str, error: str = None):
        """Update processing status"""
        self.processing_status = status
        if status == "processing" and not self.processing_started_at:
            self.processing_started_at = func.now()
        elif status in ["completed", "failed"]:
            self.processing_completed_at = func.now()
        if error:
            self.processing_error = error
    
    def update_content_stats(self, text: str):
        """Update content statistics from extracted text"""
        self.extracted_text = text
        self.text_length = len(text)
        self.word_count = len(text.split()) if text else 0
    
    def increment_view_count(self):
        """Increment view count and update last accessed time"""
        self.view_count += 1
        self.last_accessed_at = func.now()
    
    def increment_search_count(self):
        """Increment search count"""
        self.search_count += 1
    
    def increment_reference_count(self):
        """Increment reference count"""
        self.reference_count += 1 