"""
Database model for tracking OpenAI Files API uploads
Maintains list of all files uploaded to OpenAI for management and cleanup
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, BigInteger, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class OpenAIFile(Base):
    """
    Database table to track OpenAI Files API uploads
    
    Enables:
    1. List all files uploaded to OpenAI
    2. Track file ownership and metadata
    3. Bulk deletion when needed
    4. Cost tracking and usage monitoring
    """
    __tablename__ = "openai_files"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # OpenAI file identification
    openai_file_id = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "file-abc123"
    
    # File metadata
    filename = Column(String(500), nullable=False)  # Original filename
    purpose = Column(String(50), nullable=False, index=True)  # "vision", "assistants", "fine-tune"
    
    # Ownership
    user_id = Column(String(255), nullable=False, index=True)  # Owner of the file
    
    # File details
    file_size_bytes = Column(BigInteger, nullable=False)  # Size in bytes
    status = Column(String(50), nullable=False, default="uploaded")  # "uploaded", "processed", "error"
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # Last time used in chat
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_user_uploaded_openai', 'user_id', 'uploaded_at'),
        Index('idx_purpose_status', 'purpose', 'status'),
        Index('idx_openai_file_user', 'openai_file_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<OpenAIFile(openai_file_id='{self.openai_file_id}', user_id='{self.user_id}', filename='{self.filename}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "openai_file_id": self.openai_file_id,
            "filename": self.filename,
            "purpose": self.purpose,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at is not None else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at is not None else None,
            "description": self.description,
            "tags": self.tags
        }
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return float(self.file_size_bytes) / (1024 * 1024) 