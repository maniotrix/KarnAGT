"""Vector Collection model for tracking vector collections and their state."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class VectorCollection(Base):
    """
    Tracks vector collections (Qdrant collections) and their metadata.
    Each user can have multiple collections for different projects/contexts.
    """
    __tablename__ = "vector_collections"

    # Primary identification
    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Collection information
    collection_name = Column(String(100), unique=True, index=True, nullable=False)  # Qdrant collection name
    display_name = Column(String(255), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)  # Collection description
    
    # Vector store configuration
    qdrant_url = Column(String(500), nullable=False)  # Qdrant server URL
    vector_size = Column(Integer, default=1536)  # Embedding dimensions
    distance_metric = Column(String(20), default="Cosine")  # Distance metric
    
    # Collection statistics
    total_documents = Column(Integer, default=0)  # Number of documents indexed
    total_nodes = Column(Integer, default=0)  # Number of chunks/nodes
    total_vectors = Column(Integer, default=0)  # Number of vectors stored
    
    # Processing configuration
    embedding_model = Column(String(100), nullable=True)  # Model used for embeddings
    chunk_size = Column(Integer, nullable=True)  # Chunk size used
    chunk_overlap = Column(Integer, nullable=True)  # Chunk overlap used
    pipeline_config = Column(JSON, nullable=True)  # Full IngestionPipeline config
    
    # Status and health
    status = Column(String(50), default="active")  # active, inactive, error, syncing
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    last_sync = Column(DateTime(timezone=True), nullable=True)  # Last successful sync
    health_status = Column(String(50), default="unknown")  # healthy, degraded, unhealthy
    
    # Performance metrics
    avg_query_time = Column(Float, nullable=True)  # Average query time in seconds
    last_query_time = Column(DateTime(timezone=True), nullable=True)
    total_queries = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    last_error = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration flags
    auto_sync = Column(Boolean, default=True)  # Automatically sync new files
    is_default = Column(Boolean, default=False)  # Default collection for user
    is_shared = Column(Boolean, default=False)  # Shared with other users
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="vector_collections")
    knowledge_files = relationship("KnowledgeFile", 
                                 primaryjoin="VectorCollection.collection_name == foreign(KnowledgeFile.collection_id)",
                                 viewonly=True)

    # Database optimizations
    __table_args__ = (
        Index('ix_vector_collections_user_status', 'user_id', 'status'),
        Index('ix_vector_collections_name_user', 'collection_name', 'user_id'),
        Index('ix_vector_collections_default', 'user_id', 'is_default'),
    )

    def __repr__(self):
        return f"<VectorCollection(id={self.id}, name={self.collection_name}, status={self.status})>"

    def is_healthy(self) -> bool:
        """Check if collection is in healthy state."""
        return (getattr(self, 'status', None) == "active" and 
                getattr(self, 'health_status', None) == "healthy")

    def needs_attention(self) -> bool:
        """Check if collection needs attention due to errors or issues."""
        status_val = getattr(self, 'status', None)
        health_val = getattr(self, 'health_status', None)
        error_count_val = getattr(self, 'error_count', 0) or 0
        return (status_val == "error" or 
                health_val in ["degraded", "unhealthy"] or 
                error_count_val > 5)

    def collection_size_mb(self) -> float:
        """Estimate collection size in MB based on vectors."""
        total_vectors_val = getattr(self, 'total_vectors', 0) or 0
        vector_size_val = getattr(self, 'vector_size', 0) or 0
        
        if total_vectors_val and vector_size_val:
            # Rough estimate: vector_size * 4 bytes (float32) * total_vectors
            # Plus overhead for HNSW index (approximately 2x)
            size_bytes = total_vectors_val * vector_size_val * 4 * 2
            return size_bytes / (1024 * 1024)  # Convert to MB
        return 0.0

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "collection_name": self.collection_name,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status,
            "health_status": self.health_status,
            "total_documents": self.total_documents,
            "total_nodes": self.total_nodes,
            "total_vectors": self.total_vectors,
            "vector_size": self.vector_size,
            "distance_metric": self.distance_metric,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "is_default": self.is_default,
            "is_shared": self.is_shared,
            "auto_sync": self.auto_sync,
            "avg_query_time": self.avg_query_time,
            "total_queries": self.total_queries,
            "collection_size_mb": self.collection_size_mb(),
            "created_at": self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            "updated_at": self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None,
            "last_sync": self.last_sync.isoformat() if getattr(self, 'last_sync', None) else None,
            "last_query_time": self.last_query_time.isoformat() if getattr(self, 'last_query_time', None) else None,
        }

    def to_config_dict(self):
        """Convert to configuration dictionary for IngestionPipeline."""
        return {
            "collection_name": self.collection_name,
            "qdrant_url": self.qdrant_url,
            "vector_size": self.vector_size,
            "distance_metric": self.distance_metric,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "pipeline_config": getattr(self, 'pipeline_config', None) or {}
        } 