"""
Database model for tracking uploaded image files and ownership
This is the industry-standard approach for file access control
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, BigInteger, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class UploadedImage(Base):
    """
    Database table to track image file ownership and metadata
    
    This follows security best practices by:
    1. Storing file ownership in database (not in file paths)
    2. Enabling proper access control validation
    3. Supporting file metadata and audit trails
    """
    __tablename__ = "uploaded_images"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # File identification
    file_id = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "img_7f9e2b4c"
    filename = Column(String(500), nullable=False)  # Original filename
    s3_key = Column(String(1000), nullable=False, unique=True)  # S3 storage path
    
    # Ownership and access control
    user_id = Column(String(255), nullable=False, index=True)  # Owner of the file
    
    # File metadata
    content_type = Column(String(100), nullable=False)  # e.g., "image/png"
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accessed_at = Column(DateTime(timezone=True), nullable=True)  # Last access time
    
    # Optional metadata
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string for search/categorization
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_user_uploaded', 'user_id', 'uploaded_at'),
        Index('idx_file_id_user', 'file_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<UploadedImage(file_id='{self.file_id}', user_id='{self.user_id}', filename='{self.filename}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "description": self.description,
            "tags": self.tags
        } 