"""Memory-Aware Context Builder - Extends ConversationContextBuilder with user memories"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.context.conversation_context_builder import ConversationContextBuilder, ConversationContextConfig
from app.services.memory.memory_service import MemoryService
from app.models.database.user_memory import UserMemory
from aicore.logger import get_logger

logger = get_logger(__name__)


class MemoryAwareContextBuilder(ConversationContextBuilder):
    """
    Enhanced context builder that includes user memories in conversation context
    
    Extends the existing ConversationContextBuilder to add user memory retrieval
    and formatting for LLM consumption.
    """
    
    def __init__(
        self, 
        config: ConversationContextConfig, 
        db_session: AsyncSession, 
        conversation_id: str,
        user_id: int
    ):
        """
        Initialize memory-aware context builder
        
        Args:
            config: Conversation context configuration
            db_session: Database session
            conversation_id: Current conversation ID
            user_id: User ID for memory retrieval
        """
        super().__init__(config, db_session, conversation_id)
        self.user_id = user_id
        self.memory_service = MemoryService(db_session)
    
    async def build_context_dict(self, latest_user_message: str) -> Dict[str, Any]:
        """
        Enhanced context building with user memories
        
        Args:
            latest_user_message: The latest user message to include in context
            
        Returns:
            Dictionary with enhanced context including memories:
            {
                "summary_old_messages": str or None,
                "recent_conversation_history": List[Dict[str, str]],
                "user_input": str,
                "overflow": bool,
                "user_memories": Dict[str, Any]  # NEW
            }
        """
        
        # Get base context from parent class
        context_dict = await super().build_context_dict(latest_user_message)
        
        # Add user memories if memory system is enabled
        if await self._is_memory_enabled():
            try:
                memory_context = await self._build_memory_context(latest_user_message)
                context_dict["user_memories"] = memory_context
                
                logger.debug(f"Added memory context with {len(memory_context)} buckets for user {self.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to build memory context for user {self.user_id}: {e}")
                context_dict["user_memories"] = {}
        else:
            context_dict["user_memories"] = {}
        
        return context_dict
    
    async def _build_memory_context(self, user_message: str) -> Dict[str, Any]:
        """
        Build memory context for current query
        
        Args:
            user_message: Current user message to find relevant memories
            
        Returns:
            Dictionary with memory context organized by bucket
        """
        
        memory_context = {}
        
        # Get memories organized for context
        context_memories = await self.memory_service.get_memories_for_context(
            self.user_id, 
            user_message, 
            max_memories=10
        )
        
        # Format memories by bucket
        for bucket, memories in context_memories.items():
            if memories:
                formatted_memories = []
                for memory in memories:
                    formatted_memory = {
                        "content": memory.content,
                        "importance": memory.importance,
                        "created_at": memory.created_at.isoformat(),
                        "bucket": memory.bucket
                    }
                    
                    # Add bucket-specific fields
                    if memory.bucket == "goals" and memory.status:
                        formatted_memory["status"] = memory.status
                    elif memory.bucket == "social" and memory.relationship_strength:
                        formatted_memory["relationship"] = memory.relationship_strength
                    
                    formatted_memories.append(formatted_memory)
                
                memory_context[bucket] = formatted_memories
        
        return memory_context
    
    def format_memory_context_for_llm(self, memory_context: Dict[str, Any]) -> str:
        """
        Format memory context into LLM-friendly string
        
        Args:
            memory_context: Memory context dictionary from _build_memory_context
            
        Returns:
            Formatted string for LLM consumption
        """
        
        if not memory_context:
            return ""
        
        sections = []
        
        # Identity section (highest priority)
        if "identity" in memory_context:
            identity_facts = [m["content"] for m in memory_context["identity"]]
            sections.append(f"USER IDENTITY: {'; '.join(identity_facts)}")
        
        # Preferences section
        if "preferences" in memory_context:
            preferences = [m["content"] for m in memory_context["preferences"]]
            sections.append(f"USER PREFERENCES: {'; '.join(preferences)}")
        
        # Active goals section
        if "goals" in memory_context:
            goals = []
            for goal in memory_context["goals"]:
                status = goal.get("status", "active")
                goals.append(f"{goal['content']} ({status})")
            sections.append(f"USER GOALS: {'; '.join(goals)}")
        
        # Capabilities section
        if "capabilities" in memory_context:
            capabilities = [m["content"] for m in memory_context["capabilities"]]
            sections.append(f"USER CAPABILITIES: {'; '.join(capabilities)}")
        
        # Workflows section
        if "workflows" in memory_context:
            workflows = [m["content"] for m in memory_context["workflows"]]
            sections.append(f"USER WORKFLOWS: {'; '.join(workflows)}")
        
        # Social connections section
        if "social" in memory_context:
            contacts = []
            for contact in memory_context["social"]:
                relationship = contact.get("relationship", "")
                if relationship:
                    contacts.append(f"{contact['content']} ({relationship})")
                else:
                    contacts.append(contact['content'])
            sections.append(f"USER CONTACTS: {'; '.join(contacts)}")
        
        # Other memories
        if "other" in memory_context:
            other = [m["content"] for m in memory_context["other"]]
            sections.append(f"OTHER RELEVANT INFO: {'; '.join(other)}")
        
        return "\n".join(sections)
    
    async def build_memory_enhanced_llm_context(self, latest_user_message: str) -> str:
        """
        Build complete LLM context with memories integrated
        
        Args:
            latest_user_message: Latest user message
            
        Returns:
            Complete formatted context string for LLM
        """
        
        # Get structured context
        context_dict = await self.build_context_dict(latest_user_message)
        
        # Build context sections
        context_sections = []
        
        # Add memory context first (most important)
        if context_dict.get("user_memories"):
            memory_section = self.format_memory_context_for_llm(context_dict["user_memories"])
            if memory_section:
                context_sections.append("=== USER MEMORY CONTEXT ===")
                context_sections.append(memory_section)
                context_sections.append("")  # Blank line
        
        # Add conversation summary if exists
        if context_dict.get("summary_old_messages"):
            context_sections.append("=== CONVERSATION SUMMARY ===")
            context_sections.append(context_dict["summary_old_messages"])
            context_sections.append("")
        
        # Add recent conversation history
        if context_dict.get("recent_conversation_history"):
            context_sections.append("=== RECENT CONVERSATION ===")
            for msg in context_dict["recent_conversation_history"]:
                role = msg["role"].title()
                context_sections.append(f"{role}: {msg['content']}")
            context_sections.append("")
        
        # Add current user input
        context_sections.append("=== CURRENT USER INPUT ===")
        context_sections.append(f"User: {context_dict['user_input']}")
        
        formatted_context = "\n".join(context_sections)
        
        # Log context statistics
        total_memories = sum(
            len(memories) for memories in context_dict.get("user_memories", {}).values()
        )
        logger.debug(f"Built LLM context: {len(formatted_context)} chars, {total_memories} memories, overflow={context_dict.get('overflow', False)}")
        
        return formatted_context
    
    async def _is_memory_enabled(self) -> bool:
        """Check if memory is enabled for this user"""
        
        try:
            # Check user's global memory setting
            # For MVP, assume memory is enabled if user has any memory preferences
            config = await self.memory_service.get_user_memory_stats(self.user_id)
            return config.get("total_memories", 0) >= 0  # Always true for MVP
            
        except Exception as e:
            logger.error(f"Error checking memory status for user {self.user_id}: {e}")
            return False
    
    def _is_goal_related_query(self, query: str) -> bool:
        """Simple heuristic to detect goal-related queries"""
        goal_keywords = [
            "goal", "project", "plan", "objective", "target", 
            "working on", "building", "learning", "studying",
            "progress", "status", "update"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in goal_keywords)
    
    def _is_technical_query(self, query: str) -> bool:
        """Detect if query is technical and might need capability info"""
        technical_keywords = [
            "code", "programming", "development", "technical", "implement",
            "build", "create", "system", "algorithm", "database", "api"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in technical_keywords)


# Convenience functions for integration

async def get_memory_enhanced_context(
    conversation_id: str, 
    user_id: int,
    db_session: AsyncSession, 
    latest_user_message: str,
    config: Optional[ConversationContextConfig] = None
) -> Dict[str, Any]:
    """
    Get memory-enhanced context for a conversation
    
    Args:
        conversation_id: Conversation ID
        user_id: User ID for memory retrieval
        db_session: Database session
        latest_user_message: Latest user message
        config: Optional context configuration
        
    Returns:
        Dictionary with enhanced context including memories
    """
    
    if config is None:
        from app.services.context.conversation_context_builder import get_default_conversation_context_config
        config = get_default_conversation_context_config()
    
    context_builder = MemoryAwareContextBuilder(
        config, db_session, conversation_id, user_id
    )
    
    return await context_builder.build_context_dict(latest_user_message)


async def get_memory_enhanced_llm_context(
    conversation_id: str, 
    user_id: int,
    db_session: AsyncSession, 
    latest_user_message: str,
    config: Optional[ConversationContextConfig] = None
) -> str:
    """
    Get complete LLM-ready context with memories
    
    Args:
        conversation_id: Conversation ID
        user_id: User ID for memory retrieval
        db_session: Database session
        latest_user_message: Latest user message
        config: Optional context configuration
        
    Returns:
        Formatted context string ready for LLM consumption
    """
    
    if config is None:
        from app.services.context.conversation_context_builder import get_default_conversation_context_config
        config = get_default_conversation_context_config()
    
    context_builder = MemoryAwareContextBuilder(
        config, db_session, conversation_id, user_id
    )
    
    return await context_builder.build_memory_enhanced_llm_context(latest_user_message) 