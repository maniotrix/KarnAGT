"""Knowledge File model for tracking document processing and vector index state."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class KnowledgeFile(Base):
    """
    Tracks individual files processed through the RAG system.
    Links to LlamaIndex document IDs for proper state management.
    """
    __tablename__ = "knowledge_files"

    # Primary identification
    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # File information
    file_id = Column(String(100), unique=True, index=True, nullable=False)  # Generated unique ID
    file_path = Column(String(500), nullable=False)  # S3 key or file path
    file_name = Column(String(255), nullable=False)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    content_type = Column(String(100), nullable=True)  # MIME type
    
    # Vector index tracking (LlamaIndex integration)
    ref_doc_id = Column(String(255), unique=True, index=True, nullable=True)  # LlamaIndex document ID
    document_hash = Column(String(100), nullable=True)  # For change detection
    node_count = Column(Integer, default=0)  # Number of chunks/nodes created
    collection_id = Column(String(100), nullable=True, index=True)  # Qdrant collection
    
    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    indexed_in_vector_db = Column(Boolean, default=False)
    embeddings_generated = Column(Boolean, default=False)
    
    # Metadata and configuration
    processing_config = Column(JSON, nullable=True)  # Chunk size, model used, etc.
    file_metadata = Column(JSON, nullable=True)  # Additional file metadata
    error_message = Column(Text, nullable=True)  # Error details if processing failed
    
    # Hierarchy support
    parent_file_id = Column(String(50), ForeignKey("knowledge_files.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="knowledge_files")
    children = relationship("KnowledgeFile", backref="parent", remote_side=[id])

    # Database optimizations
    __table_args__ = (
        Index('ix_knowledge_files_user_status', 'user_id', 'processing_status'),
        Index('ix_knowledge_files_collection_status', 'collection_id', 'indexed_in_vector_db'),
        Index('ix_knowledge_files_ref_doc', 'ref_doc_id'),
    )

    def __repr__(self):
        return f"<KnowledgeFile(id={self.id}, file_name={self.file_name}, status={self.processing_status})>"

    @property
    def is_processed(self) -> bool:
        """Check if file has been successfully processed."""
        status = getattr(self, 'processing_status', None)
        indexed = getattr(self, 'indexed_in_vector_db', False)
        return status == "completed" and indexed

    @property
    def needs_reprocessing(self) -> bool:
        """Check if file needs reprocessing due to errors or changes."""
        status = getattr(self, 'processing_status', None)
        indexed = getattr(self, 'indexed_in_vector_db', False)
        return status in ["failed", "pending"] or not indexed

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "processing_status": self.processing_status,
            "indexed_in_vector_db": self.indexed_in_vector_db,
            "embeddings_generated": self.embeddings_generated,
            "node_count": self.node_count,
            "collection_id": self.collection_id,
            "created_at": getattr(self, 'created_at', None).isoformat() if getattr(self, 'created_at', None) else None,
            "updated_at": getattr(self, 'updated_at', None).isoformat() if getattr(self, 'updated_at', None) else None,
            "processed_at": getattr(self, 'processed_at', None).isoformat() if getattr(self, 'processed_at', None) else None,
        } 