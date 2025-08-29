#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM Knowledge Tools - Functions for AI agents to search uploaded files and documents
"""

from typing import Dict, List, Optional, Any
from agents import function_tool
from app.services.knowledge.knowledge_service import KnowledgeService
from app.logging.logger import get_logger

logger = get_logger(__name__)

# ANSI color codes for knowledge tool logs
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'
    
class KnowledgeToolNames:
    # Public-facing name shown to the LLM – keep neutral to avoid stealing generic "search" cues
    KNOWLEDGE_SEARCH = "user_uploaded_documents_query"
    KNOWLEDGE_DISCOVERY = "list_user_uploaded_documents"
    
class KnowledgeToolsInfo():
    """
    Information about the knowledge tools configuration
    """
    TOOL_TYPE: str = "knowledge_tools"
    TOOL_NAMES: List[str] = [KnowledgeToolNames.KNOWLEDGE_SEARCH, KnowledgeToolNames.KNOWLEDGE_DISCOVERY]

def knowledge_log(level, message, tool_name=None):
    """Helper to log knowledge tool messages with color coding"""
    tool_prefix = f"[{tool_name}]" if tool_name else ""
    colored_prefix = f"{Colors.BLUE}[KNOWLEDGE-TOOLS]{tool_prefix}{Colors.END}"
    if level == "info":
        logger.info(f"{colored_prefix} {message}")
    elif level == "error":
        logger.error(f"{colored_prefix} {Colors.RED}{message}{Colors.END}")
    elif level == "success":
        logger.info(f"{colored_prefix} {Colors.GREEN}{message}{Colors.END}")


def create_knowledge_search_tool(
    knowledge_service: KnowledgeService,
    user_id: str,
    conversation_id: str
):
    """
    Create a configured knowledge search tool for a specific user and conversation.
    
    Args:
        knowledge_service: KnowledgeService instance
        user_id: User ID for file access validation
        conversation_id: Conversation ID for context scoping
        
    Returns:
        Configured function tool ready for agent use
    """
    
    @function_tool(
        name_override=KnowledgeToolNames.KNOWLEDGE_SEARCH,
        description_override="""
        This tool is used to query user uploaded files and documents to answer questions about their content.
        
        **CRITICAL: PREFER TO CHECK UPLOADED DOCUMENTS WHEN RELEVANT AS PER USER INTENT**
        - Do not use it when the user explicitly requests a web or internet search.
        
        Before providing any answer, check if the user has uploaded files that might contain the answer.
        Users expect answers from their uploaded documents, not generic knowledge.
    
        **User Uploaded Documents Query Tool Instructions:**
        1. **Prefer to query uploaded documents first** before giving generic answers
        2. Use user_uploaded_documents_query with search_all_files=true for most queries
        3. Only use specific file IDs if you have them from message attachments
        4. If no relevant information found in documents, then proceed with other tools
        5. Examples of when to query documents:
            - "What is [company/person/topic]?" → Query documents first
            - "What are the key points?" → Query documents first
            - "Compare/analyze/summarize" → Query documents first
        
        TWO QUERY MODES:
        1. SPECIFIC FILES: Query only specific uploaded files by their IDs
        2. ALL FILES: Query all files uploaded in this conversation
        
        WHEN TO USE SPECIFIC FILES MODE:
        - User asks about specific files: "What does document X say about Y?"
        - You have knowledge_file_ids from message attachments
        - You want to focus query on particular documents
        - User uploaded files in current message and asks about them
        
        WHEN TO USE ALL FILES MODE in USER UPLOADED DOCUMENTS QUERY TOOL (DEFAULT - USE THIS MOST OF THE TIME):
        - User asks ANY question that could be answered by uploaded files
        - User asks "What is X?" where X might be mentioned in documents
        - User asks for analysis, comparison, or summary of any kind
        - When unsure and have no knowledge_file_ids, use this mode to query all files first
        - Better to query and find nothing than miss important information
        - In short, use this mode when you have no context regarding a query or has very vague context
        
        PARAMETERS:
        - query: Your question about the files
        - knowledge_file_ids: List of specific file IDs to query (optional)
        - search_all_files: Set to true to query all files (optional, default: false)
        
        EXAMPLES:
        user_uploaded_documents_query(
            query="What are the main conclusions?",
            knowledge_file_ids=["kf_abc123", "kf_def456"]
        )
        
        user_uploaded_documents_query(
            query="What are the key points across all documents?",
            search_all_files=true
        )
        """,
        strict_mode=True
    )
    async def knowledge_search_tool(
        query: str,
        knowledge_file_ids: Optional[List[str]] = None,
        search_all_files: bool = False
    ) -> str:
        """
        Search knowledge files and return answers.
        
        Args:
            query: Question about the files
            knowledge_file_ids: List of specific file IDs to search
            search_all_files: Whether to search all files in conversation
            
        Returns:
            Formatted answer with sources and metadata
        """
        try:
            knowledge_log("info", f"Knowledge search query: '{query}'", "SEARCH")
            
            # Handle empty query by providing discovery query
            if not query or not query.strip():
                knowledge_log("info", "Empty query detected, using discovery mode", "DISCOVERY")
                query = """
                Provide a comprehensive summary of the uploaded files and suggest 5 specific, actionable questions that would help explore these documents further.
                
                Format your response as:
                SUMMARY: [detailed summary of main topics and insights]
                
                SUGGESTED QUESTIONS:
                1. [specific question about key topic]
                2. [specific question about methodology/approach]
                3. [specific question about findings/conclusions]
                4. [specific question about implications]
                5. [specific question about details/specifics]
                """
            
            # Validate search mode parameters
            if knowledge_file_ids and search_all_files:
                return "**Error:** Cannot use both knowledge_file_ids and search_all_files=true. Choose one search mode."
            
            if not knowledge_file_ids and not search_all_files:
                # Default to searching all files with helpful message
                knowledge_log("info", "No specific mode selected, defaulting to search all files", "SEARCH")
                search_all_files = True
            
            # MODE 1: Search specific knowledge files
            if knowledge_file_ids:
                result = await knowledge_service.search_specific_files(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=query,
                    knowledge_file_ids=knowledge_file_ids
                )
                
                if not result:
                    return f"**No Results:** No accessible files found for the provided IDs: {knowledge_file_ids}. The files may not exist, may not be processed yet, or you may not have access to them."
                
                # Format response for specific files
                sources_info = f"{len(result.sources)} source chunks" if result.sources else "No sources"
                
                response = f"""**Query:** {query}

**Files Searched:** {len(knowledge_file_ids)} specific files

**Answer:** {result.response}

**Sources:** {sources_info} found in {result.query_time:.3f}s"""
                
                # Add source details if available
                if result.sources:
                    response += "\n\n**Source Details:**"
                    for i, source in enumerate(result.sources[:5], 1):  # Limit to top 5 sources
                        response += f"\n{i}. {source['file_name']} (Score: {source['score']:.3f})"
                        if source.get('page_label'):
                            response += f" - Page {source['page_label']}"
                
                knowledge_log("success", f"Specific file search completed: {len(result.sources)} sources found", "SPECIFIC")
                return response
            
            # MODE 2: Search all files in conversation
            elif search_all_files:
                result = await knowledge_service.search_conversation_files(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=query
                )
                
                if not result:
                    return f"**No Results:** No files found in this conversation or no results for query: '{query}'. Make sure files have been uploaded and processed."
                
                # Get file count for context
                available_docs = await knowledge_service.list_available_files(
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                
                sources_info = f"{len(result.sources)} source chunks" if result.sources else "No sources"
                
                response = f"""**Query:** {query}

**Files Searched:** All files in conversation ({len(available_docs)} files available)

**Answer:** {result.response}

**Sources:** {sources_info} found in {result.query_time:.3f}s"""
                
                # Add source details if available
                if result.sources:
                    response += "\n\n**Source Details:**"
                    for i, source in enumerate(result.sources[:5], 1):  # Limit to top 5 sources
                        response += f"\n{i}. {source['file_name']} (Score: {source['score']:.3f})"
                        if source.get('page_label'):
                            response += f" - Page {source['page_label']}"
                
                knowledge_log("success", f"All files search completed: {len(result.sources)} sources found", "ALL")
                return response
            
            else:
                return "**Error:** Please specify either knowledge_file_ids or set search_all_files=true."
            
        except Exception as e:
            knowledge_log("error", f"Error in knowledge search: {e}", "SEARCH")
            return f"**Error:** Failed to search knowledge files: {str(e)}"
    
    return knowledge_search_tool


def create_knowledge_discovery_tool(
    knowledge_service: KnowledgeService,
    user_id: str,
    conversation_id: str
):
    """
    Create a tool for discovering available knowledge files in the conversation.
    
    Args:
        knowledge_service: KnowledgeService instance
        user_id: User ID for file access validation
        conversation_id: Conversation ID for context scoping
        
    Returns:
        Configured function tool ready for agent use
    """
    
    @function_tool(
        name_override=KnowledgeToolNames.KNOWLEDGE_DISCOVERY,
        description_override="""
        List all available user uploaded files in this conversation.
        
        Use this tool to:
        - See what files are available for searching
        - Get knowledge_file_ids for specific file searches
        - Check file processing status
        - Understand what content is available
        
        This is helpful when you need to know what files you can search
        or when the user asks "what files do I have uploaded?"
        """,
        strict_mode=True
    )
    async def knowledge_discovery_tool() -> str:
        """
        List available knowledge files in the conversation.
        
        Returns:
            Formatted list of available files with metadata
        """
        try:
            knowledge_log("info", f"Listing knowledge files in conversation {conversation_id}", "DISCOVERY")
            
            # Get available documents using the knowledge service
            available_docs = await knowledge_service.list_available_files(
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            if not available_docs:
                return "**No Files Found:** No knowledge files found in this conversation. Upload some files to get started with document search."
            
            # Format response
            response = f"**Available Knowledge Files ({len(available_docs)} files):**\n\n"
            
            for i, doc in enumerate(available_docs, 1):
                response += f"{i}. **{doc['file_name']}**\n"
                response += f"   - Knowledge File ID: `{doc['knowledge_file_id']}`\n"
                response += f"   - Documents: {doc['document_count']}\n"
                response += f"   - Chunks: {doc['node_count']}\n"
                response += f"   - Size: {doc['file_size']} bytes\n"
                response += f"   - Type: {doc['content_type']}\n"
                if doc.get('processed_at'):
                    response += f"   - Processed: {doc['processed_at']}\n"
                response += "\n"
            
            response += f"\n**Usage:** Use `search_knowledge_files()` with specific `knowledge_file_ids` to search individual files, or set `search_all_files=true` to search all files."
            
            knowledge_log("success", f"Listed {len(available_docs)} knowledge files", "DISCOVERY")
            return response
            
        except Exception as e:
            knowledge_log("error", f"Error listing knowledge files: {e}", "DISCOVERY")
            return f"**Error:** Failed to list knowledge files: {str(e)}"
    
    return knowledge_discovery_tool


# =============================================================================
# UTILITY FUNCTIONS FOR CREATING KNOWLEDGE SERVICE
# =============================================================================

def create_knowledge_service_from_config(
    db_session,
    rag_config_type: str = "chat_application"
) -> KnowledgeService:
    """
    Create a KnowledgeService instance with the specified configuration.
    
    Args:
        db_session: Database session
        rag_config_type: Type of RAG configuration to use
        
    Returns:
        KnowledgeService instance
    """
    from app.services.knowledge.config import RAGConfig
    
    # Map configuration types to factory methods
    config_methods = {
        "chat_application": RAGConfig.for_chat_application,
        "robust_retrieval": RAGConfig.for_robust_retrieval,
        "precise_retrieval": RAGConfig.for_precise_retrieval,
        "fast_processing": RAGConfig.for_fast_processing,
        "cost_optimized": RAGConfig.for_cost_optimized,
        "gpt4": RAGConfig.for_gpt4,
        "gpt4o_mini": RAGConfig.for_gpt4o_mini,
        "gpt35_turbo": RAGConfig.for_gpt35_turbo,
        "claude": RAGConfig.for_claude,
    }
    
    config_method = config_methods.get(rag_config_type, RAGConfig.for_chat_application)
    rag_config = config_method()
    
    logger.info(f"Creating KnowledgeService with {rag_config_type} configuration")
    return KnowledgeService(db_session, rag_config)


def get_knowledge_service_info(knowledge_service: KnowledgeService) -> Dict[str, Any]:
    """
    Get information about a knowledge service instance.
    
    Args:
        knowledge_service: KnowledgeService instance
        
    Returns:
        Dictionary with service information
    """
    return knowledge_service.get_service_info() 