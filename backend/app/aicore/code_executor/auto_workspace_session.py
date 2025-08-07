#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Auto-Workspace Session Manager

A clean, simplified workspace session that automatically manages a default workspace
for seamless code execution without requiring explicit workspace creation by LLMs.

Key Features:
- Automatic default workspace creation on first use
- Context manager for guaranteed cleanup
- Simplified tool interface (no workspace_id required)
- Auto-recovery from workspace failures
- Session-aware tools via context variables
"""

import uuid
import contextvars
from datetime import datetime
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
from app.services.file_proxy_service import FileProxyService
from app.core.file_proxy_constants import FileProxyConfig

logger = get_logger(__name__)

# =============================================================================
# CONTEXT VARIABLE FOR SESSION MANAGEMENT
# =============================================================================

_current_auto_session: contextvars.ContextVar[Optional['AutoWorkspaceSession']] = contextvars.ContextVar(
    'auto_workspace_session', 
    default=None
)

def _get_current_auto_session() -> 'AutoWorkspaceSession':
    """
    Get the current auto-workspace session from context variables.
    
    Returns:
        AutoWorkspaceSession: The currently active session
        
    Raises:
        RuntimeError: If no session is active in current context
    """
    try:
        session = _current_auto_session.get()
    except LookupError:
        raise RuntimeError(
            "No auto-workspace session found in context. "
            "Make sure you're calling this within an 'async with AutoWorkspaceSession()' block."
        )
    
    if session is None:
        raise RuntimeError(
            "Auto-workspace session is None in current context. "
            "Make sure you're calling this within an active session block."
        )
    
    return session


class AutoWorkspaceSession:
    """
    Automatic workspace session manager that creates and manages a default workspace
    transparently, eliminating the need for LLMs to explicitly create workspaces.
    
    Usage:
        async with AutoWorkspaceSession() as session:
            # Tools automatically use the default workspace
            result = await execute_code("import pandas as pd")
            await upload_file("https://example.com/data.csv", "data.csv")
            result = await execute_code("df = pd.read_csv('data.csv')")
        
        # Workspace automatically cleaned up here
    """
    
    def __init__(self, session_id: Optional[str] = None, default_ttl_hours: int = 6):
        """
        Initialize auto-workspace session.
        
        Args:
            session_id: Optional custom session ID
            default_ttl_hours: TTL for the default workspace (default: 6 hours)
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.default_ttl_hours = default_ttl_hours
        
        # Default workspace management
        self._default_workspace_id: Optional[str] = None
        self._default_workspace_healthy = False
        self._last_health_check: Optional[datetime] = None
        
        # Track all workspaces for cleanup (including default)
        self.tracked_workspaces: Set[str] = set()
        
        # Initialize services
        self.workspace_service = WorkspaceService()
        self.file_service = FileService()
        self.execution_service = ExecutionService()
        
        # Cleanup state
        self._cleanup_completed = False
        self._cleanup_errors: List[str] = []
        
        logger.info(f"AutoWorkspaceSession {self.session_id} initialized (default TTL: {default_ttl_hours}h)")
    
    async def __aenter__(self) -> 'AutoWorkspaceSession':
        """Enter context manager and set session in context"""
        logger.info(f"Starting auto-workspace session {self.session_id}")
        
        # Set this session as the current session in context variables
        self._context_token = _current_auto_session.set(self)
        logger.debug(f"Session {self.session_id}: Set as current auto-session in context")
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager with automatic cleanup"""
        try:
            await self.cleanup_all_workspaces()
        finally:
            # Always reset the context variable
            if hasattr(self, '_context_token'):
                _current_auto_session.reset(self._context_token)
                logger.debug(f"Session {self.session_id}: Cleared from context")
        
        # Log session summary
        if exc_type:
            logger.info(f"AutoWorkspaceSession {self.session_id} ended with exception: {exc_type.__name__}")
        else:
            logger.info(f"AutoWorkspaceSession {self.session_id} completed successfully")
    
    # =============================================================================
    # AUTO-WORKSPACE MANAGEMENT
    # =============================================================================
    
    async def get_default_workspace_id(self) -> str:
        """
        Get or create the default workspace for this session.
        
        Returns:
            str: Default workspace ID
            
        Raises:
            RuntimeError: If workspace creation fails
        """
        # Check if we have a healthy default workspace
        if self._default_workspace_id and await self._is_default_workspace_healthy():
            return self._default_workspace_id
        
        # Create new default workspace
        logger.info(f"Session {self.session_id}: Creating default workspace")
        result = await self.workspace_service.create_workspace(self.default_ttl_hours)
        
        if result.success and result.workspace_info:
            self._default_workspace_id = result.workspace_info.workspace_id
            self._default_workspace_healthy = True
            self._last_health_check = datetime.now()
            
            # Track for cleanup
            self.tracked_workspaces.add(self._default_workspace_id)
            
            logger.info(f"Session {self.session_id}: Default workspace created: {self._default_workspace_id}")
            return self._default_workspace_id
        else:
            error_msg = f"Failed to create default workspace: {result.error}"
            logger.error(f"Session {self.session_id}: {error_msg}")
            raise RuntimeError(error_msg)
    
    async def _is_default_workspace_healthy(self) -> bool:
        """
        Check if the default workspace is still healthy.
        Uses caching to avoid excessive API calls.
        """
        if not self._default_workspace_id:
            return False
        
        # Use cached result if checked recently (within 30 seconds)
        now = datetime.now()
        if (self._last_health_check and 
            (now - self._last_health_check).total_seconds() < 30 and 
            self._default_workspace_healthy):
            return True
        
        # Check workspace health
        try:
            result = await self.workspace_service.get_workspace(self._default_workspace_id)
            self._default_workspace_healthy = result.success
            self._last_health_check = now
            
            if not result.success:
                logger.warning(f"Session {self.session_id}: Default workspace {self._default_workspace_id} is unhealthy")
            
            return result.success
        except Exception as e:
            logger.warning(f"Session {self.session_id}: Health check failed for default workspace: {e}")
            self._default_workspace_healthy = False
            self._last_health_check = now
            return False
    
    # =============================================================================
    # SIMPLIFIED SERVICE METHODS
    # =============================================================================
    
    async def execute_code(self, code: str) -> ExecutionOperationResult:
        """
        Execute Python code in the default workspace.
        
        Args:
            code: Python code to execute
            
        Returns:
            ExecutionOperationResult with execution details
        """
        workspace_id = await self.get_default_workspace_id()
        logger.info(f"Session {self.session_id}: Executing code in default workspace {workspace_id}")
        
        try:
            result = await self.execution_service.execute_code(workspace_id, code)
            
            # Handle file persistence
            if result.success and result.execution_result and result.execution_result.generated_files:
                logger.info(f"Session {self.session_id}: Code execution generated {len(result.execution_result.generated_files)} files")
                await self._persist_generated_files_to_storage(workspace_id, result.execution_result.generated_files)
            
            return result
            
        except Exception as e:
            # Check if this is a workspace-not-found error and try recovery
            if "not found" in str(e).lower() or "workspace" in str(e).lower():
                logger.warning(f"Session {self.session_id}: Workspace error detected, attempting recovery: {e}")
                
                # Mark default workspace as unhealthy and retry
                self._default_workspace_healthy = False
                self._default_workspace_id = None
                
                # Get new workspace and retry
                new_workspace_id = await self.get_default_workspace_id()
                logger.info(f"Session {self.session_id}: Retrying code execution with new workspace {new_workspace_id}")
                
                result = await self.execution_service.execute_code(new_workspace_id, code)
                
                # Handle file persistence for retry
                if result.success and result.execution_result and result.execution_result.generated_files:
                    await self._persist_generated_files_to_storage(new_workspace_id, result.execution_result.generated_files)
                
                return result
            else:
                # Re-raise non-workspace errors
                raise
    
    async def upload_file(self, file_url: str, file_name: str) -> FileUploadResult:
        """
        Upload file from URL to the default workspace.
        
        Args:
            file_url: HTTP URL to download from
            file_name: Name for the file in workspace
            
        Returns:
            FileUploadResult with upload status
        """
        workspace_id = await self.get_default_workspace_id()
        logger.info(f"Session {self.session_id}: Uploading {file_name} to default workspace {workspace_id}")
        
        try:
            return await self.file_service.download_and_upload_file_to_workspace(
                workspace_id, file_url, file_name
            )
        except Exception as e:
            # Check if this is a workspace-not-found error and try recovery
            if "not found" in str(e).lower() or "workspace" in str(e).lower():
                logger.warning(f"Session {self.session_id}: Workspace error during upload, attempting recovery: {e}")
                
                # Mark default workspace as unhealthy and retry
                self._default_workspace_healthy = False
                self._default_workspace_id = None
                
                # Get new workspace and retry
                new_workspace_id = await self.get_default_workspace_id()
                logger.info(f"Session {self.session_id}: Retrying upload with new workspace {new_workspace_id}")
                
                return await self.file_service.download_and_upload_file_to_workspace(
                    new_workspace_id, file_url, file_name
                )
            else:
                # Re-raise non-workspace errors
                raise
    
    # =============================================================================
    # FILE PERSISTENCE (Same as original)
    # =============================================================================
    
    async def _persist_generated_files_to_storage(self, workspace_id: str, generated_files: List[FileInfo]) -> None:
        """Persist generated files from sandbox to permanent storage"""
        from app.services.storage.storage import S3StorageBackend
        
        persist_count = 0
        total_files = len(generated_files)
        
        logger.info(f"Session {self.session_id}: Persisting {total_files} generated files to permanent storage")
        
        storage_backend = S3StorageBackend()
        
        for i, file_info in enumerate(generated_files, 1):
            try:
                logger.debug(f"Session {self.session_id}: Persisting file {i}/{total_files}: {file_info.filename}")
                
                # Download from sandbox
                download_result = await self.file_service.download_file(workspace_id, file_info.relative_path)
                
                if not download_result.success or download_result.content is None:
                    logger.error(f"Session {self.session_id}: Failed to download {file_info.filename}")
                    continue
                
                # Generate storage key
                date_prefix = datetime.now().strftime("%Y_%m_%d")
                unique_id = uuid.uuid4().hex[:8]
                proxy_filename = f"{FileProxyConfig.CODE_GENERATED_FILE_PREFIX}_{date_prefix}_{unique_id}_{file_info.filename}"
                storage_key = f"{FileProxyConfig.CODE_SANDBOX_GENERATED_PREFIX}/{proxy_filename}"
                
                # Upload to permanent storage
                await storage_backend.upload_file(
                    file_data=download_result.content,
                    key=storage_key,
                    content_type=file_info.mime_type or "application/octet-stream"
                )
                
                # Generate proxy URL
                file_proxy_service = FileProxyService()
                permanent_url = file_proxy_service.generate_code_generated_proxy_url(proxy_filename)
                
                # Update file info
                original_url = file_info.download_url
                file_info.download_url = permanent_url
                
                persist_count += 1
                logger.info(f"Session {self.session_id}: Persisted {file_info.filename} -> {permanent_url}")
                
            except Exception as e:
                logger.error(f"Session {self.session_id}: Failed to persist {file_info.filename}: {e}")
        
        if persist_count > 0:
            logger.info(f"Session {self.session_id}: File persistence completed - {persist_count}/{total_files} files persisted")
        else:
            logger.warning(f"Session {self.session_id}: File persistence failed - 0/{total_files} files persisted")
    
    # =============================================================================
    # CLEANUP METHODS
    # =============================================================================
    
    async def cleanup_all_workspaces(self) -> Dict[str, Any]:
        """Clean up all tracked workspaces"""
        if self._cleanup_completed:
            return {
                "session_id": self.session_id,
                "workspaces_cleaned": 0,
                "already_completed": True
            }
        
        workspace_count = len(self.tracked_workspaces)
        if workspace_count == 0:
            self._cleanup_completed = True
            return {
                "session_id": self.session_id,
                "workspaces_cleaned": 0
            }
        
        logger.info(f"Session {self.session_id}: Cleaning up {workspace_count} workspaces...")
        
        cleaned_count = 0
        cleanup_errors = []
        
        # Clean up all workspaces
        workspaces_to_cleanup = self.tracked_workspaces.copy()
        
        for workspace_id in workspaces_to_cleanup:
            try:
                result = await self.workspace_service.delete_workspace(workspace_id)
                if result.success:
                    cleaned_count += 1
                    self.tracked_workspaces.discard(workspace_id)
                else:
                    cleanup_errors.append(f"Failed to cleanup workspace {workspace_id}")
            except Exception as e:
                error_msg = f"Exception cleaning workspace {workspace_id}: {e}"
                cleanup_errors.append(error_msg)
                logger.error(f"Session {self.session_id}: Exception cleaning {workspace_id}: {e}")
        
        self._cleanup_completed = True
        
        logger.info(f"Session {self.session_id}: Cleanup completed - {cleaned_count}/{workspace_count} workspaces cleaned")
        
        return {
            "session_id": self.session_id,
            "workspaces_cleaned": cleaned_count,
            "workspaces_failed": len(cleanup_errors),
            "errors": cleanup_errors
        }
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        return {
            "session_id": self.session_id,
            "default_workspace_id": self._default_workspace_id,
            "default_workspace_healthy": self._default_workspace_healthy,
            "tracked_workspaces": len(self.tracked_workspaces),
            "workspace_ids": list(self.tracked_workspaces),
            "cleanup_completed": self._cleanup_completed
        }


# =============================================================================
# SIMPLIFIED TOOL FUNCTIONS
# =============================================================================

async def execute_code_auto(code: str) -> ExecutionOperationResult:
    """
    Execute Python code in the default workspace (auto-managed).
    
    Args:
        code: Python code to execute
        
    Returns:
        ExecutionOperationResult with execution details
    """
    try:
        session = _get_current_auto_session()
        return await session.execute_code(code)
    except RuntimeError as e:
        error_msg = f"Cannot execute code: {str(e)}"
        logger.error(f"execute_code_auto error: {error_msg}")
        return ExecutionOperationResult.error_result(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during code execution: {str(e)}"
        logger.error(f"execute_code_auto unexpected error: {error_msg}", exc_info=True)
        return ExecutionOperationResult.error_result(error_msg)


async def upload_file_auto(file_url: str, file_name: str) -> FileUploadResult:
    """
    Upload file from URL to the default workspace (auto-managed).
    
    Args:
        file_url: HTTP URL to download from
        file_name: Name for the file in workspace
        
    Returns:
        FileUploadResult with upload status
    """
    try:
        session = _get_current_auto_session()
        return await session.upload_file(file_url, file_name)
    except RuntimeError as e:
        error_msg = f"Cannot upload file '{file_name}': {str(e)}"
        logger.error(f"upload_file_auto error: {error_msg}")
        return FileUploadResult.error_result(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during file upload '{file_name}': {str(e)}"
        logger.error(f"upload_file_auto unexpected error: {error_msg}", exc_info=True)
        return FileUploadResult.error_result(error_msg)


def get_auto_workspace_callables() -> Dict[str, Callable[..., Any]]:
    """
    Get the raw callable functions for all auto-workspace tools.
    
    Returns:
        Dict mapping tool names to their underlying callable functions
    """
    return {
        'execute_code': execute_code_auto,
        'upload_file': upload_file_auto
    }

# =============================================================================
# TOOL REGISTRY FOR AUTO-WORKSPACE TOOLS
# =============================================================================

class AutoWorkspaceToolNames:
    """Tool names for auto workspace session tools"""
    AUTO_EXECUTE_CODE = "execute_code"
    AUTO_UPLOAD_FILE = "upload_file"

class AutoWorkspaceToolsInfo:
    """
    Information about the auto workspace tools for tool registry system.
    
    This provides metadata about auto workspace tools that is used by:
    - Tool event formatters for display names
    - Tool registry for categorization
    - Streaming event handlers for tool identification
    """
    TOOL_TYPE: str = "auto_workspace"
    TOOL_NAMES: List[str] = [
        AutoWorkspaceToolNames.AUTO_EXECUTE_CODE,
        AutoWorkspaceToolNames.AUTO_UPLOAD_FILE
    ]

# Tool descriptions for the simplified interface
EXECUTE_CODE_AUTO_DESCRIPTION = """
# CODE EXECUTION INSTRUCTIONS:
Execute Python code in an isolated code execution environment with persistent state and file generation capabilities.
Do not download files from internet in code execution environment,instead provide url in upload file tool to upload it and then later use it in the code.

Make sure to strictly follow all the code execution instructions and requirements below.

## CRITICAL REQUIREMENT FOR CODE EXECUTION: 
- ALWAYS check if the execution succeeded before using any outputs

## CRITICAL TIMEOUT HANDLING:
- If a piece of code times-out, do not execute **the same timed-out code** again.
- DO NOT make up or estimate results for failed or timed out code executions
- If you receive a timeout error, you MUST:
    1. Analyze why the code timed out
    2. Optimize the code (e.g., use more efficient algorithms)
    3. Reduce computational complexity
    4. Only then try to execute the OPTIMIZED code
- NEVER retry the exact same code after a timeout

## REQUIRED PARAMETERS:
- code: Python code string

## RETURN VALUE STRUCTURE:
The tool returns an ExecutionOperationResult containing:
- **success**: boolean indicating if execution completed successfully
- **standard output**: text that was printed during execution  
- **error messages**: any error messages that occurred
- **generated files**: list of files created during execution with full HTTP download URLs
- **result data**: the final computed result (if any)

## CODE EXECUTION ENVIRONMENT:
- Jupyter kernel with persistent variables/imports across calls
- Working directory: workspace root (contains uploaded files)
- Pre-installed 3rd-party packages (e.g., not exhaustive):
  - Data / science: numpy, pandas, matplotlib, seaborn, scikit-learn, scipy, statsmodels, etc.
  - File & doc I/O: openpyxl, python-docx, pypdf, pdfplumber, pdf2image, etc.
  - Image & OCR: pillow, opencv, pytesseract, etc.
  - NLP / text utils: nltk, markdown, langdetect, etc.
  ...many other popular PyPI libraries are also available.
- For OCR, use pdf2image and pytesseract to extract text from images for pdf files.
- Output capture: stdout, stderr, and execution results
- Your code will be executed with a timeout of 30 seconds.

## CRITICAL FILE ACCESS WORKFLOW:
**NEVER download URLs directly in Python code** - use upload_file tool instead!

**CORRECT WORKFLOW:**
1. **First**: Use upload_file tool for ANY external file/image URLs (especially proxy URLs like http://localhost:8000/api/v1/proxy/*)
2. **Then**: Access the uploaded file locally by filename in your Python code

**WRONG:**
```python
import requests
img = Image.open(requests.get('http://localhost:8000/api/v1/proxy/images/img_123', stream=True).raw)
```

**CORRECT:**
```python
# After using upload_file tool to upload the image first
img = Image.open('image_filename.jpg')  # Direct local access
```

## FILE OPERATIONS:
- **Read uploaded files**: open('filename.txt', 'r') - access files uploaded via upload_file tool
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
"""

UPLOAD_FILE_AUTO_DESCRIPTION = """
Upload a file from a URL to the code execution environment so it can be accessed locally by Python code.

**ALWAYS use this tool FIRST before accessing any external files in Python code!**

## WHEN TO USE THIS TOOL:
- **REQUIRED** for ALL proxy URLs (http://localhost:8000/api/v1/proxy/*)
- **REQUIRED** for any external web URLs you want to process in Python
- **REQUIRED** before any file processing operations in code execution

## WORKFLOW:
1. **First**: Call upload_file with the URL and desired filename
2. **Then**: Use execute_code to process the file locally by filename

## CRITICAL FILE UPLOAD INSTRUCTIONS:
- File URL must be a valid Full HTTP URL and the maximum file size allowed is 20MB.
- You must provide a file_name to be used for the file in the code execution environment.
- After uploading, access the file in Python code using ONLY the filename (not the original URL)

## REQUIRED PARAMETERS:
- file_url: Valid Full HTTP URL
- file_name: Name of the file

## RETURN VALUE STRUCTURE:
The tool returns a FileUploadResult containing:
- **success**: boolean indicating if upload completed successfully
- **file_info**: FileInfo object with details about the uploaded file
- **error**: Optional error message if upload failed

## EXAMPLES:

**For proxy URLs (images, documents, etc.):**
```
upload_file(file_url="http://localhost:8000/api/v1/proxy/images/img_8d9d8724", file_name="my_image.jpg")
# Then in Python: img = Image.open('my_image.jpg')
```

**For external URLs:**
```
upload_file(file_url="https://example.com/data.csv", file_name="data.csv")  
# Then in Python: df = pd.read_csv('data.csv')
```
"""


# Function tools for agent integration
@function_tool(
    name_override="execute_code",
    description_override=EXECUTE_CODE_AUTO_DESCRIPTION,
    strict_mode=True
)
async def execute_code_tool(code: str) -> ExecutionOperationResult:
    """Execute Python code tool with auto-workspace management"""
    return await execute_code_auto(code)


@function_tool(
    name_override="upload_file", 
    description_override=UPLOAD_FILE_AUTO_DESCRIPTION,
    strict_mode=True
)
async def upload_file_tool(file_url: str, file_name: str) -> FileUploadResult:
    """Upload file tool with auto-workspace management"""
    return await upload_file_auto(file_url, file_name)


def create_auto_workspace_tools() -> List:
    """
    Create auto-workspace tools for agent use.
    
    These tools automatically manage workspaces without requiring explicit
    workspace creation or workspace_id parameters from the LLM.
    
    Returns:
        List of function tools ready for agent use
    """
    return [
        execute_code_tool,
        upload_file_tool
    ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "AutoWorkspaceSession",
    "AutoWorkspaceToolsInfo", 
    "AutoWorkspaceToolNames",
    "create_auto_workspace_tools",
    "execute_code_auto",
    "upload_file_auto",
    "get_auto_workspace_callables"
]
