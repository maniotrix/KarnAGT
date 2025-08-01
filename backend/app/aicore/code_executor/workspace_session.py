#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Execution Session Manager

Provides unified workspace tracking and cleanup as a context manager.
Can be used directly or with agent tools for automatic resource management.

Features:
- Context manager for automatic workspace cleanup
- Direct service access (session.create_workspace(), session.execute_code(), etc.)  
- Agent tool integration via session-aware wrappers
- Provider-agnostic resource tracking
- Backward compatible with existing tools
"""

import uuid
import contextvars
from typing import Set, Optional, List, Dict, Any, Callable
from agents import function_tool

from app.logging.logger import get_logger
from app.aicore.code_executor.services import (
    WorkspaceService,
    FileService, 
    ExecutionService
)
from app.aicore.code_executor.models import (
    WorkspaceCreateResult,
    FileUploadResult,
    ExecutionOperationResult,
    FileInfo
)
from app.aicore.code_executor.prompts.tools_prompts import (
    CREATE_WORKSPACE_TOOL_DESCRIPTION,
    UPLOAD_FILE_TOOL_DESCRIPTION,
    EXECUTE_CODE_TOOL_DESCRIPTION
)

logger = get_logger(__name__)

# =============================================================================
# CONTEXT VARIABLE FOR SESSION MANAGEMENT
# =============================================================================

# PRIVATE: Context variable to store the current workspace session (internal use only)
_current_session: contextvars.ContextVar[Optional['WorkspaceExecutionSession']] = contextvars.ContextVar(
    'workspace_session_internal', 
    default=None
)

def _get_current_workspace_session() -> 'WorkspaceExecutionSession':
    """
    PRIVATE: Get the current workspace session from context variables.
    
    This is an internal function used by the workspace tools. External code
    should NOT call this directly. Instead, use the WorkspaceExecutionSession
    context manager and let the tools handle session access automatically.
    
    Returns:
        WorkspaceExecutionSession: The currently active session
        
    Raises:
        RuntimeError: If no workspace session is active in current context
    """
    try:
        session = _current_session.get()
    except LookupError:
        # This happens when context variable was never set
        raise RuntimeError(
            "No workspace session found in context. "
            "Make sure you're calling this within an 'async with WorkspaceExecutionSession()' block. "
            "Example usage:\n"
            "    async with WorkspaceExecutionSession() as session:\n"
            "        # Your tool calls here\n"
            "        result = await create_workspace()\n"
        )
    
    if session is None:
        # This happens when context variable was explicitly set to None
        raise RuntimeError(
            "Workspace session is None in current context. "
            "This might indicate a session cleanup issue or invalid context state. "
            "Make sure you're calling this within an active 'async with WorkspaceExecutionSession()' block."
        )
    
    return session


class WorkspaceExecutionSession:
    """
    Context manager for tracking and cleaning up workspace resources.
    
    Can be used in two ways:
    1. DIRECTLY - session.create_workspace(), session.execute_code(), etc.
    2. WITH AGENTS - via create_session_aware_code_tools()
    
    Example direct usage:
        async with WorkspaceExecutionSession() as session:
            workspace = await session.create_workspace()
            workspace_id = workspace.workspace_info.workspace_id
            
            await session.upload_file(workspace_id, "data.csv", csv_content)
            result = await session.execute_code(workspace_id, python_code)
            
            # More workspaces...
            ws2 = await session.create_workspace()
            
        # All workspaces automatically cleaned up here
        
    Example agent usage:
        async with WorkspaceExecutionSession() as session:
            agent = Agent(
                name="code_agent",
                tools=create_session_aware_code_tools(session),
                # ... other config
            )
            result = await Runner.run(agent, input="Create a plot")
            
        # All agent-created workspaces automatically cleaned up
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize workspace execution session.
        
        Args:
            session_id: Optional custom session ID. If None, generates UUID.
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.tracked_workspaces: Set[str] = set()
        
        # Initialize services
        self.workspace_service = WorkspaceService()
        self.file_service = FileService()
        self.execution_service = ExecutionService()
        
        # Cleanup state
        self._cleanup_completed = False
        self._cleanup_errors: List[str] = []
        
        logger.info(f"Initialized workspace session {self.session_id}")
    
    async def __aenter__(self) -> 'WorkspaceExecutionSession':
        """Enter context manager and set session in context"""
        logger.info(f"Starting workspace session {self.session_id}")
        
        # Set this session as the current session in context variables
        self._context_token = _current_session.set(self)
        logger.debug(f"Session {self.session_id}: Set as current session in context")
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager with automatic cleanup and context reset"""
        try:
            await self.cleanup_all_workspaces()
        finally:
            # Always reset the context variable, even if cleanup fails
            if hasattr(self, '_context_token'):
                _current_session.reset(self._context_token)
                logger.debug(f"Session {self.session_id}: Cleared from context")
        
        # Log session summary
        if exc_type:
            logger.info(f"Session {self.session_id} ended with exception: {exc_type.__name__}")
        else:
            logger.info(f"Session {self.session_id} completed successfully")
    
    # =============================================================================
    # DIRECT SERVICE METHODS - Use session directly without agents
    # =============================================================================
    
    async def create_workspace(self, ttl_hours: int = 2) -> WorkspaceCreateResult:
        """
        Create workspace and automatically track it for cleanup.
        
        Args:
            ttl_hours: Workspace lifetime in hours (default: 2, max: 24)
            
        Returns:
            WorkspaceCreateResult with workspace info
        """
        logger.info(f"Session {self.session_id}: Creating workspace with TTL {ttl_hours}h")
        
        result = await self.workspace_service.create_workspace(ttl_hours)
        
        if result.success and result.workspace_info:
            workspace_id = result.workspace_info.workspace_id
            self.tracked_workspaces.add(workspace_id)
            logger.info(f"Session {self.session_id}: Now tracking workspace {workspace_id} ({len(self.tracked_workspaces)} total)")
        else:
            logger.warning(f"Session {self.session_id}: Failed to create workspace: {result.error}")
            
        return result
    
    async def execute_code(self, workspace_id: str, code: str) -> ExecutionOperationResult:
        """
        Execute code in a workspace (workspace should be session-tracked).
        
        Args:
            workspace_id: Target workspace identifier
            code: Python code to execute
            
        Returns:
            ExecutionOperationResult with execution details
        """
        if workspace_id not in self.tracked_workspaces:
            logger.warning(f"Session {self.session_id}: Executing code in untracked workspace {workspace_id}")
        
        logger.info(f"Session {self.session_id}: Executing code in workspace {workspace_id}")
        result: ExecutionOperationResult = await self.execution_service.execute_code(workspace_id, code)
        
        # If code execution succeeded and generated files, persist them to permanent storage
        if result.success and result.execution_result and result.execution_result.generated_files:
            logger.info(f"Session {self.session_id}: Code execution generated {len(result.execution_result.generated_files)} files - starting persistence")
            await self._persist_generated_files_to_storage(workspace_id, result.execution_result.generated_files)
        
        return result
    
    async def upload_file(self, workspace_id: str, filename: str, content: str | bytes) -> FileUploadResult:
        """
        Upload file to a workspace (workspace should be session-tracked).
        
        Args:
            workspace_id: Target workspace identifier
            filename: Name of the file (can include subdirectory)
            content: File content as string or bytes
            
        Returns:
            FileUploadResult with upload status and file info
        """
        if workspace_id not in self.tracked_workspaces:
            logger.warning(f"Session {self.session_id}: Uploading to untracked workspace {workspace_id}")
            
        logger.info(f"Session {self.session_id}: Uploading {filename} to workspace {workspace_id}")
        return await self.file_service.upload_file(workspace_id, filename, content)
    
    async def download_and_upload_file(
        self, 
        workspace_id: str, 
        source_url: str, 
        file_name: str
    ) -> FileUploadResult:
        """
        Download file from URL and upload to workspace.
        
        Args:
            workspace_id: Target workspace identifier
            source_url: HTTP URL to download from
            file_name: Name for the file in workspace
            
        Returns:
            FileUploadResult with upload status and file info
        """
        if workspace_id not in self.tracked_workspaces:
            logger.warning(f"Session {self.session_id}: Uploading to untracked workspace {workspace_id}")
            
        logger.info(f"Session {self.session_id}: Downloading {source_url} as {file_name} to workspace {workspace_id}")
        return await self.file_service.download_and_upload_file_to_workspace(
            workspace_id, source_url, file_name
        )
    
    # =============================================================================
    # SESSION MANAGEMENT METHODS
    # =============================================================================
    
    def track_workspace(self, workspace_id: str) -> None:
        """
        Manually track a workspace for cleanup.
        
        This is useful if you have workspace IDs from other sources that
        should be cleaned up with this session.
        
        Args:
            workspace_id: Workspace ID to track
        """
        self.tracked_workspaces.add(workspace_id)
        logger.info(f"Session {self.session_id}: Manually tracking workspace {workspace_id} ({len(self.tracked_workspaces)} total)")
    
    def untrack_workspace(self, workspace_id: str) -> bool:
        """
        Stop tracking a workspace (won't be cleaned up).
        
        Args:
            workspace_id: Workspace ID to stop tracking
            
        Returns:
            True if workspace was being tracked, False otherwise
        """
        if workspace_id in self.tracked_workspaces:
            self.tracked_workspaces.remove(workspace_id)
            logger.info(f"Session {self.session_id}: Stopped tracking workspace {workspace_id} ({len(self.tracked_workspaces)} remaining)")
            return True
        return False
    
    def get_tracked_workspaces(self) -> Set[str]:
        """Get set of all tracked workspace IDs"""
        return self.tracked_workspaces.copy()
    
    def get_workspace_count(self) -> int:
        """Get number of tracked workspaces"""
        return len(self.tracked_workspaces)
    
    async def cleanup_all_workspaces(self) -> Dict[str, Any]:
        """
        Clean up all tracked workspaces.
        
        Returns:
            Dict with cleanup statistics and any errors
        """
        if self._cleanup_completed:
            logger.info(f"Session {self.session_id}: Cleanup already completed")
            return {
                "session_id": self.session_id,
                "workspaces_cleaned": 0,
                "already_completed": True,
                "errors": []
            }
        
        workspace_count = len(self.tracked_workspaces)
        if workspace_count == 0:
            logger.info(f"Session {self.session_id}: No workspaces to clean up")
            self._cleanup_completed = True
            return {
                "session_id": self.session_id,
                "workspaces_cleaned": 0,
                "errors": []
            }
        
        logger.info(f"Session {self.session_id}: Cleaning up {workspace_count} workspaces...")
        
        cleaned_count = 0
        cleanup_errors = []
        
        # Create a copy to iterate over since cleanup_workspace modifies the original set
        workspaces_to_cleanup = self.tracked_workspaces.copy()
        
        # Use the existing cleanup_workspace function for each workspace
        for workspace_id in workspaces_to_cleanup:
            try:
                success = await self.cleanup_workspace(workspace_id)
                if success:
                    cleaned_count += 1
                else:
                    error_msg = f"Failed to cleanup workspace {workspace_id}"
                    cleanup_errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"Exception cleaning up workspace {workspace_id}: {e}"
                cleanup_errors.append(error_msg)
                logger.error(f"Session {self.session_id}: {error_msg}")
        
        self._cleanup_completed = True
        self._cleanup_errors = cleanup_errors
        
        # Final summary
        remaining_count = len(self.tracked_workspaces)
        if remaining_count > 0:
            logger.warning(f"Session {self.session_id}: {remaining_count} workspaces could not be cleaned up")
        
        logger.info(f"Session {self.session_id}: Cleanup completed - {cleaned_count}/{workspace_count} workspaces cleaned")
        
        return {
            "session_id": self.session_id,
            "workspaces_cleaned": cleaned_count,
            "workspaces_failed": len(cleanup_errors),
            "workspaces_remaining": remaining_count,
            "errors": cleanup_errors
        }
    
    async def cleanup_workspace(self, workspace_id: str) -> bool:
        """
        Clean up a specific workspace immediately.
        
        Args:
            workspace_id: Workspace to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        if workspace_id not in self.tracked_workspaces:
            logger.warning(f"Session {self.session_id}: Attempted to cleanup untracked workspace {workspace_id}")
            return False
        
        try:
            logger.info(f"Session {self.session_id}: Cleaning up specific workspace {workspace_id}")
            result = await self.workspace_service.delete_workspace(workspace_id)
            
            if result.success:
                self.tracked_workspaces.discard(workspace_id)
                logger.info(f"Session {self.session_id}: Successfully cleaned up workspace {workspace_id}")
                return True
            else:
                logger.warning(f"Session {self.session_id}: Failed to cleanup workspace {workspace_id}: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Session {self.session_id}: Exception cleaning up workspace {workspace_id}: {e}")
            return False
    
    async def _persist_generated_files_to_storage(self, workspace_id: str, generated_files: List[FileInfo]) -> None:
        """
        Persist generated files from sandbox workspace to permanent S3/MinIO storage.
        
        This method downloads files from the ephemeral sandbox and uploads them to
        permanent storage, replacing sandbox URLs with permanent storage URLs.
        
        Args:
            workspace_id: Sandbox workspace containing the files
            generated_files: List of FileInfo objects with generated files
        """
        # Import here to avoid circular imports
        from app.services.storage.storage import S3StorageBackend
        
        persist_count = 0
        total_files = len(generated_files)
        
        logger.info(
            f"Session {self.session_id}: Starting persistence of {total_files} generated files "
            f"from workspace {workspace_id} to permanent storage"
        )
        
        # Initialize S3 storage backend directly
        storage_backend = S3StorageBackend()
        
        for i, file_info in enumerate(generated_files, 1):
            try:
                logger.debug(
                    f"Session {self.session_id}: Persisting file {i}/{total_files}: "
                    f"{file_info.filename} ({file_info.size} bytes)"
                )
                
                # Download file content from sandbox
                download_result = await self.file_service.download_file(workspace_id, file_info.relative_path)
                
                if not download_result.success or download_result.content is None:
                    logger.error(
                        f"Session {self.session_id}: Failed to download {file_info.filename} "
                        f"from workspace {workspace_id}: {download_result.error or 'No content returned'}"
                    )
                    continue
                
                # Generate storage key for permanent storage
                # Use pattern: generated/{session_id}/{workspace_id}/{filename}
                storage_key = f"generated/{self.session_id}/{workspace_id}/{file_info.filename}"
                
                # Upload to permanent storage using the standard S3 storage backend
                uploaded_key = await storage_backend.upload_file(
                    file_data=download_result.content,
                    key=storage_key,
                    content_type=file_info.mime_type or "application/octet-stream"
                )
                
                # Generate presigned URL for user access (7 days expiration)
                permanent_url = await storage_backend.generate_presigned_url(
                    key=uploaded_key,
                    expire_seconds=7 * 24 * 3600  # 7 days
                )
                
                # Replace sandbox URL with permanent storage URL
                original_url = file_info.download_url
                file_info.download_url = permanent_url
                
                persist_count += 1
                
                logger.info(
                    f"Session {self.session_id}: Successfully persisted {file_info.filename} "
                    f"({file_info.size} bytes) to permanent storage. "
                    f"URL updated: {original_url} -> {permanent_url[:100]}..."
                )
                
            except Exception as e:
                # Log error but continue with other files - don't fail entire execution
                logger.error(
                    f"Session {self.session_id}: Failed to persist {file_info.filename} "
                    f"from workspace {workspace_id}: {type(e).__name__}: {e}",
                    exc_info=True
                )
        
        if persist_count > 0:
            logger.info(
                f"Session {self.session_id}: File persistence completed - "
                f"{persist_count}/{total_files} files successfully persisted to permanent storage"
            )
        else:
            logger.warning(
                f"Session {self.session_id}: File persistence failed - "
                f"0/{total_files} files were persisted. Generated files may become unavailable after workspace cleanup."
            )
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        return {
            "session_id": self.session_id,
            "tracked_workspaces": len(self.tracked_workspaces),
            "workspace_ids": list(self.tracked_workspaces),
            "cleanup_completed": self._cleanup_completed,
            "cleanup_errors": len(self._cleanup_errors)
        }


# =============================================================================
# AGENT TOOL INTEGRATION FUNCTIONS
# =============================================================================


class WorkspaceFunctionTool:
    """
    Wrapper for workspace functions that can be used as either:
    1. Raw callable functions (agent.get_callable())
    2. Decorated function tools (agent.as_function_tool())
    """
    
    def __init__(
        self, 
        name_override: str, 
        description_override: str, 
        strict_mode: bool, 
        func: Callable[..., Any]
    ):
        self.name_override = name_override
        self.description_override = description_override
        self.strict_mode = strict_mode
        self.func = func
        
    def get_callable(self) -> Callable[..., Any]:
        """Return the raw callable function without @function_tool decorator"""
        return self.func
        
    def as_function_tool(self):
        """Return the function wrapped with @function_tool decorator"""
        return function_tool(
            name_override=self.name_override,
            description_override=self.description_override,
            strict_mode=self.strict_mode
        )(self.func)
        
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Allow direct calling of the underlying function"""
        return self.func(*args, **kwargs)
    
    def __str__(self) -> str:
        return f"WorkspaceFunctionTool(name={self.name_override}, strict_mode={self.strict_mode})"
    
async def create_workspace_func(ttl_hours: int = 2) -> WorkspaceCreateResult:
    """Create workspace using current session from context (automatically tracked)"""
    try:
        session = _get_current_workspace_session()
        return await session.create_workspace(ttl_hours)
    except RuntimeError as e:
        # Handle context variable issues
        error_msg = (
            "Cannot create workspace: No active workspace session found. "
            "Make sure you're calling this tool within an 'async with WorkspaceExecutionSession()' context. "
            f"Original error: {str(e)}"
        )
        logger.error(f"create_workspace tool error: {error_msg}")
        
        # Return a failed result instead of raising
        return WorkspaceCreateResult.error_result(error_msg)
    except Exception as e:
        # Handle any other unexpected errors
        error_msg = (
            f"Unexpected error during workspace creation: {str(e)}. "
            "This might be a service issue or configuration problem."
        )
        logger.error(f"create_workspace tool unexpected error: {error_msg}", exc_info=True)
        return WorkspaceCreateResult.error_result(error_msg)
    
async def upload_file_func(workspace_id: str, file_url: str, file_name: str) -> FileUploadResult:
    """Upload file using current session from context"""
    try:
        session = _get_current_workspace_session()
        return await session.download_and_upload_file(workspace_id, file_url, file_name)
    except RuntimeError as e:
        # Handle context variable issues
        error_msg = (
            f"Cannot upload file '{file_name}': No active workspace session found. "
            "Make sure you're calling this tool within an 'async with WorkspaceExecutionSession()' context. "
            f"Original error: {str(e)}"
        )
        logger.error(f"upload_file tool error: {error_msg}")
        
        # Return a failed result instead of raising
        return FileUploadResult.error_result(error_msg)
    except Exception as e:
        # Handle any other unexpected errors (network issues, validation errors, etc.)
        error_msg = (
            f"Unexpected error during file upload '{file_name}' to workspace '{workspace_id}': {str(e)}. "
            "This might be a network issue, invalid URL, or service problem."
        )
        logger.error(f"upload_file tool unexpected error: {error_msg}", exc_info=True)
        
        return FileUploadResult.error_result(error_msg)
    
async def execute_code_func(workspace_id: str, code: str) -> ExecutionOperationResult:
    """Execute code using current session from context"""
    try:
        session = _get_current_workspace_session()
        return await session.execute_code(workspace_id, code)
    except RuntimeError as e:
        # Create a more specific error message for this tool
        error_msg = (
            f"Cannot execute code in workspace '{workspace_id}': No active workspace session found. "
            "Make sure you're calling this tool within an 'async with WorkspaceExecutionSession()' context. "
            f"Original error: {str(e)}"
        )
        logger.error(f"execute_code tool error: {error_msg}")
        
        # Return a failed result instead of raising
        return ExecutionOperationResult.error_result(error_msg)
    except Exception as e:
        # Handle any other unexpected errors
        error_msg = (
            f"Unexpected error during code execution: {str(e)}. "
            "This might be a service issue or configuration problem."
        )
        logger.error(f"execute_code tool unexpected error: {error_msg}", exc_info=True)
        
        return ExecutionOperationResult.error_result(error_msg)
    

# =============================================================================
# WORKSPACE FUNCTION TOOL REGISTRY
# =============================================================================

# Define all workspace function tools with their parameters in one place
WORKSPACE_FUNCTION_TOOLS = {
    'create_workspace': WorkspaceFunctionTool(
        name_override="create_workspace",
        description_override=CREATE_WORKSPACE_TOOL_DESCRIPTION,
        strict_mode=True,
        func=create_workspace_func
    ),
    
    'upload_file': WorkspaceFunctionTool(
        name_override="upload_file",
        description_override=UPLOAD_FILE_TOOL_DESCRIPTION,
        strict_mode=True,
        func=upload_file_func
    ),
    
    'execute_code': WorkspaceFunctionTool(
        name_override="execute_code",
        description_override=EXECUTE_CODE_TOOL_DESCRIPTION,
        strict_mode=True,
        func=execute_code_func
    )
}


def get_workspace_function_tools() -> Dict[str, WorkspaceFunctionTool]:
    """
    Get all workspace function tools as WorkspaceFunctionTool objects.
    
    Returns:
        Dict mapping tool names to WorkspaceFunctionTool objects
        Each tool can be used as:
        - Raw callable: tool.get_callable()
        - Function tool: tool.as_function_tool()
    """
    return WORKSPACE_FUNCTION_TOOLS.copy()


def get_workspace_callables() -> Dict[str, Callable[..., Any]]:
    """
    Get the raw callable functions for all workspace tools.
    
    Returns:
        Dict mapping tool names to their underlying callable functions
    """
    return {
        name: tool.get_callable() 
        for name, tool in WORKSPACE_FUNCTION_TOOLS.items()
    }
    
def create_session_aware_code_tools() -> List:
    """
    Create agent tools that automatically use the current session from context.
    
    These tools will automatically access the active WorkspaceExecutionSession
    from context variables, eliminating the need to pass session parameters.
    
    The tools can only be used within an 'async with WorkspaceExecutionSession()' block.
    
    Returns:
        List of function tools ready for agent use
        
    Raises:
        RuntimeError: If tools are called outside of an active session context
    """
    # Use the centralized tool registry to get decorated function tools
    workspace_tools = get_workspace_function_tools()
    
    return [
        workspace_tools['create_workspace'].as_function_tool(),
        workspace_tools['upload_file'].as_function_tool(),
        workspace_tools['execute_code'].as_function_tool()
    ]


# =============================================================================
# WHAT GETS IMPORTED WHEN USING `from workspace_session import *`
# =============================================================================

__all__ = [
    "WorkspaceExecutionSession",
    "create_session_aware_code_tools",
    "WorkspaceFunctionTool",
    "get_workspace_function_tools",
    "get_workspace_callables",
    # Note: _get_current_workspace_session is private and not exported
]