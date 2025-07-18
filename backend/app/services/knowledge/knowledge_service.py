#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Service - High-level service for knowledge file operations
Follows the same pattern as MemoryService for consistency
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.production_rag_service import ProductionRAGService, ProcessingResult, QueryResult
from app.services.knowledge.config import RAGConfig
from aicore.logger import get_logger

logger = get_logger(__name__)


class KnowledgeService:
    """
    High-level service for knowledge file operations.
    
    This service wraps ProductionRAGService and manages database sessions internally,
    following the same pattern as MemoryService for consistency.
    
    Key features:
    - Database session managed internally
    - RAG service created once and reused
    - High-level methods that hide implementation complexity
    - Consistent with memory tools architecture
    """
    
    def __init__(self, db_session: AsyncSession, rag_config: Optional[RAGConfig] = None):
        """
        Initialize Knowledge Service.
        
        Args:
            db_session: Database session to store internally
            rag_config: Optional RAG configuration (uses default if not provided)
        """
        self.db = db_session
        
        # Initialize RAG service once (not per tool call)
        if rag_config is None:
            rag_config = RAGConfig.for_chat_application()
        
        self.rag_service = ProductionRAGService(rag_config)
        
        logger.info(f"KnowledgeService initialized with RAG config: {rag_config.llm_model}")
    
    # =============================================================================
    # HIGH-LEVEL SEARCH METHODS
    # =============================================================================
    
    async def search_conversation_files(
        self, 
        user_id: str, 
        conversation_id: str, 
        query: str,
        include_inactive: bool = False
    ) -> Optional[QueryResult]:
        """
        Search all files in a conversation.
        
        Args:
            user_id: User ID for access validation
            conversation_id: Conversation ID to search within
            query: Search query
            include_inactive: Whether to include inactive documents (default: False)
            
        Returns:
            QueryResult if successful, None if no collection found
        """
        logger.info(f"Searching conversation {conversation_id} files for query: {query}")
        
        try:
            result = await self.rag_service.query_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                query=query,
                db=self.db,
                include_inactive=include_inactive
            )
            
            if result:
                logger.info(f"Found {len(result.sources)} sources in conversation search")
            else:
                logger.info("No results found in conversation search")
                
            return result
            
        except Exception as e:
            logger.error(f"Error searching conversation files: {e}")
            raise
    
    async def search_specific_files(
        self,
        user_id: str,
        conversation_id: str,
        query: str,
        knowledge_file_ids: List[str],
        include_inactive: bool = False
    ) -> Optional[QueryResult]:
        """
        Search specific knowledge files by their IDs.
        
        Args:
            user_id: User ID for access validation
            conversation_id: Conversation ID for context
            query: Search query
            knowledge_file_ids: List of knowledge file IDs to search
            include_inactive: Whether to include inactive documents (default: False)
            
        Returns:
            QueryResult if successful, None if no files found
        """
        logger.info(f"Searching {len(knowledge_file_ids)} specific files for query: {query}")
        
        try:
            # Get knowledge files and extract ref_doc_ids
            from sqlalchemy import select, and_
            from app.models.database.knowledge_file import KnowledgeFile
            
            result = await self.db.execute(
                select(KnowledgeFile).where(
                    and_(
                        KnowledgeFile.id.in_(knowledge_file_ids),
                        KnowledgeFile.user_id == user_id,
                        KnowledgeFile.indexed_in_vector_db == True
                    )
                )
            )
            knowledge_files = result.scalars().all()
            
            if not knowledge_files:
                logger.warning(f"No accessible files found for IDs: {knowledge_file_ids}")
                return None
            
            # Extract all ref_doc_ids from knowledge files
            all_ref_doc_ids = []
            for kf in knowledge_files:
                ref_doc_ids = kf.get_ref_doc_ids()
                all_ref_doc_ids.extend(ref_doc_ids)
            
            if not all_ref_doc_ids:
                logger.warning("No ref_doc_ids found in knowledge files")
                return None
            
            # Query using RAG service with document filtering
            result = await self.rag_service.query_conversation_with_documents(
                user_id=user_id,
                conversation_id=conversation_id,
                query=query,
                document_ids=all_ref_doc_ids,
                db=self.db,
                include_inactive=include_inactive
            )
            
            if result:
                logger.info(f"Found {len(result.sources)} sources in specific files search")
            else:
                logger.info("No results found in specific files search")
                
            return result
            
        except Exception as e:
            logger.error(f"Error searching specific files: {e}")
            raise
    
    async def list_available_files(
        self,
        user_id: str,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        List available knowledge files in a conversation.
        
        Args:
            user_id: User ID for access validation
            conversation_id: Conversation ID to list files for
            
        Returns:
            List of file metadata dictionaries
        """
        logger.info(f"Listing available files for conversation {conversation_id}")
        
        try:
            available_docs = await self.rag_service.get_available_documents_in_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                db=self.db
            )
            
            logger.info(f"Found {len(available_docs)} available files")
            return available_docs
            
        except Exception as e:
            logger.error(f"Error listing available files: {e}")
            raise
    
    # =============================================================================
    # DOCUMENT PROCESSING METHODS
    # =============================================================================
    
    async def process_conversation_documents(
        self,
        user_id: str,
        conversation_id: str,
        s3_keys: List[str],
        conversation_title: Optional[str] = None,
        force_reprocess: bool = False
    ) -> ProcessingResult:
        """
        Process documents for a conversation.
        
        Args:
            user_id: User ID for ownership
            conversation_id: Conversation ID
            s3_keys: List of S3 keys to process
            conversation_title: Optional conversation title
            force_reprocess: Whether to force reprocessing
            
        Returns:
            ProcessingResult with processing metrics
        """
        logger.info(f"Processing {len(s3_keys)} documents for conversation {conversation_id}")
        
        try:
            collection, result = await self.rag_service.process_conversation_documents(
                user_id=user_id,
                conversation_id=conversation_id,
                s3_keys=s3_keys,
                db=self.db,
                conversation_title=conversation_title,
                force_reprocess=force_reprocess
            )
            
            logger.info(f"Processed {result.processed_count} documents successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing conversation documents: {e}")
            raise
    
    async def process_s3_documents(
        self,
        collection_id: str,
        s3_keys: List[str],
        user_id: str,
        force_reprocess: bool = False
    ) -> ProcessingResult:
        """
        Process S3 documents for a specific collection.
        
        Args:
            collection_id: Vector collection ID
            s3_keys: List of S3 keys to process
            user_id: User ID for ownership
            force_reprocess: Whether to force reprocessing
            
        Returns:
            ProcessingResult with processing metrics
        """
        logger.info(f"Processing {len(s3_keys)} S3 documents for collection {collection_id}")
        
        try:
            result = await self.rag_service.process_s3_documents(
                collection_id=collection_id,
                s3_keys=s3_keys,
                user_id=user_id,
                db=self.db,
                force_reprocess=force_reprocess
            )
            
            logger.info(f"Processed {result.processed_count} documents successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing S3 documents: {e}")
            raise
    
    # =============================================================================
    # COLLECTION MANAGEMENT METHODS
    # =============================================================================
    
    async def get_or_create_conversation_collection(
        self,
        user_id: str,
        conversation_id: str,
        conversation_title: Optional[str] = None
    ):
        """
        Get or create a conversation collection.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            conversation_title: Optional conversation title
            
        Returns:
            VectorCollection instance
        """
        logger.info(f"Getting or creating collection for conversation {conversation_id}")
        
        try:
            collection = await self.rag_service.get_or_create_conversation_collection(
                user_id=user_id,
                conversation_id=conversation_id,
                db=self.db,
                conversation_title=conversation_title
            )
            
            logger.info(f"Using collection: {collection.id}")
            return collection
            
        except Exception as e:
            logger.error(f"Error getting/creating conversation collection: {e}")
            raise
    
    async def get_or_create_user_collection(
        self,
        user_id: str,
        collection_name: Optional[str] = None,
        display_name: Optional[str] = None
    ):
        """
        Get or create a user collection.
        
        Args:
            user_id: User ID
            collection_name: Optional collection name
            display_name: Optional display name
            
        Returns:
            VectorCollection instance
        """
        logger.info(f"Getting or creating user collection for user {user_id}")
        
        try:
            collection = await self.rag_service.get_or_create_user_collection(
                user_id=user_id,
                db=self.db,
                collection_name=collection_name,
                display_name=display_name
            )
            
            logger.info(f"Using collection: {collection.id}")
            return collection
            
        except Exception as e:
            logger.error(f"Error getting/creating user collection: {e}")
            raise
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def get_collection_stats(self, collection_id: str) -> Dict[str, Any]:
        """
        Get statistics for a collection.
        
        Args:
            collection_id: Collection ID
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            from app.services.knowledge.vector_collection_service import VectorCollectionService
            
            collection_service = VectorCollectionService()
            collection = await collection_service.get_by_id(collection_id, self.db)
            
            if not collection:
                return {}
            
            return {
                "collection_id": collection.id,
                "collection_name": collection.collection_name,
                "total_documents": getattr(collection, 'total_documents', 0),
                "total_nodes": getattr(collection, 'total_nodes', 0),
                "total_vectors": getattr(collection, 'total_vectors', 0),
                "total_queries": getattr(collection, 'total_queries', 0),
                "last_sync": getattr(collection, 'last_sync', None),
                "created_at": collection.created_at,
                "updated_at": collection.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def get_rag_config(self) -> RAGConfig:
        """Get the current RAG configuration."""
        return self.rag_service.config
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the knowledge service."""
        return {
            "service_type": "KnowledgeService",
            "rag_model": self.rag_service.config.llm_model,
            "embedding_model": self.rag_service.config.embedding_model,
            "chunk_size": self.rag_service.config.chunk_size,
            "similarity_top_k": self.rag_service.config.similarity_top_k,
            "qdrant_url": self.rag_service.qdrant_config.url,
            "qdrant_collection": self.rag_service.qdrant_config.collection_name
        } 