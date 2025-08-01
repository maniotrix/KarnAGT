"""
File Proxy Service
Utility service for generating and managing file proxy URLs
"""

from typing import Optional, Dict, Any, List
from app.core.file_proxy_constants import (
    build_image_proxy_url,
    build_knowledge_proxy_url,
    FileProxyType,
    ContextFileKeys,
    FileProxyConfig
)
from app.logging.logger import get_logger

logger = get_logger(__name__)

class FileProxyService:
    """
    Service for generating file proxy URLs and managing file context
    
    This service provides a centralized way to generate proxy URLs
    that can be consumed by code execution sessions while maintaining
    security through the proxy endpoints.
    
    """
    
    def generate_image_proxy_url(
        self,
        file_id: str, 
        download: Optional[bool] = None,
        filename: Optional[str] = None,
        cache_duration: Optional[int] = None
    ) -> str:
        """
        Generate proxy URL for image file
        
        Args:
            file_id: Image file ID (e.g., img_abc123)
            download: Force download vs inline display
            filename: Override filename for download
            cache_duration: Cache duration in seconds
            
        Returns:
            Complete proxy URL for image file
        """
        try:
            query_params = {}
            
            if download is not None:
                query_params['download'] = str(download).lower()
            
            if filename:
                query_params['filename'] = filename
                
            if cache_duration is not None:
                query_params['cache'] = str(cache_duration)
            
            url = build_image_proxy_url(file_id, **query_params)
            logger.debug(f"Generated image proxy URL: {file_id} -> {url}")
            return url
        except Exception as e:
            logger.error(f"Error generating image proxy URL: {e}")
            return ""
    
    def generate_knowledge_proxy_url(
        self,
        knowledge_file_id: str,
        download: Optional[bool] = None,
        filename: Optional[str] = None,
        cache_duration: Optional[int] = None
    ) -> str:
        """
        Generate proxy URL for knowledge file
        
        Args:
            knowledge_file_id: Knowledge file database ID
            download: Force download vs inline display
            filename: Override filename for download
            cache_duration: Cache duration in seconds
            
        Returns:
            Complete proxy URL for knowledge file
        """
        try:
            query_params = {}
            
            if download is not None:
                query_params['download'] = str(download).lower()
            
            if filename:
                query_params['filename'] = filename
                
            if cache_duration is not None:
                query_params['cache'] = str(cache_duration)
            
            url = build_knowledge_proxy_url(knowledge_file_id, **query_params)
            logger.debug(f"Generated knowledge proxy URL: {knowledge_file_id} -> {url}")
            return url
        except Exception as e:
            logger.error(f"Error generating knowledge proxy URL: {e}")
            return ""
    
    def build_image_attachments_with_proxy_urls(
        self,
        attachments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build image context with proxy URLs for code execution
        
        Args:
            attachments: List of image attachment dictionaries
            
        Returns:
            Enhanced attachments with proxy URLs
        """
        if not attachments:
            return []
        
        enhanced_attachments = []
        
        for attachment in attachments:
            file_id = attachment.get(ContextFileKeys.IMAGE_FILE_ID)
            filename = attachment.get(ContextFileKeys.IMAGE_FILENAME, "image")
            
            if not file_id:
                logger.warning(f"Skipping attachment without file_id: {attachment}")
                continue
            
            # Generate proxy URL for this image
            proxy_url = self.generate_image_proxy_url(
                file_id=file_id,
                filename=filename,
                cache_duration=FileProxyConfig.DEFAULT_CACHE_DURATION
            )
            
            # Build enhanced context
            enhanced_attachment = {
                ContextFileKeys.IMAGE_FILE_ID: file_id,
                ContextFileKeys.IMAGE_OPENAI_FILE_ID: attachment.get(ContextFileKeys.IMAGE_OPENAI_FILE_ID),
                ContextFileKeys.IMAGE_FILENAME: filename,
                ContextFileKeys.IMAGE_DOWNLOAD_URL: proxy_url,
                ContextFileKeys.IMAGE_CONTENT_TYPE: attachment.get(ContextFileKeys.IMAGE_CONTENT_TYPE, "image/jpeg"),
                ContextFileKeys.FILE_SIZE: attachment.get(ContextFileKeys.FILE_SIZE)
            }
            
            # Add any additional fields from original attachment
            for key, value in attachment.items():
                if key not in enhanced_attachment and value is not None:
                    enhanced_attachment[key] = value
            
            enhanced_attachments.append(enhanced_attachment)
        
        logger.info(f"Enhanced {len(enhanced_attachments)} image attachments with proxy URLs")
        return enhanced_attachments
    
    def build_knowledge_attachments_with_proxy_urls(
        self,
        vector_file_references: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build knowledge file context with proxy URLs for code execution
        
        Args:
            vector_file_references: Vector file references from attachment service
            
        Returns:
            Enhanced knowledge files with proxy URLs
        """
        if not vector_file_references or not vector_file_references.get("processed_files"):
            return []
        
        enhanced_files = []
        
        for file_info in vector_file_references["processed_files"]:
            if file_info.get(ContextFileKeys.PROCESSING_STATUS) != "completed":
                logger.debug(f"Skipping incomplete file: {file_info}")
                continue
            
            knowledge_file_id = file_info.get(ContextFileKeys.KNOWLEDGE_FILE_ID)
            filename = file_info.get(ContextFileKeys.KNOWLEDGE_FILENAME, "document")
            
            if not knowledge_file_id:
                logger.warning(f"Skipping knowledge file without ID: {file_info}")
                continue
            
            # Generate proxy URL for this knowledge file
            proxy_url = self.generate_knowledge_proxy_url(
                knowledge_file_id=knowledge_file_id,
                filename=filename,
                cache_duration=FileProxyConfig.DEFAULT_CACHE_DURATION
            )
            
            # Build enhanced context
            enhanced_file = {
                ContextFileKeys.KNOWLEDGE_FILE_ID: knowledge_file_id,
                ContextFileKeys.KNOWLEDGE_REF_DOC_IDS: file_info.get(ContextFileKeys.KNOWLEDGE_REF_DOC_IDS, []),
                ContextFileKeys.KNOWLEDGE_FILENAME: filename,
                ContextFileKeys.KNOWLEDGE_DOWNLOAD_URL: proxy_url,
                ContextFileKeys.KNOWLEDGE_CONTENT_TYPE: file_info.get(ContextFileKeys.KNOWLEDGE_CONTENT_TYPE, "application/octet-stream"),
                ContextFileKeys.KNOWLEDGE_NODE_COUNT: file_info.get(ContextFileKeys.KNOWLEDGE_NODE_COUNT, 0),
                ContextFileKeys.FILE_SIZE: file_info.get(ContextFileKeys.FILE_SIZE),
                ContextFileKeys.PROCESSING_STATUS: file_info.get(ContextFileKeys.PROCESSING_STATUS)
            }
            
            # Add any additional fields from original file info
            for key, value in file_info.items():
                if key not in enhanced_file and value is not None:
                    enhanced_file[key] = value
            
            enhanced_files.append(enhanced_file)
        
        logger.info(f"Enhanced {len(enhanced_files)} knowledge files with proxy URLs")
        return enhanced_files
    
    def build_both_image_and_knowledge_attachments_with_proxy_urls(
        self,
        attachments: Optional[List[Dict[str, Any]]] = None,
        vector_file_references: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build complete file context with proxy URLs for both images and knowledge files
        
        Args:
            attachments: Image attachments from message
            vector_file_references: Vector file references from attachment service
            
        Returns:
            Complete context with proxy URLs for code execution
        """
        context = {}
        
        # Process images
        if attachments:
            enhanced_images = self.build_image_attachments_with_proxy_urls(attachments)
            if enhanced_images:
                context["images"] = enhanced_images
        
        # Process knowledge files
        if vector_file_references:
            enhanced_knowledge = self.build_knowledge_attachments_with_proxy_urls(vector_file_references)
            if enhanced_knowledge:
                context["knowledge_files"] = enhanced_knowledge
        
        # Add metadata
        context["proxy_metadata"] = {
            "service_version": "1.0",
            "total_images": len(context.get("images", [])),
            "total_knowledge_files": len(context.get("knowledge_files", [])),
            "cache_duration": FileProxyConfig.DEFAULT_CACHE_DURATION
        }
        
        logger.info(f"Built complete file context: {context['proxy_metadata']}")
        return context
    


# Note: Service methods require FastAPI Request object for dynamic URL generation
# Usage: service = FileProxyService(); url = service.generate_image_proxy_url(request, file_id)