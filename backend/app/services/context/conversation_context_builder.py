from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.context.ai_context_agent import ConversationSummarizerAgent, summarize_conversation_async
from app.services.context.utils import count_tokens
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from app.logging.logger import get_logger
import json
from app.services.file_proxy_service import FileProxyService

logger = get_logger(__name__)

# TODO : optimissation strategy for context builder, maybe use redis to store the context and update it when needed
# instead of building the context from scratch every time

@dataclass
class ConversationContextConfig:
    """Configuration for conversation context building"""
    summary_length: str = "comprehensive"
    summary_max_tokens: int = 1000
    fixed_llm_conversation_tokens: int = 40000
    
    
@dataclass
class ImageDataContext:
    """Image data context"""
    image_file_id: str
    openai_file_id: str
    filename: str
    image_file_url: str
    
@dataclass
class KnowledgeDataContext:
    """Knowledge data context"""
    knowledge_file_id: str
    filename: str
    knowledge_file_url: str
    

def get_default_conversation_context_config() -> ConversationContextConfig:
    return ConversationContextConfig(
        summary_length="comprehensive",
        summary_max_tokens=1000,
        fixed_llm_conversation_tokens=40000
    )
    
    
class ConversationContextBuilder:
    def __init__(self, config: ConversationContextConfig, db_session: AsyncSession, conversation_id: str):
        self.config = config
        self.db_session = db_session
        self.conversation_id = conversation_id
        self.summarizer = ConversationSummarizerAgent()
        self.file_proxy_service = FileProxyService()
        

    async def build_context(self, latest_user_message: str, openai_file_ids: Optional[List[str]] = None, vector_file_references: Optional[Dict[str, Any]] = None, last_user_message_saved_in_db: bool = True) -> List[Dict[str, Any]]:
        """
        Build conversation context with intelligent summarization when needed.
        
        Args:
            latest_user_message: The user message to include in context
            openai_file_ids: Optional list of OpenAI file IDs for images
            vector_file_references: Optional vector file references for knowledge files
            last_user_message_saved_in_db: If True, the latest_user_message is already in DB and should be excluded from history
        
        Returns a list of messages formatted for LLM consumption:
        [
            {summary of conversation history if needed},
            {user-assistant message pairs within token limit},
            {"role": "user", "content": "latest user message" or multimodal content}
        ]
        """
        logger.info(f"Building context for conversation {self.conversation_id}, last_user_message_saved_in_db={last_user_message_saved_in_db}")
        
        # Extract knowledge data contexts from vector_file_references if provided
        latest_message_knowledge_contexts = []
        if vector_file_references:
            latest_message_knowledge_contexts = self._extract_knowledge_data_contexts_from_vector_references(vector_file_references)
            if latest_message_knowledge_contexts:
                logger.info(f"Extracted {len(latest_message_knowledge_contexts)} knowledge data contexts from latest message")
        
        # Step 1: Get all previous messages from database
        previous_messages, most_recent_user_message = await self._get_conversation_history(exclude_latest_if_user=last_user_message_saved_in_db)
        
        if not previous_messages:
            logger.info("No previous messages found, returning only latest user message")
            # Convert openai_file_ids to ImageDataContext objects
            # Use most_recent_user_message if available and contains the openai_file_ids we need
            latest_message_image_contexts = self._create_image_contexts_from_openai_ids(
                openai_file_ids or [], 
                most_recent_user_message
            )
            
            # Build final user message with images and knowledge files if provided
            final_message = self._build_user_message_with_image_and_knowledge_contexts(
                latest_user_message, 
                latest_message_image_contexts, 
                latest_message_knowledge_contexts
            )
            logger.info(f"Final context built: {len(final_message)} messages, {count_tokens(final_message['content'])} total tokens \n {final_message}")
            return [final_message]
        
        # Step 2: Check if we need summarization
        overflow_index = self._get_overflow_index(previous_messages)
        
        context_messages = []
        
        if overflow_index == -1:
            # No overflow, include all messages
            logger.info("No overflow detected, including all previous messages")
            for message in reversed(previous_messages):  # Reverse to chronological order
                # Extract image data contexts from message attachments
                message_image_contexts = self._extract_image_data_contexts_from_message(message)
                
                # Extract knowledge data contexts from message vector_file_references
                message_knowledge_contexts = self._extract_knowledge_data_contexts_from_message(message)
                
                if message_image_contexts or message_knowledge_contexts:
                    # Build multimodal message with images and/or knowledge files
                    message_dict = self._build_message_with_attachment_and_knowledge_contexts(
                        str(message.role), 
                        str(message.content), 
                        message_image_contexts,
                        message_knowledge_contexts
                    )
                    logger.info(f"Added {message.role} message with {len(message_image_contexts)} images and {len(message_knowledge_contexts)} knowledge files to context")
                else:
                    # Text-only message
                    message_dict = {
                        "role": str(message.role),
                        "content": str(message.content)
                    }
                
                context_messages.append(message_dict)
        else:
            # Overflow detected, need summarization
            logger.info(f"Overflow detected, summarizing messages from index {overflow_index} onwards")
            
            # Messages that need summarization (from overflow_index to end)
            messages_to_summarize = previous_messages[overflow_index:]
            
            # Messages to keep as-is (recent messages within token limit)
            recent_messages = previous_messages[:overflow_index]
            
            logger.info(f"Summarizing {len(messages_to_summarize)} messages, keeping {len(recent_messages)} recent messages")
            
            # Create conversation history for summarization (in chronological order)
            conversation_history = []
            for message in reversed(messages_to_summarize):
                conversation_history.append({
                    "role": str(message.role),
                    "content": str(message.content)
                })
            
            # Generate summary
            if conversation_history:
                summary = await self._summarize_old_messages([conversation_history])
                context_messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}"
                })
                logger.info(f"Added conversation summary ({count_tokens(summary)} tokens)")
            
            # Add recent messages in chronological order
            for message in reversed(recent_messages):
                # Extract image data contexts from message attachments
                message_image_contexts = self._extract_image_data_contexts_from_message(message)
                
                # Extract knowledge data contexts from message vector_file_references
                message_knowledge_contexts = self._extract_knowledge_data_contexts_from_message(message)
                
                if message_image_contexts or message_knowledge_contexts:
                    # Build multimodal message with images and/or knowledge files
                    message_dict = self._build_message_with_attachment_and_knowledge_contexts(
                        str(message.role), 
                        str(message.content), 
                        message_image_contexts,
                        message_knowledge_contexts
                    )
                    logger.info(f"Added {message.role} message with {len(message_image_contexts)} images and {len(message_knowledge_contexts)} knowledge files to context")
                else:
                    # Text-only message
                    message_dict = {
                        "role": str(message.role),
                        "content": str(message.content)
                    }
                
                context_messages.append(message_dict)
        
        # Step 3: Add the latest user message with images and knowledge files
        # Convert openai_file_ids to ImageDataContext objects
        # Use most_recent_user_message if available and contains the openai_file_ids we need
        latest_message_image_contexts = self._create_image_contexts_from_openai_ids(
            openai_file_ids or [], 
            most_recent_user_message
        )
        
        final_message = self._build_user_message_with_image_and_knowledge_contexts(
            latest_user_message, 
            latest_message_image_contexts, 
            latest_message_knowledge_contexts
        )
        context_messages.append(final_message)
        
        # Log final context statistics
        total_context_tokens = sum(count_tokens(msg["content"] if isinstance(msg["content"], str) else latest_user_message) for msg in context_messages)
        
        # Safely log the context to avoid Unicode encoding issues
        try:
            import json
            context_str = ""
            context_str = json.dumps(context_messages, ensure_ascii=False, indent=2)
            logger.info(f"Final context built: {len(context_messages)} messages, {total_context_tokens} total tokens\n{context_str}")
        except Exception as e:
            logger.warning(f"Final context logging issue: {e}")
        
        return context_messages


    async def build_context_dict(self, latest_user_message: str, openai_file_ids: Optional[List[str]] = None, vector_file_references: Optional[Dict[str, Any]] = None, last_user_message_saved_in_db: bool = True) -> Dict[str, Any]:
        """
        Build conversation context as a structured dictionary with separate components.
        
        Args:
            latest_user_message: The latest user message to include in context
            openai_file_ids: Optional list of OpenAI file IDs for images
            vector_file_references: Optional vector file references for knowledge files
            last_user_message_saved_in_db: If True, the latest_user_message is already saved in DB
            
        Returns:
            Dictionary with structured context components:
            {
                "summary_old_messages": str or None,
                "recent_conversation_history": List[Dict[str, str]],
                "user_input": str,
                "overflow": bool
            }
        """
        logger.info(f"Building structured context dict for conversation {self.conversation_id}")
        
        # Step 1: Get all previous messages from database (excluding the current message)
        # For build_context_dict, we assume the message is already saved since this is used for structured output
        previous_messages, most_recent_user_message = await self._get_conversation_history(exclude_latest_if_user=last_user_message_saved_in_db)
        
        # Step 2: Process latest user message with images and knowledge files
        knowledge_contexts = []
        if vector_file_references:
            knowledge_contexts = self._extract_knowledge_data_contexts_from_vector_references(vector_file_references)
        
        # Convert openai_file_ids to ImageDataContext objects
        # Use most_recent_user_message if available and contains the openai_file_ids we need
        image_contexts = self._create_image_contexts_from_openai_ids(
            openai_file_ids or [], 
            most_recent_user_message
        )
        
        # Build latest user message with attachments
        user_input = self._build_user_message_with_image_and_knowledge_contexts(
            latest_user_message, 
            image_contexts, 
            knowledge_contexts
        )
        
        # Initialize context structure with proper typing
        context_dict: Dict[str, Any] = {
            "summary_old_messages": None,
            "recent_conversation_history": [],
            "user_input": user_input,
            "overflow": False
        }
        
        if not previous_messages:
            logger.info("No previous messages found, returning empty history")
            return context_dict
        
        # Step 2: Check if we need summarization
        overflow_index = self._get_overflow_index(previous_messages)
        
        if overflow_index == -1:
            # No overflow, include all messages as recent history
            logger.info("No overflow detected, including all previous messages as recent history")
            context_dict["overflow"] = False
            
            for message in reversed(previous_messages):  # Reverse to chronological order
                # Extract image data contexts from message attachments
                message_image_contexts = self._extract_image_data_contexts_from_message(message)
                
                # Extract knowledge data contexts from message vector_file_references
                message_knowledge_contexts = self._extract_knowledge_data_contexts_from_message(message)
                
                if message_image_contexts or message_knowledge_contexts:
                    # Build multimodal message with images and knowledge files
                    message_dict = self._build_message_with_attachment_and_knowledge_contexts(
                        str(message.role), 
                        str(message.content), 
                        message_image_contexts,
                        message_knowledge_contexts
                    )
                    attachments_info = []
                    if message_image_contexts:
                        attachments_info.append(f"{len(message_image_contexts)} images")
                    if message_knowledge_contexts:
                        attachments_info.append(f"{len(message_knowledge_contexts)} knowledge files")
                    logger.info(f"Added {message.role} message with {', '.join(attachments_info)} to conversation history")
                else:
                    # Text-only message
                    message_dict = {
                        "role": str(message.role),
                        "content": str(message.content)
                    }
                
                context_dict["recent_conversation_history"].append(message_dict)
        else:
            # Overflow detected, need summarization
            logger.info(f"Overflow detected, summarizing messages from index {overflow_index} onwards")
            context_dict["overflow"] = True
            
            # Messages that need summarization (from overflow_index to end)
            messages_to_summarize = previous_messages[overflow_index:]
            
            # Messages to keep as-is (recent messages within token limit)
            recent_messages = previous_messages[:overflow_index]
            
            logger.info(f"Summarizing {len(messages_to_summarize)} messages, keeping {len(recent_messages)} recent messages")
            
            # Create conversation history for summarization (in chronological order)
            conversation_history = []
            for message in reversed(messages_to_summarize):
                conversation_history.append({
                    "role": str(message.role),
                    "content": str(message.content)
                })
            
            # Generate summary
            if conversation_history:
                summary = await self._summarize_old_messages([conversation_history])
                context_dict["summary_old_messages"] = summary
                logger.info(f"Added conversation summary ({count_tokens(summary)} tokens)")
            
            # Add recent messages as history (in chronological order)
            for message in reversed(recent_messages):
                # Extract image data contexts from message attachments
                message_image_contexts = self._extract_image_data_contexts_from_message(message)
                
                # Extract knowledge data contexts from message vector_file_references
                message_knowledge_contexts = self._extract_knowledge_data_contexts_from_message(message)
                
                if message_image_contexts or message_knowledge_contexts:
                    # Build multimodal message with images and knowledge files
                    message_dict = self._build_message_with_attachment_and_knowledge_contexts(
                        str(message.role), 
                        str(message.content), 
                        message_image_contexts,
                        message_knowledge_contexts
                    )
                    attachments_info = []
                    if message_image_contexts:
                        attachments_info.append(f"{len(message_image_contexts)} images")
                    if message_knowledge_contexts:
                        attachments_info.append(f"{len(message_knowledge_contexts)} knowledge files")
                    logger.info(f"Added {message.role} message with {', '.join(attachments_info)} to conversation history")
                else:
                    # Text-only message
                    message_dict = {
                        "role": str(message.role),
                        "content": str(message.content)
                    }
                
                context_dict["recent_conversation_history"].append(message_dict)
        
        # Log final context statistics
        history_count = len(context_dict["recent_conversation_history"])
        has_summary = context_dict["summary_old_messages"] is not None
        total_tokens = (
            count_tokens(context_dict["summary_old_messages"] or "") +
            sum(count_tokens(msg["content"]) for msg in context_dict["recent_conversation_history"]) +
            count_tokens(context_dict["user_input"])
        )
        
        logger.info(f"Context dict built: {history_count} recent messages, summary={has_summary}, overflow={context_dict['overflow']}, total_tokens={total_tokens}")
        
        return context_dict
    
    def _extract_openai_file_ids_from_message(self, message: 'Message') -> List[str]:
        """Extract OpenAI file IDs from a message's attachments (legacy method for backward compatibility)"""
        image_contexts = self._extract_image_data_contexts_from_message(message)
        return [img_ctx.openai_file_id for img_ctx in image_contexts]
    
    def _extract_image_data_contexts_from_message(self, message: 'Message') -> List[ImageDataContext]:
        """Extract image contexts from a message's attachments"""
        attachments = message.attachments
        if attachments is None or (hasattr(attachments, '__len__') and len(attachments) == 0):
            return []
        
        image_contexts : List[ImageDataContext] = []
        for attachment in attachments:
            if isinstance(attachment, dict) and attachment.get('openai_file_id'):
                file_id = attachment.get('file_id', '')
                image_file_url = self.file_proxy_service.generate_image_proxy_url(file_id)
                
                image_context = ImageDataContext(
                    image_file_id=file_id,
                    openai_file_id=attachment['openai_file_id'],
                    filename=attachment.get('filename', ''),
                    image_file_url=image_file_url
                )
                image_contexts.append(image_context)
        
        return image_contexts

    def _extract_knowledge_file_ids_from_vector_references(self, vector_file_references: Dict[str, Any]) -> List[str]:
        """Extract knowledge file IDs from a vector_file_references dictionary (legacy method for backward compatibility)."""
        knowledge_contexts = self._extract_knowledge_data_contexts_from_vector_references(vector_file_references)
        return [str(kf_ctx.knowledge_file_id) for kf_ctx in knowledge_contexts]
    
    def _extract_knowledge_data_contexts_from_vector_references(self, vector_file_references: Dict[str, Any]) -> List[KnowledgeDataContext]:
        """Extract knowledge contexts from a vector_file_references dictionary."""
        if not vector_file_references or not isinstance(vector_file_references, dict):
            return []
        
        knowledge_contexts : List[KnowledgeDataContext] = []
        processed_files = vector_file_references.get('processed_files', [])
        
        for file_info in processed_files:
            if isinstance(file_info, dict) and 'knowledge_file_id' in file_info:
                knowledge_file_id = file_info['knowledge_file_id']
                knowledge_file_url = self.file_proxy_service.generate_knowledge_proxy_url(knowledge_file_id)
                
                knowledge_context = KnowledgeDataContext(
                    knowledge_file_id=str(knowledge_file_id),  # Convert to string for consistency
                    filename=file_info.get('filename', ''),
                    knowledge_file_url=knowledge_file_url
                )
                knowledge_contexts.append(knowledge_context)
        
        return knowledge_contexts

    def _extract_knowledge_file_ids_from_message(self, message: 'Message') -> List[str]:
        """Extract knowledge file IDs from a message's vector_file_references (legacy method for backward compatibility)."""
        knowledge_contexts = self._extract_knowledge_data_contexts_from_message(message)
        return [kf_ctx.knowledge_file_id for kf_ctx in knowledge_contexts]
    
    def _extract_knowledge_data_contexts_from_message(self, message: 'Message') -> List[KnowledgeDataContext]:
        """Extract knowledge contexts from a message's vector_file_references."""
        vector_file_references = message.vector_file_references
        if vector_file_references is None:
            return []
        
        # Reuse the existing function
        return self._extract_knowledge_data_contexts_from_vector_references(vector_file_references)

    def _create_image_contexts_from_openai_ids(self, openai_file_ids: List[str], message: Optional['Message'] = None) -> List[ImageDataContext]:
        """
        Create ImageDataContext objects from OpenAI file IDs using message attachments.
        
        Args:
            openai_file_ids: List of OpenAI file IDs to create contexts for
            message: Optional message object containing attachments to match against
        """
        image_contexts: List[ImageDataContext] = []
        
        # If we have a message with attachments, use them to populate full context
        if message and message.attachments and (hasattr(message.attachments, '__len__') and len(message.attachments) > 0): # type: ignore
            # Create a lookup map of openai_file_id -> attachment
            attachments_map = {}
            for attachment in message.attachments:
                if isinstance(attachment, dict) and attachment.get('openai_file_id'):
                    attachments_map[attachment['openai_file_id']] = attachment
            
            # Create contexts for matching openai_file_ids
            for openai_file_id in openai_file_ids:
                attachment = attachments_map.get(openai_file_id)
                if attachment:
                    # Build full context with all attachment data
                    image_context = ImageDataContext(
                        image_file_id=attachment.get('file_id', ''),
                        openai_file_id=openai_file_id,
                        filename=attachment.get('filename', ''),
                        image_file_url=self.file_proxy_service.generate_image_proxy_url(attachment.get('file_id', ''))
                    )
                else:
                    # Fallback to minimal context if attachment not found
                    image_context = ImageDataContext(
                        image_file_id="",
                        openai_file_id=openai_file_id,
                        filename="",
                        image_file_url=""
                    )
                image_contexts.append(image_context)
        else:
            # Fallback: create minimal contexts without attachment data
            for openai_file_id in openai_file_ids:
                image_context = ImageDataContext(
                    image_file_id="",
                    openai_file_id=openai_file_id,
                    filename="",
                    image_file_url=""
                )
                image_contexts.append(image_context)
        
        return image_contexts

    def _update_image_context_urls(self, image_contexts: List[ImageDataContext], base_url: str) -> None:
        """
        Update proxy URLs in ImageDataContext objects when base_url is available
        
        Args:
            image_contexts: List of image contexts to update
            base_url: Base URL for constructing proxy URLs
        """
        for img_ctx in image_contexts:
            if img_ctx.image_file_id:
                img_ctx.image_file_url = self.file_proxy_service.generate_image_proxy_url(img_ctx.image_file_id)

    def _update_knowledge_context_urls(self, knowledge_contexts: List[KnowledgeDataContext], base_url: str) -> None:
        """
        Update proxy URLs in KnowledgeDataContext objects when base_url is available
        
        Args:
            knowledge_contexts: List of knowledge contexts to update  
            base_url: Base URL for constructing proxy URLs
        """
        for kf_ctx in knowledge_contexts:
            if kf_ctx.knowledge_file_id:
                kf_ctx.knowledge_file_url = self.file_proxy_service.generate_knowledge_proxy_url(kf_ctx.knowledge_file_id)

    def _build_knowledge_files_data(self, knowledge_contexts: List[KnowledgeDataContext]) -> List[Dict[str, Any]]:
        """Build structured data for knowledge files."""
        knowledge_files : List[Dict[str, Any]] = []
        for idx, kf_ctx in enumerate(knowledge_contexts, start=1):
            knowledge_file = {
                "index": idx,
                "knowledge_file_id": kf_ctx.knowledge_file_id,
                "knowledge_file_name": kf_ctx.filename,
                "knowledge_file_url": kf_ctx.knowledge_file_url
            }
            knowledge_files.append(knowledge_file)
        return knowledge_files

    def _build_image_files_data(self, image_contexts: List[ImageDataContext]) -> List[Dict[str, Any]]:
        """Build structured data for image files."""
        image_files : List[Dict[str, Any]] = []
        for idx, img_ctx in enumerate(image_contexts, start=1):
            image_file = {
                "index": idx,
                "image_file_id": img_ctx.image_file_id,
                "image_file_name": img_ctx.filename,
                "image_file_url": img_ctx.image_file_url,
                "openai_file_id": img_ctx.openai_file_id
            }
            image_files.append(image_file)
        return image_files

    def _create_structured_context_data(
        self, 
        content: str, 
        image_contexts: List[ImageDataContext], 
        knowledge_contexts: List[KnowledgeDataContext]
    ) -> Dict[str, Any]:
        """Create structured data object for user context."""
        structured_data: Dict[str, Any] = {
            "user_query": content,
            "uploaded_files": {}
        }
        
        if knowledge_contexts:
            structured_data["uploaded_files"]["knowledge_files"] = self._build_knowledge_files_data(knowledge_contexts)
        
        if image_contexts:
            structured_data["uploaded_files"]["image_files"] = self._build_image_files_data(image_contexts)
        
        return structured_data

    def _build_enhanced_content(
        self, 
        role: str, 
        content: str, 
        image_contexts: List[ImageDataContext], 
        knowledge_contexts: List[KnowledgeDataContext]
    ) -> str:
        """Build enhanced content with structured context data."""
        if (knowledge_contexts or image_contexts) and role == "user":
            structured_data = self._create_structured_context_data(content, image_contexts, knowledge_contexts)
            return f"User Request Context:\n{json.dumps(structured_data, indent=2)}"
        return content

    def _build_multimodal_content_parts(
        self, 
        enhanced_content: str, 
        image_contexts: List[ImageDataContext]
    ) -> List[Dict[str, Any]]:
        """Build content parts for multimodal messages."""
        content_parts: List[Dict[str, Any]] = []
        
        # Add text content only if it's not empty
        if enhanced_content and enhanced_content.strip():
            content_parts.append({"type": "input_text", "text": enhanced_content})
        
        # Add images using OpenAI file IDs
        for img_ctx in image_contexts:
            content_parts.append({
                "type": "input_image", 
                "file_id": img_ctx.openai_file_id
            })
        
        return content_parts

    def _build_message_with_attachment_and_knowledge_contexts(
        self, 
        role: str, 
        content: str, 
        image_contexts: List[ImageDataContext], 
        knowledge_contexts: List[KnowledgeDataContext]
    ) -> Dict[str, Any]:
        """Build message with optional image and knowledge file contexts for conversation history."""
        enhanced_content = self._build_enhanced_content(role, content, image_contexts, knowledge_contexts)
        
        if not image_contexts:
            # Text-only message (possibly with knowledge file context)
            return {
                "role": role,
                "content": enhanced_content
            }
        
        # Multimodal message with images
        content_parts = self._build_multimodal_content_parts(enhanced_content, image_contexts)
        
        logger.info(f"Built multimodal {role} message with {len(image_contexts)} images and {len(knowledge_contexts)} knowledge files and {'text' if enhanced_content.strip() else 'no text'}")
        return {
            "role": role,
            "content": content_parts
        }

    def _build_user_message_with_image_and_knowledge_contexts(
        self, 
        text_content: str, 
        image_contexts: List[ImageDataContext], 
        knowledge_contexts: List[KnowledgeDataContext]
    ) -> Dict[str, Any]:
        """Build user message with optional image and knowledge file contexts."""
        # Delegate to the generic method with role="user"
        return self._build_message_with_attachment_and_knowledge_contexts(
            role="user",
            content=text_content,
            image_contexts=image_contexts,
            knowledge_contexts=knowledge_contexts
        )

    def _build_message_with_attachments_and_knowledge(self, role: str, content: str, openai_file_ids: List[str], knowledge_file_ids: List[str]) -> Dict[str, Any]:
        """Build message with optional image and knowledge file attachments for conversation history."""
        # Enhance content with knowledge file IDs if present
        enhanced_content = content
        if knowledge_file_ids and role == "user":
            enhanced_content = f"Query: {content}\n\nUser has uploaded files with IDs: {knowledge_file_ids}"
        
        if not openai_file_ids:
            # Text-only message (possibly with knowledge file context)
            return {
                "role": role,
                "content": enhanced_content
            }
        
        # Multimodal message with images
        content_parts = []
        
        # Add text content only if it's not empty
        if enhanced_content and enhanced_content.strip():
            content_parts.append({"type": "input_text", "text": enhanced_content})
        
        # Add images
        for file_id in openai_file_ids:
            content_parts.append({
                "type": "input_image", 
                "file_id": file_id
            })
        
        logger.info(f"Built multimodal {role} message with {len(openai_file_ids)} images and {len(knowledge_file_ids)} knowledge files and {'text' if enhanced_content.strip() else 'no text'}")
        return {
            "role": role,
            "content": content_parts
        }

    def _build_user_message_with_images_and_knowledge(self, text_content: str, openai_file_ids: List[str], knowledge_file_ids: List[str]) -> Dict[str, Any]:
        """Build user message with optional image and knowledge file attachments."""
        # Enhance content with knowledge file IDs if present
        enhanced_content = text_content
        if knowledge_file_ids:
            enhanced_content = f"Query: {text_content}\n\nUser has uploaded files with IDs: {knowledge_file_ids}"
        
        if not openai_file_ids:
            # Text-only message (possibly with knowledge file context)
            return {
                "role": "user",
                "content": enhanced_content
            }
        
        # Multimodal message with images
        content_parts = []
        
        # Add text content only if it's not empty
        if enhanced_content and enhanced_content.strip():
            content_parts.append({"type": "input_text", "text": enhanced_content})
        
        # Add images
        for file_id in openai_file_ids:
            content_parts.append({
                "type": "input_image", 
                "file_id": file_id
            })
        
        logger.info(f"Built multimodal user message with {len(openai_file_ids)} images and {len(knowledge_file_ids)} knowledge files and {'text' if enhanced_content.strip() else 'no text'}")
        return {
            "role": "user",
            "content": content_parts
        }

    def _get_overflow_index(self, messages: List[Message]) -> int:
        """
        Return the index in conversation from where summarization starts.
        
        Args:
            messages: List of messages in reverse chronological order (most recent first)
            
        Returns:
            int: Index where overflow occurs, or -1 if no overflow.
        """
        if not messages:
            logger.debug("No messages provided, returning -1")
            return -1
            
        total_tokens = 0
        token_limit = self.config.fixed_llm_conversation_tokens
        
        logger.info(f"Checking for token overflow with limit: {token_limit} tokens")
        
        # Iterate through messages (they are in reverse chronological order)
        for i, message in enumerate(messages):
            # Count tokens for this message
            message_tokens = count_tokens(str(message.content))
            total_tokens += message_tokens
            
            logger.debug(f"Message {i}: role={message.role}, tokens={message_tokens}, total_tokens={total_tokens}")
            
            # Check if we've exceeded the token limit
            if total_tokens > token_limit:
                logger.info(f"Token overflow detected at index {i}: total_tokens={total_tokens} > limit={token_limit}")
                logger.info(f"Messages from index {i} onwards will need summarization")
                return i
        
        # No overflow occurred
        logger.info("No token overflow detected, returning -1")
        return -1
    
    async def _get_conversation_history(self, exclude_latest_if_user: bool = False) -> Tuple[List[Message], Optional[Message]]:
        """
        Retrieve all messages for the conversation from database, sorted by creation time.
        
        Args:
            exclude_latest_if_user: If True and the most recent message is from user, exclude it
        """
        try:
            
            most_recent_user_message = None
            # First get the conversation by conversation_id string
            query = select(Conversation).where(
                Conversation.conversation_id == self.conversation_id
            )
            result = await self.db_session.execute(query)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                logger.warning(f"Conversation {self.conversation_id} not found")
                return [], None
            
            # Then get messages by the integer ID
            messages_query = select(Message).where(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at.desc())
            
            messages_result = await self.db_session.execute(messages_query)
            all_messages = list(messages_result.scalars().all())
            
            # Optionally skip the most recent user message to avoid duplicates
            if exclude_latest_if_user and all_messages:
                most_recent = all_messages[0]  # Messages are in DESC order, so [0] is newest
                if str(most_recent.role) == "user":
                    most_recent_user_message = most_recent
                    logger.debug(f"Excluding most recent user message to avoid duplicate")
                    return all_messages[1:], most_recent_user_message  # Skip the first message
            
            return all_messages, most_recent_user_message
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return [], None
    
    async def _summarize_old_messages(self, old_pairs: List[List[Dict[str, str]]]) -> str:
        """Summarize old message pairs that exceed the token limit."""
        # Flatten pairs into conversation history format
        conversation_history = []
        for pair in reversed(old_pairs):  # Process in chronological order
            conversation_history.extend(pair)
        
        # Use the summarizer agent
        summary = await summarize_conversation_async(
            conversation_history=conversation_history,
            summary_length=self.config.summary_length,
            max_tokens=self.config.summary_max_tokens
        )
        
        return summary
        

async def get_context_dict_for_conversation(conversation_id: str, db_session: AsyncSession, latest_user_message: str, openai_file_ids: Optional[List[str]] = None, vector_file_references: Optional[Dict[str, Any]] = None, last_user_message_saved_in_db: bool = True) -> Dict[str, Any]:
    """
    Get the structured context dictionary for a conversation.
    
    Returns:
        Dictionary with structured context components:
        {
            "summary_old_messages": str or None,
            "recent_conversation_history": List[Dict[str, str]],
            "user_input": str,
            "overflow": bool
        }
    """
    context_builder = ConversationContextBuilder(get_default_conversation_context_config(), db_session, conversation_id)
    context_dict = await context_builder.build_context_dict(latest_user_message, openai_file_ids, vector_file_references, last_user_message_saved_in_db)
    return context_dict


async def get_context_for_conversation(
    conversation_id: str, 
    db_session: AsyncSession, 
    latest_user_message: str,
    openai_file_ids: Optional[List[str]] = None,
    vector_file_references: Optional[Dict[str, Any]] = None,
    last_user_message_saved_in_db: bool = True
) -> List[Dict[str, Any]]:
    """
    Get context for conversation with optional images as list of message dictionaries
    
    Args:
        conversation_id: The conversation ID
        db_session: Database session
        latest_user_message: The user message to include in context
        openai_file_ids: Optional list of OpenAI file IDs for images
        vector_file_references: Optional vector file references for knowledge files
        last_user_message_saved_in_db: If True, the latest_user_message is already in DB and should be excluded from history
    """
    builder = ConversationContextBuilder(
        get_default_conversation_context_config(), 
        db_session, 
        conversation_id
    )
    
    return await builder.build_context(latest_user_message, openai_file_ids, vector_file_references, last_user_message_saved_in_db)
