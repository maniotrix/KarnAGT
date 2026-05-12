"""Vector Collection model for tracking vector collections and their state."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class VectorCollectionScope(str, enum.Enum):
    """
    Enum for vector collection scopes.
    Defines the different types of entities that can own vector collections.
    """
    USER = "user"                    # User-level collections (User knowledge base)
    CONVERSATION = "conversation"    # Conversation-level collections (chat documents)
    PROJECT = "project"             # Project-level collections (team/workspace docs)
    ORGANIZATION = "organization"   # Organization-level collections (company knowledge)
    TEAM = "team"                   # Team-level collections (group documents)
    WORKSPACE = "workspace"         # Workspace-level collections (shared workspace)
    
    @classmethod
    def get_display_name(cls, scope: "VectorCollectionScope") -> str:
        """Get human-readable display name for scope."""
        display_names = {
            cls.USER: "User",
            cls.CONVERSATION: "Conversation",
            cls.PROJECT: "Project",
            cls.ORGANIZATION: "Organization",
            cls.TEAM: "Team",
            cls.WORKSPACE: "Workspace"
        }
        return display_names.get(scope, scope.value.title())
    
    @classmethod
    def get_description(cls, scope: "VectorCollectionScope") -> str:
        """Get description for scope."""
        descriptions = {
            cls.USER: "User knowledge base and documents",
            cls.CONVERSATION: "Documents uploaded during chat conversations",
            cls.PROJECT: "Project-specific documents and resources",
            cls.ORGANIZATION: "Organization-wide knowledge base",
            cls.TEAM: "Team-shared documents and resources",
            cls.WORKSPACE: "Workspace-level shared documents"
        }
        return descriptions.get(scope, f"{scope.value.title()} level collection")


class VectorCollection(Base):
    """
    Tracks vector collections (Qdrant collections) and their metadata.
    Supports multiple scopes: user, conversation, project, etc.
    """
    __tablename__ = "vector_collections"

    # Primary identification
    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)  # Owner for permissions (UUID)
    
    # Scope configuration - flexible for any future use cases
    scope = Column(String(50), nullable=False, index=True)  # Store as string, use enum in app
    scope_id = Column(String(50), nullable=False, index=True)  # ID of the scope entity
    
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
    knowledge_files = relationship("KnowledgeFile", back_populates="vector_collection")

    # Database optimizations
    __table_args__ = (
        Index('ix_vector_collections_user_status', 'user_id', 'status'),
        Index('ix_vector_collections_name_user', 'collection_name', 'user_id'),
        Index('ix_vector_collections_default', 'user_id', 'is_default'),
        Index('ix_vector_collections_scope', 'scope', 'scope_id'),
        Index('ix_vector_collections_scope_status', 'scope', 'scope_id', 'status'),
        Index('ix_vector_collections_user_scope', 'user_id', 'scope', 'scope_id'),
    )

    def __repr__(self):
        return f"<VectorCollection(id={self.id}, name={self.collection_name}, scope={self.scope}, scope_id={self.scope_id}, status={self.status})>"

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

    def is_user_scope(self) -> bool:
        """Check if this is a user-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.USER.value

    def is_conversation_scope(self) -> bool:
        """Check if this is a conversation-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.CONVERSATION.value

    def is_project_scope(self) -> bool:
        """Check if this is a project-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.PROJECT.value

    def is_organization_scope(self) -> bool:
        """Check if this is an organization-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.ORGANIZATION.value

    def is_team_scope(self) -> bool:
        """Check if this is a team-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.TEAM.value

    def is_workspace_scope(self) -> bool:
        """Check if this is a workspace-level collection."""
        return getattr(self, 'scope', None) == VectorCollectionScope.WORKSPACE.value

    def get_scope_entity_id(self) -> str:
        """Get the scope entity ID."""
        return getattr(self, 'scope_id', None) or ""

    def get_scope_display_name(self) -> str:
        """Get human-readable display name for the scope."""
        scope_val = getattr(self, 'scope', None)
        if scope_val:
            scope_enum = VectorCollectionScope(scope_val)
            return VectorCollectionScope.get_display_name(scope_enum)
        return "Unknown"

    def get_scope_description(self) -> str:
        """Get description for the scope."""
        scope_val = getattr(self, 'scope', None)
        if scope_val:
            scope_enum = VectorCollectionScope(scope_val)
            return VectorCollectionScope.get_description(scope_enum)
        return "Unknown scope"

    @classmethod
    def generate_collection_name(cls, scope: VectorCollectionScope, scope_id: str, prefix: str = None) -> str:
        """Generate a unique collection name for a scope."""
        short_uuid = str(uuid.uuid4()).replace('-', '')[:8]
        if prefix:
            return f"{prefix}_{scope.value}_{scope_id}_{short_uuid}"
        return f"{scope.value}_{scope_id}_{short_uuid}"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "collection_name": self.collection_name,
            "display_name": self.display_name,
            "description": self.description,
            "scope": self.scope,
            "scope_id": self.scope_id,
            "scope_display_name": self.get_scope_display_name(),
            "scope_description": self.get_scope_description(),
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