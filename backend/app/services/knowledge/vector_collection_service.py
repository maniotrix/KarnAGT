"""
Vector Collection Service for database operations.

This service handles all CRUD operations for VectorCollection records across different scopes.
It focuses purely on database operations and does not handle vector processing.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.database import VectorCollection, VectorCollectionScope, User, Conversation, KnowledgeFile
from app.core.database import get_db
from app.services.knowledge.config import QdrantConfig, get_default_qdrant_config

logger = logging.getLogger(__name__)


@dataclass
class VectorCollectionFilter:
    """Filter criteria for searching vector collections."""
    user_id: Optional[int] = None
    scope: Optional[VectorCollectionScope] = None
    scope_id: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None
    collection_name: Optional[str] = None


@dataclass
class VectorCollectionStats:
    """Statistics for vector collections."""
    total_collections: int
    active_collections: int
    inactive_collections: int
    total_documents: int
    total_vectors: int
    collections_by_scope: Dict[str, int]
    avg_collection_size_mb: float


class VectorCollectionService:
    """
    Service for managing VectorCollection database records across different scopes.
    
    This service provides:
    - Scope-aware collection creation and retrieval
    - Collection lifecycle management
    - Statistics and analytics
    - Bulk operations
    - Collection validation and consistency checks
    """
    
    def __init__(self, qdrant_config: Optional[QdrantConfig] = None):
        """Initialize the vector collection service."""
        self.qdrant_config = qdrant_config or get_default_qdrant_config()
        logger.info("VectorCollectionService initialized")

    # Core CRUD Operations

    async def get_or_create_for_scope(
        self,
        user_id: int,
        scope: VectorCollectionScope,
        scope_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> VectorCollection:
        """
        Get existing collection for scope or create new one.
        
        Args:
            user_id: Owner user ID
            scope: Collection scope (VectorCollectionScope enum)
            scope_id: ID of the scope entity (conversation_id, project_id, etc.)
            display_name: Human-readable name (optional)
            description: Collection description (optional)
            db: Database session (optional)
            **kwargs: Additional collection parameters
            
        Returns:
            VectorCollection record
        """
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        logger.info(f"Getting or creating collection for scope {scope.value}:{scope_id}")

        # Check if collection exists for this scope
        existing = await self.get_by_scope(user_id, scope, scope_id, db)
        if existing:
            logger.info(f"Found existing collection: {existing.id}")
            return existing

        # Create new collection
        collection = await self.create_for_scope(
            user_id=user_id,
            scope=scope,
            scope_id=scope_id,
            display_name=display_name,
            description=description,
            db=db,
            **kwargs
        )
        
        logger.info(f"Created new collection: {collection.id}")
        return collection

    async def create_for_scope(
        self,
        user_id: int,
        scope: VectorCollectionScope,
        scope_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> VectorCollection:
        """
        Create new vector collection for specific scope.
        
        Args:
            user_id: Owner user ID
            scope: Collection scope
            scope_id: Scope entity ID
            display_name: Human-readable name
            description: Collection description
            db: Database session
            **kwargs: Additional collection parameters
            
        Returns:
            New VectorCollection record
        """
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        # Generate collection name
        collection_name = VectorCollection.generate_collection_name(scope, scope_id)
        
        # Set default display name if not provided
        if not display_name:
            display_name = f"{VectorCollectionScope.get_display_name(scope)} {scope_id}"

        # Get vector size for embedding model
        embedding_model = kwargs.get('embedding_model', 'text-embedding-3-small')
        vector_size = QdrantConfig.get_vector_size_for_model(embedding_model)

        # Create collection record
        collection = VectorCollection(
            id=f"col_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            scope=scope.value,  # Store string value in database
            scope_id=scope_id,
            collection_name=collection_name,
            display_name=display_name,
            description=description or VectorCollectionScope.get_description(scope),
            qdrant_url=kwargs.get('qdrant_url', self.qdrant_config.url),
            vector_size=vector_size,
            distance_metric=kwargs.get('distance_metric', 'Cosine'),
            embedding_model=embedding_model,
            chunk_size=kwargs.get('chunk_size', 1000),
            chunk_overlap=kwargs.get('chunk_overlap', 200),
            status=kwargs.get('status', 'active'),
            health_status=kwargs.get('health_status', 'healthy'),
            auto_sync=kwargs.get('auto_sync', True),
            is_default=kwargs.get('is_default', False),
            is_shared=kwargs.get('is_shared', False)
        )

        db.add(collection)
        await db.commit()
        await db.refresh(collection)

        logger.info(f"Created collection {collection.id} for {scope.value}:{scope_id}")
        return collection

    async def get_by_id(self, collection_id: str, db: Optional[AsyncSession] = None) -> Optional[VectorCollection]:
        """Get collection by ID."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        result = await db.execute(
            select(VectorCollection).where(VectorCollection.id == collection_id)
        )
        return result.scalar_one_or_none()

    async def get_by_scope(
        self,
        user_id: int,
        scope: VectorCollectionScope,
        scope_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[VectorCollection]:
        """Get collection by scope and scope_id."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        result = await db.execute(
            select(VectorCollection).where(
                and_(
                    VectorCollection.user_id == user_id,
                    VectorCollection.scope == scope.value,  # Compare with string value
                    VectorCollection.scope_id == scope_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_collections_for_user(
        self,
        user_id: int,
        scope_filter: Optional[VectorCollectionScope] = None,
        include_inactive: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[VectorCollection]:
        """Get all collections for a user, optionally filtered by scope."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        query = select(VectorCollection).where(VectorCollection.user_id == user_id)
        
        if scope_filter:
            query = query.where(VectorCollection.scope == scope_filter.value)  # Compare with string value
        
        if not include_inactive:
            query = query.where(VectorCollection.status == 'active')
        
        query = query.order_by(VectorCollection.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())

    async def search_collections(
        self,
        filter_criteria: VectorCollectionFilter,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> Tuple[List[VectorCollection], int]:
        """Search collections with advanced filtering."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        # Build query conditions
        conditions = []
        
        if filter_criteria.user_id:
            conditions.append(VectorCollection.user_id == filter_criteria.user_id)
        
        if filter_criteria.scope:
            conditions.append(VectorCollection.scope == filter_criteria.scope.value)  # Compare with string value
        
        if filter_criteria.scope_id:
            conditions.append(VectorCollection.scope_id == filter_criteria.scope_id)
        
        if filter_criteria.status:
            conditions.append(VectorCollection.status == filter_criteria.status)
        
        if filter_criteria.is_default is not None:
            conditions.append(VectorCollection.is_default == filter_criteria.is_default)
        
        if filter_criteria.is_shared is not None:
            conditions.append(VectorCollection.is_shared == filter_criteria.is_shared)
        
        if filter_criteria.collection_name:
            conditions.append(VectorCollection.collection_name.ilike(f"%{filter_criteria.collection_name}%"))

        # Build main query
        query = select(VectorCollection)
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(VectorCollection.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(VectorCollection.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        collections = list(result.scalars().all())

        return collections, total_count

    # Scope-specific convenience methods

    async def get_user_collections(self, user_id: int, db: Optional[AsyncSession] = None) -> List[VectorCollection]:
        """Get all user-scope collections for a user."""
        return await self.get_collections_for_user(user_id, VectorCollectionScope.USER, db=db)

    async def get_conversation_collection(
        self,
        user_id: int,
        conversation_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[VectorCollection]:
        """Get conversation-scope collection."""
        return await self.get_by_scope(user_id, VectorCollectionScope.CONVERSATION, str(conversation_id), db)

    async def get_or_create_conversation_collection(
        self,
        user_id: int,
        conversation_id: int,
        conversation_title: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> VectorCollection:
        """Get or create collection for a conversation."""
        display_name = f"Conversation: {conversation_title}" if conversation_title else f"Conversation {conversation_id}"
        
        return await self.get_or_create_for_scope(
            user_id=user_id,
            scope=VectorCollectionScope.CONVERSATION,
            scope_id=str(conversation_id),
            display_name=display_name,
            description=f"Documents uploaded in conversation {conversation_id}",
            db=db
        )

    async def get_project_collections(self, user_id: int, project_id: str, db: Optional[AsyncSession] = None) -> List[VectorCollection]:
        """Get all collections for a project."""
        return await self.get_collections_for_user(user_id, VectorCollectionScope.PROJECT, db=db)

    # Update operations

    async def update_collection(
        self,
        collection_id: str,
        updates: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> Optional[VectorCollection]:
        """Update collection with provided values."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        # Add updated_at timestamp
        updates['updated_at'] = datetime.now(timezone.utc)

        await db.execute(
            update(VectorCollection)
            .where(VectorCollection.id == collection_id)
            .values(**updates)
        )
        await db.commit()

        return await self.get_by_id(collection_id, db)

    async def update_collection_stats(
        self,
        collection_id: str,
        total_documents: Optional[int] = None,
        total_nodes: Optional[int] = None,
        total_vectors: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[VectorCollection]:
        """Update collection statistics."""
        updates = {
            'last_sync': datetime.now(timezone.utc)
        }
        
        if total_documents is not None:
            updates['total_documents'] = total_documents
        if total_nodes is not None:
            updates['total_nodes'] = total_nodes
        if total_vectors is not None:
            updates['total_vectors'] = total_vectors

        return await self.update_collection(collection_id, updates, db)

    async def update_collection_health(
        self,
        collection_id: str,
        health_status: str,
        error_message: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[VectorCollection]:
        """Update collection health status."""
        updates = {'health_status': health_status}
        
        if error_message:
            updates['error_message'] = error_message
            updates['error_count'] = func.coalesce(VectorCollection.error_count, 0) + 1
            updates['last_error'] = datetime.now(timezone.utc)

        return await self.update_collection(collection_id, updates, db)

    # Delete operations

    async def delete_collection(self, collection_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Delete collection record (soft delete by setting status to 'deleted')."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        result = await db.execute(
            update(VectorCollection)
            .where(VectorCollection.id == collection_id)
            .values(
                status='deleted',
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()

        return result.rowcount > 0

    async def hard_delete_collection(self, collection_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Permanently delete collection record."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        result = await db.execute(
            delete(VectorCollection).where(VectorCollection.id == collection_id)
        )
        await db.commit()

        return result.rowcount > 0

    # Analytics and statistics

    async def get_user_collection_stats(self, user_id: int, db: Optional[AsyncSession] = None) -> VectorCollectionStats:
        """Get comprehensive statistics for user's collections."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        # Get all collections for user
        collections = await self.get_collections_for_user(user_id, include_inactive=True, db=db)
        
        # Calculate statistics
        total_collections = len(collections)
        active_collections = len([c for c in collections if getattr(c, 'status', None) == 'active'])
        inactive_collections = total_collections - active_collections
        
        total_documents = sum(getattr(c, 'total_documents', 0) or 0 for c in collections)
        total_vectors = sum(getattr(c, 'total_vectors', 0) or 0 for c in collections)
        
        # Count by scope
        collections_by_scope = {}
        for collection in collections:
            scope = getattr(collection, 'scope', None)
            if scope:
                scope_value = scope.value if hasattr(scope, 'value') else str(scope)
                collections_by_scope[scope_value] = collections_by_scope.get(scope_value, 0) + 1
        
        # Average collection size
        total_size_mb = sum(c.collection_size_mb() for c in collections)
        avg_collection_size_mb = total_size_mb / total_collections if total_collections > 0 else 0.0

        return VectorCollectionStats(
            total_collections=total_collections,
            active_collections=active_collections,
            inactive_collections=inactive_collections,
            total_documents=total_documents,
            total_vectors=total_vectors,
            collections_by_scope=collections_by_scope,
            avg_collection_size_mb=avg_collection_size_mb
        )

    # Validation and consistency

    async def validate_collection_consistency(
        self,
        collection_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Validate collection consistency and return issues."""
        if db is None:
            async for db_session in get_db():
                db = db_session
                break

        collection = await self.get_by_id(collection_id, db)
        if not collection:
            return {"valid": False, "errors": ["Collection not found"]}

        issues = []
        warnings = []

        # Check if scope entity exists
        if collection.is_conversation_scope():
            # Validate conversation exists
            result = await db.execute(
                select(Conversation).where(
                    and_(
                        Conversation.id == int(collection.scope_id),
                        Conversation.user_id == collection.user_id
                    )
                )
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                issues.append(f"Conversation {collection.scope_id} not found")

        # Check knowledge files count consistency
        result = await db.execute(
            select(func.count(KnowledgeFile.id)).where(
                KnowledgeFile.collection_id == collection.collection_name
            )
        )
        actual_files = result.scalar() or 0
        expected_files = getattr(collection, 'total_documents', 0) or 0
        
        if actual_files != expected_files:
            warnings.append(f"File count mismatch: expected {expected_files}, found {actual_files}")

        return {
            "valid": len(issues) == 0,
            "errors": issues,
            "warnings": warnings,
            "actual_file_count": actual_files,
            "expected_file_count": expected_files
        }