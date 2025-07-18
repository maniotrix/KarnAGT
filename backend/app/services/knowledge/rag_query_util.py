from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# NEW FUNCTIONS FOR DOCUMENT-SPECIFIC QUERYING

async def query_specific_vector_documents(
    self,
    user_id: str,
    conversation_id: str,
    query: str,
    ref_doc_ids: List[str], # vector collection ref_doc_ids
    db: AsyncSession,
    include_inactive: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Query specific vector documents by their ref_doc_ids.
    
    This is the main function you'll use - just pass the ref_doc_ids directly.
    """
    if not ref_doc_ids:
        logger.warning("No ref_doc_ids provided")
        return None
    
    logger.info(f"Querying {len(ref_doc_ids)} specific vector documents in conversation {conversation_id}")
    logger.info(f"ref_doc_ids: {ref_doc_ids}")
    
    try:
        # Import the ProductionRAGService
        from app.services.knowledge.production_rag_service import ProductionRAGService
        from app.services.knowledge.config import RAGConfig
        
        # Create RAG service instance
        rag_config = RAGConfig.for_chat_application()
        rag_service = ProductionRAGService(rag_config)
        
        # Query using the new document filtering - simple and direct
        result = await rag_service.query_conversation_with_documents(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            document_ids=ref_doc_ids,  # Use ref_doc_ids directly
            db=db,
            include_inactive=include_inactive
        )
        
        if result:
            return {
                "query": query,
                "ref_doc_ids": ref_doc_ids,
                "response": result.response,
                "sources": result.sources,
                "query_time": result.query_time,
                "total_nodes_retrieved": result.total_nodes_retrieved
            }
        else:
            return {
                "query": query,
                "ref_doc_ids": ref_doc_ids,
                "result": None,
                "error": "Query returned no results"
            }
            
    except Exception as e:
        logger.error(f"Error querying specific vector documents: {e}")
        return {
            "query": query,
            "ref_doc_ids": ref_doc_ids,
            "error": str(e)
        }

async def get_conversation_vector_docs_list(
    self,
    user_id: str,
    conversation_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Get list of all available vector documents in a conversation.
    
    Returns document metadata including ref_doc_ids for filtering.
    """
    try:
        from app.services.knowledge.production_rag_service import ProductionRAGService
        from app.services.knowledge.config import RAGConfig
        
        # Create RAG service instance
        rag_config = RAGConfig.for_chat_application()
        rag_service = ProductionRAGService(rag_config)
        
        # Get available documents
        documents = await rag_service.get_available_documents_in_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            db=db
        )
        
        logger.info(f"Found {len(documents)} vector documents in conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "total_vector_docs": len(documents),
            "vector_docs": documents  # Each has ref_doc_id for direct use
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation vector docs list: {e}")
        return {
            "conversation_id": conversation_id,
            "total_vector_docs": 0,
            "vector_docs": [],
            "error": str(e)
        }

async def query_documents_by_filename(
    self,
    user_id: str,
    conversation_id: str,
    query: str,
    file_names: List[str],
    db: AsyncSession,
    include_inactive: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Query documents by their file names - finds ref_doc_ids and queries those.
    
    Just a convenience method that finds ref_doc_ids by filename.
    """
    if not file_names:
        logger.warning("No file names provided")
        return None
    
    try:
        from app.services.knowledge.production_rag_service import ProductionRAGService
        from app.services.knowledge.config import RAGConfig
        
        # Create RAG service instance
        rag_config = RAGConfig.for_chat_application()
        rag_service = ProductionRAGService(rag_config)
        
        # Get available documents
        available_docs = await rag_service.get_available_documents_in_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            db=db
        )
        
        # Find ref_doc_ids by file name
        ref_doc_ids = []
        matched_files = {}
        
        for doc in available_docs:
            for file_name in file_names:
                if file_name.lower() in doc["file_name"].lower():
                    ref_doc_ids.append(doc["ref_doc_id"])
                    matched_files[file_name] = doc["ref_doc_id"]
                    break
        
        if not ref_doc_ids:
            return {
                "query": query,
                "file_names_requested": file_names,
                "ref_doc_ids_found": [],
                "error": "No matching files found"
            }
        
        # Now use the main function with ref_doc_ids
        return await self.query_specific_vector_documents(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            ref_doc_ids=ref_doc_ids,
            db=db,
            include_inactive=include_inactive
        )
        
    except Exception as e:
        logger.error(f"Error querying documents by filename: {e}")
        return {
            "query": query,
            "file_names_requested": file_names,
            "error": str(e)
        } 