"""Memory Extraction Service - Extracts memories from conversations using LLM"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.services.memory.memory_service import MemoryService
from app.models.database.user_memory import UserMemory, MEMORY_BUCKETS
from app.logging.logger import get_logger

logger = get_logger(__name__)


class MemoryExtractor:
    """Service for extracting memories from conversations using LLM"""
    
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service
        
        # Extraction prompts for each bucket
        self.bucket_extraction_prompts = {
            "identity": """
Extract basic identity information from this conversation. Look for:
- Name, pronouns, role/job title
- Location, timezone, age
- Basic biographical information
- Personal identifiers

Return as JSON array of objects with:
{"content": "extracted fact", "importance": 0.0-1.0, "confidence": 0.0-1.0}

Only extract clear, factual identity information. Be conservative.
            """,
            
            "preferences": """
Extract user preferences and communication style from this conversation. Look for:
- Communication preferences (formal/casual, detail level)
- Tool preferences, technology choices
- Format preferences (bullet points, tables, etc.)
- Work style preferences
- Learning preferences

Return as JSON array of objects with:
{"content": "extracted preference", "importance": 0.0-1.0, "confidence": 0.0-1.0}

Focus on explicit preferences the user states or demonstrates.
            """,
            
            "goals": """
Extract goals, projects, or objectives mentioned in this conversation. Look for:
- Short-term and long-term goals
- Active projects being worked on
- Learning objectives
- Career goals
- Personal objectives

Return as JSON array of objects with:
{"content": "extracted goal", "importance": 0.0-1.0, "confidence": 0.0-1.0, "status": "active|planned|completed"}

Only extract clear goals or objectives the user mentions.
            """,
            
            "workflows": """
Extract patterns, workflows, or habits from this conversation. Look for:
- Daily routines or schedules
- Work patterns or methodologies
- Coding patterns or practices
- Regular activities
- Process preferences

Return as JSON array of objects with:
{"content": "extracted workflow/habit", "importance": 0.0-1.0, "confidence": 0.0-1.0}

Focus on recurring patterns or established workflows.
            """,
            
            "capabilities": """
Extract user capabilities, skills, or constraints from this conversation. Look for:
- Technical skills and expertise levels
- Hardware specifications or limitations
- Budget constraints
- Software proficiency
- Language capabilities
- Physical or time constraints

Return as JSON array of objects with:
{"content": "extracted capability/constraint", "importance": 0.0-1.0, "confidence": 0.0-1.0}

Focus on clearly stated capabilities or limitations.
            """,
            
            "social": """
Extract social connections and relationships from this conversation. Look for:
- Names of colleagues, friends, collaborators
- Professional relationships
- Team members or contacts
- Family members (if relevant to context)
- Business connections

Return as JSON array of objects with:
{"content": "extracted contact/relationship", "importance": 0.0-1.0, "confidence": 0.0-1.0, "relationship_type": "professional|personal|family"}

Only extract people explicitly mentioned with clear relationship context.
            """
        }
    
    async def extract_memories_from_conversation(
        self, 
        conversation_messages: List[Dict[str, str]],
        user_id: int,
        conversation_id: str,
        enabled_buckets: Optional[List[str]] = None
    ) -> Dict[str, List[UserMemory]]:
        """
        Extract memories from a conversation across all enabled buckets
        
        Args:
            conversation_messages: List of message dicts with 'role' and 'content'
            user_id: User ID for memory storage
            conversation_id: Conversation ID for source tracking
            enabled_buckets: List of buckets to extract for (None = all)
            
        Returns:
            Dict mapping bucket names to extracted UserMemory objects
        """
        
        if not conversation_messages:
            logger.warning("No messages provided for memory extraction")
            return {}
        
        # Determine which buckets to extract for
        if enabled_buckets is None:
            enabled_buckets = list(MEMORY_BUCKETS.keys())
        
        # Filter out buckets not enabled for this user
        active_buckets = await self._get_user_active_buckets(user_id, enabled_buckets)
        
        if not active_buckets:
            logger.info(f"No active memory buckets for user {user_id}")
            return {}
        
        logger.info(f"Extracting memories for user {user_id} from {len(conversation_messages)} messages across {len(active_buckets)} buckets")
        
        # Format conversation for LLM
        conversation_text = self._format_conversation_for_extraction(conversation_messages)
        
        # Extract memories for each bucket
        extracted_memories = {}
        
        # Process buckets in parallel for efficiency
        extraction_tasks = []
        for bucket in active_buckets:
            task = self._extract_bucket_memories(
                conversation_text, 
                bucket, 
                user_id, 
                conversation_id
            )
            extraction_tasks.append((bucket, task))
        
        # Execute all extractions concurrently
        results = await asyncio.gather(*[task for _, task in extraction_tasks], return_exceptions=True)
        
        # Collect results
        for i, (bucket, _) in enumerate(extraction_tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Failed to extract memories for bucket {bucket}: {result}")
                extracted_memories[bucket] = []
            else:
                extracted_memories[bucket] = result
                logger.info(f"Extracted {len(result)} memories for bucket {bucket}")
        
        return extracted_memories
    
    async def _extract_bucket_memories(
        self, 
        conversation_text: str, 
        bucket: str, 
        user_id: int, 
        conversation_id: str
    ) -> List[UserMemory]:
        """Extract memories for a specific bucket"""
        
        prompt = self.bucket_extraction_prompts.get(bucket)
        if not prompt:
            logger.error(f"No extraction prompt for bucket: {bucket}")
            return []
        
        try:
            # Call LLM for extraction
            extraction_result = await self._llm_extract(
                prompt, 
                conversation_text, 
                bucket
            )
            
            if not extraction_result:
                return []
            
            # Convert LLM response to UserMemory objects
            memories = []
            for item in extraction_result:
                if not item.get("content") or not item["content"].strip():
                    continue
                
                # Create memory object
                memory_data = {
                    "user_id": user_id,
                    "bucket": bucket,
                    "content": item["content"].strip(),
                    "importance": item.get("importance", 0.5),
                    "confidence": item.get("confidence", 0.8),
                    "source_conversation_id": conversation_id,
                    "extraction_method": "auto"
                }
                
                # Add bucket-specific data
                if bucket == "goals" and "status" in item:
                    memory_data["status"] = item["status"]
                elif bucket == "social" and "relationship_type" in item:
                    memory_data["relationship_strength"] = item["relationship_type"]
                
                # Store memory through the service
                try:
                    stored_memory = await self.memory_service.store_memory(**memory_data)
                    if stored_memory:
                        memories.append(stored_memory)
                        logger.debug(f"Stored memory: {item['content'][:50]}...")
                except Exception as e:
                    logger.error(f"Failed to store memory: {e}")
                    continue
            
            return memories
            
        except Exception as e:
            logger.error(f"Error extracting memories for bucket {bucket}: {e}")
            return []
    
    async def _llm_extract(
        self, 
        prompt: str, 
        conversation_text: str, 
        bucket: str
    ) -> List[Dict[str, Any]]:
        """
        Call LLM to extract memories (placeholder implementation)
        
        In production, this would call your actual LLM service
        """
        
        # TODO This is a placeholder - replace with actual LLM service call
        logger.info(f"LLM extraction for bucket {bucket} (placeholder)")
        
        # Simulate LLM extraction with example data for testing
        if bucket == "identity":
            return [
                {
                    "content": "User prefers to be called Prince", 
                    "importance": 0.9, 
                    "confidence": 0.95
                }
            ]
        elif bucket == "preferences":
            return [
                {
                    "content": "Prefers detailed technical explanations", 
                    "importance": 0.7, 
                    "confidence": 0.8
                }
            ]
        elif bucket == "goals":
            return [
                {
                    "content": "Building a ChatGPT clone with memory system", 
                    "importance": 0.9, 
                    "confidence": 0.9,
                    "status": "active"
                }
            ]
        
        # For now, return empty for other buckets
        return []
    
    def _format_conversation_for_extraction(
        self, 
        messages: List[Dict[str, str]]
    ) -> str:
        """Format conversation messages for LLM extraction"""
        
        formatted_parts = []
        
        for msg in messages[-20:]:  # Use last 20 messages to avoid token limits
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Clean and format
            if role.lower() in ["user", "assistant", "human", "ai"]:
                formatted_parts.append(f"{role.title()}: {content}")
        
        return "\n\n".join(formatted_parts)
    
    async def _get_user_active_buckets(
        self, 
        user_id: int, 
        requested_buckets: List[str]
    ) -> List[str]:
        """Get list of active memory buckets for a user"""
        
        # This would check user's MemoryPreferences
        # For MVP, return all requested buckets
        active_buckets = []
        
        for bucket in requested_buckets:
            if bucket in MEMORY_BUCKETS:
                # In production, check if user has this bucket enabled
                # For now, enable all buckets
                active_buckets.append(bucket)
        
        return active_buckets
    
    def extract_memory_triggers(self, message_content: str) -> List[str]:
        """
        Identify potential memory triggers in a message
        
        Returns list of bucket names that might be relevant
        """
        
        triggers = []
        content_lower = message_content.lower()
        
        # Identity triggers
        identity_keywords = ["my name is", "i am", "call me", "i live in", "i'm from"]
        if any(keyword in content_lower for keyword in identity_keywords):
            triggers.append("identity")
        
        # Preference triggers
        preference_keywords = ["i prefer", "i like", "i hate", "i always", "i usually"]
        if any(keyword in content_lower for keyword in preference_keywords):
            triggers.append("preferences")
        
        # Goal triggers
        goal_keywords = ["my goal", "i want to", "i'm working on", "i'm building", "i plan to"]
        if any(keyword in content_lower for keyword in goal_keywords):
            triggers.append("goals")
        
        # Workflow triggers
        workflow_keywords = ["i typically", "my process", "i usually do", "my workflow"]
        if any(keyword in content_lower for keyword in workflow_keywords):
            triggers.append("workflows")
        
        # Capability triggers
        capability_keywords = ["i can", "i know", "i'm good at", "i struggle with", "my budget"]
        if any(keyword in content_lower for keyword in capability_keywords):
            triggers.append("capabilities")
        
        # Social triggers
        social_keywords = ["my colleague", "my friend", "my team", "works with me"]
        if any(keyword in content_lower for keyword in social_keywords):
            triggers.append("social")
        
        return list(set(triggers))  # Remove duplicates
    
    async def extract_incremental_memories(
        self, 
        new_messages: List[Dict[str, str]], 
        user_id: int, 
        conversation_id: str
    ) -> Dict[str, List[UserMemory]]:
        """
        Extract memories from just the new messages in a conversation
        More efficient for ongoing conversations
        """
        
        if not new_messages:
            return {}
        
        # Detect which buckets might be relevant
        relevant_buckets = set()
        for message in new_messages:
            if message.get("role") == "user":
                triggers = self.extract_memory_triggers(message.get("content", ""))
                relevant_buckets.update(triggers)
        
        if not relevant_buckets:
            logger.info("No memory triggers detected in new messages")
            return {}
        
        # Extract memories only for relevant buckets
        return await self.extract_memories_from_conversation(
            new_messages, 
            user_id, 
            conversation_id, 
            list(relevant_buckets)
        )


# Utility functions for integration

async def extract_memories_from_conversation_messages(
    messages: List[Dict[str, str]], 
    user_id: int, 
    conversation_id: str,
    memory_service: MemoryService
) -> Dict[str, List[UserMemory]]:
    """
    Convenience function for extracting memories from conversation
    
    Args:
        messages: List of conversation messages
        user_id: User ID
        conversation_id: Conversation ID  
        memory_service: MemoryService instance
        
    Returns:
        Dictionary of extracted memories by bucket
    """
    
    extractor = MemoryExtractor(memory_service)
    return await extractor.extract_memories_from_conversation(
        messages, user_id, conversation_id
    )


async def trigger_memory_extraction_for_conversation(
    conversation_id: str,
    user_id: int,
    memory_service: MemoryService,
    db_session
) -> bool:
    """
    Trigger memory extraction for an entire conversation
    
    Args:
        conversation_id: ID of conversation to process
        user_id: User ID
        memory_service: MemoryService instance
        db_session: Database session
        
    Returns:
        True if extraction was successful
    """
    
    try:
        # Get conversation messages from database
        # This would use your existing conversation/message models
        # For now, return success
        
        logger.info(f"Memory extraction triggered for conversation {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger memory extraction: {e}")
        return False 