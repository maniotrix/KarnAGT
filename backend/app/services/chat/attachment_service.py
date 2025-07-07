"""
Attachment Service for Chat Message Integration
Refactored to use new StagingFileCollection data structure
"""

from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage.staging_storage import staging_service
from app.models.schemas.staging_schemas import StagingFileCollection, StagingFileInfo

from aicore.logger import get_logger

logger = get_logger(__name__)


class AttachmentService:
    """Service for managing message attachments using new staging file structure"""
    
    async def process_staging_files(
        self, 
        staging_collection: StagingFileCollection, 
        user_id: str, 
        conversation_id: str,
        db: AsyncSession
    ) -> Tuple[List[Dict[str, Any]], List[str], Optional[Dict[str, Any]]]:
        """
        Process staging files using new data structure
        
        Args:
            staging_collection: StagingFileCollection object
            user_id: User ID for validation
            conversation_id: Conversation ID for vector collection
            db: Database session
            
        Returns:
            Tuple of (message_attachments, openai_file_ids, vector_file_references)
        """
        logger.info(f"Processing staging collection with {staging_collection.total_count} files")
        logger.info(f"  - Images: {staging_collection.image_count}")
        logger.info(f"  - Vectors: {staging_collection.vector_count}")
        logger.info(f"  - Unknown: {staging_collection.unknown_count}")
        
        message_attachments = []
        openai_file_ids = []
        vector_file_references = None
        
        # Process image files (existing functionality)
        if staging_collection.has_images:
            image_attachments, image_openai_ids = await self._process_image_files(
                staging_collection.images, user_id, db
            )
            message_attachments.extend(image_attachments)
            openai_file_ids.extend(image_openai_ids)
        
        # Process vector files (placeholder for now)
        if staging_collection.has_vectors:
            vector_file_references = await self._process_vector_files(
                staging_collection.vectors, user_id, conversation_id, db
            )
        
        logger.info(f"Processing completed: {len(message_attachments)} images, vector_refs: {vector_file_references is not None}")
        
        return message_attachments, openai_file_ids, vector_file_references
    
    async def _process_image_files(
        self,
        image_files: List[StagingFileInfo],
        user_id: str,
        db: AsyncSession
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process image files using existing staging service"""
        if not image_files:
            return [], []
        
        logger.info(f"Processing {len(image_files)} image files")
        
        # Convert to legacy format for existing staging service
        legacy_staging_files = [
            {"file_id": img.file_id, "s3_key": img.s3_key}
            for img in image_files
        ]
        
        # Use existing staging service commit functionality
        commit_result = await staging_service.commit_files_with_known_keys(
            staging_files=legacy_staging_files,
            user_id=user_id,
            db=db
        )
        
        if commit_result["failed_commits"] > 0:
            logger.warning(f"Some image files failed to commit: {commit_result['failed_files']}")
        
        if commit_result["successfully_committed"] == 0:
            logger.warning("No image files were successfully committed")
            return [], []
        
        # Extract message attachments and OpenAI file IDs
        message_attachments = commit_result["message_attachments"]
        openai_file_ids = [attachment["openai_file_id"] for attachment in message_attachments]
        
        logger.info(f"Successfully processed {len(message_attachments)} image files")
        return message_attachments, openai_file_ids
    
    async def _process_vector_files(
        self,
        vector_files: List[StagingFileInfo],
        user_id: str,
        conversation_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Process vector files using ProductionRAGService
        
        This method:
        1. Gets/creates conversation vector collection
        2. Processes S3 documents using ProductionRAGService
        3. Updates knowledge_files table automatically
        4. Returns vector file references for message storage
        """
        if not vector_files:
            return None
        
        logger.info(f"Processing {len(vector_files)} vector files for conversation {conversation_id}")
        
        try:
            # Import ProductionRAGService and config
            from app.services.knowledge.production_rag_service import ProductionRAGService
            from app.services.knowledge.config import RAGConfig
            
            # Create RAG service instance
            rag_config = RAGConfig.for_chat_application()
            rag_service = ProductionRAGService(rag_config)
            
            # Extract S3 keys from vector files
            s3_keys = [vf.s3_key for vf in vector_files]
            
            # Process documents using RAG service (handles all DB operations)
            collection, result = await rag_service.process_conversation_documents(
                user_id=user_id,
                conversation_id=conversation_id,
                s3_keys=s3_keys,
                db=db
            )
            
            # Query database to get KnowledgeFile records for linking
            from sqlalchemy import select
            from app.models.database.knowledge_file import KnowledgeFile
            
            knowledge_files_result = await db.execute(
                select(KnowledgeFile).where(
                    KnowledgeFile.collection_id == collection.id,
                    KnowledgeFile.file_path.in_(s3_keys)
                )
            )
            knowledge_files = {kf.file_path: kf for kf in knowledge_files_result.scalars().all()}
            
            # Build vector file references for message storage
            processed_files = []
            for vector_file in vector_files:
                kf = knowledge_files.get(vector_file.s3_key)
                if kf:
                    processed_files.append({
                        "file_id": vector_file.file_id,
                        "knowledge_file_id": kf.id,  # Link to KnowledgeFile
                        "ref_doc_id": kf.ref_doc_id,  # For file-specific queries
                        "s3_key": vector_file.s3_key,
                        "filename": vector_file.filename,
                        "content_type": vector_file.content_type,
                        "file_size": vector_file.file_size,
                        "node_count": kf.node_count,
                        "processing_status": "completed"
                    })
                else:
                    # File failed to process
                    processed_files.append({
                        "file_id": vector_file.file_id,
                        "s3_key": vector_file.s3_key,
                        "filename": vector_file.filename,
                        "content_type": vector_file.content_type,
                        "file_size": vector_file.file_size,
                        "processing_status": "failed"
                    })
            
            vector_references = {
                "collection_id": collection.id,
                "conversation_id": conversation_id,
                "total_files": len(vector_files),
                "processed_files": processed_files,
                "failed_files": [pf for pf in processed_files if pf["processing_status"] == "failed"],
                "processing_status": "completed",
                "processing_time": result.processing_time,
                "total_document_chunks": result.total_document_chunks
            }
            
            logger.info(f"Successfully processed {len(processed_files)} vector files")
            logger.info(f"Created {result.total_document_chunks} document chunks in {result.processing_time:.2f}s")
            
            return vector_references
            
        except Exception as e:
            logger.error(f"Error processing vector files: {e}")
            # Return error status but don't fail the entire operation
            return {
                "total_files": len(vector_files),
                "processed_files": [],
                "failed_files": [
                    {
                        "file_id": vf.file_id,
                        "s3_key": vf.s3_key,
                        "filename": vf.filename,
                        "processing_status": "failed",
                        "error_message": str(e)
                    }
                    for vf in vector_files
                ],
                "processing_status": "failed",
                "error_message": str(e)
            }
    
    async def get_openai_file_ids_from_attachments(
        self, 
        attachments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract OpenAI file IDs from message attachments for context building
        (Unchanged from existing implementation)
        """
        if not attachments:
            return []
        
        openai_file_ids = []
        for attachment in attachments:
            if isinstance(attachment, dict) and "openai_file_id" in attachment:
                openai_file_ids.append(attachment["openai_file_id"])
        
        logger.debug(f"Extracted {len(openai_file_ids)} OpenAI file IDs from {len(attachments)} attachments")
        return openai_file_ids
    
    async def validate_staging_collection(
        self, 
        staging_collection: StagingFileCollection
    ) -> Dict[str, Any]:
        """
        Validate staging collection (replaces old validation logic)
        """
        logger.info(f"Validating staging collection with {staging_collection.total_count} files")
        
        if staging_collection.is_empty:
            return {"valid": True, "errors": [], "warnings": []}
        
        errors = []
        warnings = []
        
        # Check for unknown files
        if staging_collection.unknown_count > 0:
            warnings.append(f"{staging_collection.unknown_count} unknown/unprocessable files will be ignored")
        
        # Validate file IDs and S3 keys
        for file_info in staging_collection.get_all_files():
            if not file_info.file_id:
                errors.append(f"File missing file_id: {file_info.filename}")
            
            if not file_info.s3_key:
                errors.append(f"File missing s3_key: {file_info.filename}")
            
            # Validate file_id format based on type
            if file_info.is_image and not file_info.file_id.startswith("img_"):
                errors.append(f"Image file_id must start with 'img_': {file_info.file_id}")
            
            # S3 key validation
            if not file_info.s3_key.startswith("files/"):
                errors.append(f"S3 key must start with 'files/': {file_info.s3_key}")
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "total_files": staging_collection.total_count,
                "processable_files": len(staging_collection.get_processable_files()),
                "image_files": staging_collection.image_count,
                "vector_files": staging_collection.vector_count,
                "unknown_files": staging_collection.unknown_count
            }
        }
        
        if errors:
            logger.warning(f"Validation failed with {len(errors)} errors")
        else:
            logger.info("Staging collection validation passed")
        
        return result 