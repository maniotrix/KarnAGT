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
import asyncio
import contextvars
from typing import Set, Optional, List, Dict, Any
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
    ExecutionOperationResult
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
        return await self.execution_service.execute_code(workspace_id, code)
    
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
    
    @function_tool(
        name_override="create_workspace",
        description_override="""
        Create a new isolated workspace for Python code execution.
        
        This workspace will be automatically tracked and cleaned up when the session ends.
        
        HOW IT WORKS:
        - Creates a fresh Python environment with Jupyter kernel
        - Workspace automatically expires after specified hours
        - Variables and imports persist across multiple code executions
        - Automatically tracked for cleanup by session manager
        
        WHEN TO USE:
        - At the start of any coding task or data analysis
        - When you need a clean environment for Python execution
        - Before uploading files or running any code
        
        WHAT YOU GET BACK:
        - workspace_id: Use this for all subsequent upload_file and execute_code calls
        - status: "ready" when workspace is available for use
        - expires_at: When the workspace will be automatically cleaned up
        """,
        strict_mode=True,
    )
    async def create_workspace(ttl_hours: int = 2) -> WorkspaceCreateResult:
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
    
    @function_tool(
        name_override="upload_file", 
        description_override="""
        Upload a file to a workspace so it can be accessed by Python code.
        
        ## CRITICAL FILE UPLOAD INSTRUCTIONS:
        File URL must be a valid Full HTTP URL and the maximum file size allowed is 20MB.
        You must provide a file_name to be used for the file in the workspace.
        
        ## REQUIRED PARAMETERS:
        - workspace_id: Valid workspace ID from create_workspace()
        - file_url: Valid Full HTTP URL
        - file_name: Name of the file
        
        ## RETURN VALUE STRUCTURE:
        The tool returns a FileUploadResult containing:
        - **success**: boolean indicating if upload completed successfully
        - **file_info**: FileInfo object with details about the uploaded file
        - **error**: Optional error message if upload failed
        
        HOW IT WORKS:
        - Downloads file from URL and uploads to workspace's root directory
        - Files become immediately available for code execution
        
        WHEN TO USE:
        - Upload datasets, images, or any input files needed for analysis
        - Provide configuration files, scripts, or resources
        - Before running code that needs to read specific files
        
        WHAT YOU GET BACK:
        - Confirmation of successful upload or specific error message
        - File size and location information along with a download URL
        - Ready for use in execute_code calls with the workspace_id
        """,
        strict_mode=True,
    )
    async def upload_file(
        workspace_id: str,
        file_url: str, 
        file_name: str
    ) -> FileUploadResult:
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
    
    @function_tool(
        name_override="execute_code",
        description_override="""
        Execute Python code in a isolated workspace with persistent state and file generation capabilities.
        
        ## REQUIRED PARAMETERS:
        - workspace_id: Valid workspace ID from create_workspace()
        - code: Python code string

        ## RETURN VALUE STRUCTURE:
        The tool returns an ExecutionOperationResult containing:
        - **success**: boolean indicating if execution completed successfully
        - **standard output**: text that was printed during execution  
        - **error messages**: any error messages that occurred
        - **generated files**: list of files created during execution with full HTTP download URLs
        - **result data**: the final computed result (if any)
        
        ## CRITICAL REQUIREMENT FOR CODE EXECUTION: 
        - You MUST have a valid workspace_id before calling this function
        - If you don't have one, call create_workspace() FIRST to get a workspace_id
        - NEVER use arbitrary workspace IDs like "1", "test", etc.
        - ALWAYS use the exact workspace_id returned by create_workspace()
        - If a piece of code times-out, do not run **the same code** again.
        - DO NOT make up or estimate results for failed or timed out code executions
        - ALWAYS check if the execution succeeded before using any outputs
        
        ## CODE EXECUTION ENVIRONMENT:
        - Jupyter kernel with persistent variables/imports across calls
        - Working directory: workspace root (contains uploaded files)
        - Full Python standard library + common packages (numpy, pandas, matplotlib, etc.)
        - Output capture: stdout, stderr, and execution results
        - Your code will be executed with a timeout of 30 seconds.
        
        ## FILE OPERATIONS:
        - **Read files**: open('filename.txt', 'r') - access uploaded files directly
        - **Create files**: open('output.csv', 'w') - any file you create gets tracked
        - **Generate plots**: plt.savefig('chart.png') - saved plots are automatically detected

        ## EXAMPLES:
        ```python
        # Data analysis with CSV output
        df.to_csv('analysis_results.csv', index=False)
        
        # Visualization with plot file
        plt.figure(figsize=(10,6))
        plt.plot(data)
        plt.savefig('visualization.png', dpi=300, bbox_inches='tight')
        
        # Generate reports or documents  
        with open('report.txt', 'w') as f:
            f.write(f"Analysis completed: {results}")
        ```

        ## BEST PRACTICES and DATA VISUALIZATION INSTRUCTIONS:
        - DO NOT use plt.show() as it will cause errors in the execution environment.
        - Always close plt figures: plt.close() after plt.savefig()
        - Use descriptive filenames with extensions
        - Save files you want users to access (they get full HTTP download URLs automatically)
        - Use result = your_final_value to return computed results
        """,
        strict_mode=True,
    )
    async def execute_code(workspace_id: str, code: str) -> ExecutionOperationResult:
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
    
    return [create_workspace, upload_file, execute_code]


# =============================================================================
# WHAT GETS IMPORTED WHEN USING `from workspace_session import *`
# =============================================================================

__all__ = [
    "WorkspaceExecutionSession",
    "create_session_aware_code_tools",
    # Note: _get_current_workspace_session is private and not exported
]