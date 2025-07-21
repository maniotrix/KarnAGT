import os
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from agents import Agent, RunContextWrapper, WebSearchTool, function_tool
from aicore.code_executor.new_code_tool import execute_code_func, execute_system_command_func, CodeExecutionResult, SystemCommandResult, DEFAULT_TIMEOUT
from aicore.code_executor.logger import get_logger
from aicore.prompt_utils import get_instructions_template, INITIAL_CORE_PROMPT

# Get logger with class-specific name
logger = get_logger("HTTPCodeExecutorAgent")

@dataclass
class FileMetadata:
    """
    Represents metadata for a single downloaded file.
    """
    filename: str
    download_url: str
    size: int
    mime_type: str
    created_at: str
    content: Optional[bytes] = None  # None for URL-only files
    
    @classmethod
    def from_dict(cls, filename: str, data: Dict[str, Any]) -> 'FileMetadata':
        """Create FileMetadata from dictionary data."""
        return cls(
            filename=filename,
            download_url=data.get("download_url", ""),
            size=data.get("size", 0),
            mime_type=data.get("mime_type", "application/octet-stream"),
            created_at=data.get("created_at", ""),
            content=data.get("content")
        )
    
    @classmethod
    def from_output_file(cls, file_info: Dict[str, Any]) -> 'FileMetadata':
        """Create FileMetadata from output_file info (URL-only)."""
        return cls(
            filename=file_info["name"],
            download_url=file_info.get("download_url", ""),
            size=file_info.get("size", 0),
            mime_type=file_info.get("mime_type", "application/octet-stream"),
            created_at=file_info.get("created_at", ""),
            content=None  # URL-only
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format when needed."""
        return {
            "content": self.content,
            "download_url": self.download_url,
            "size": self.size,
            "mime_type": self.mime_type,
            "created_at": self.created_at
        }
    
    def has_content(self) -> bool:
        """Check if this file has downloaded content."""
        return self.content is not None
    
    def is_image(self) -> bool:
        """Check if this file is an image."""
        return self.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif'))
    
    def is_plot(self) -> bool:
        """Check if this file is a plot/visualization."""
        return self.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.pdf', '.gif'))

@dataclass
class MessageFiles:
    """
    Represents all files associated with a specific message ID.
    """
    message_id: str
    files: Dict[str, FileMetadata] = field(default_factory=dict)
    
    def add_file(self, file_metadata: FileMetadata):
        """Add a file to this message."""
        self.files[file_metadata.filename] = file_metadata
    
    def add_files_from_dict(self, files_dict: Dict[str, Dict[str, Any]]):
        """Add files from dictionary format."""
        for filename, data in files_dict.items():
            self.add_file(FileMetadata.from_dict(filename, data))
    
    def add_files_from_output_list(self, output_files: List[Dict[str, Any]]):
        """Add files from output_files list (URL-only)."""
        for file_info in output_files:
            self.add_file(FileMetadata.from_output_file(file_info))
    
    def get_file_contents(self) -> Dict[str, bytes]:
        """Get files that have content (excluding URL-only files)."""
        result = {}
        for name, file in self.files.items():
            if file.has_content() and file.content is not None:
                result[name] = file.content
        return result
    
    def get_download_urls(self) -> Dict[str, str]:
        """Get download URLs for all files."""
        return {name: file.download_url for name, file in self.files.items()}
    
    def get_plot_files(self) -> Dict[str, FileMetadata]:
        """Get files that are plots/visualizations."""
        return {name: file for name, file in self.files.items() if file.is_plot()}
    
    def get_files_with_content(self) -> Dict[str, FileMetadata]:
        """Get files that have content."""
        return {name: file for name, file in self.files.items() if file.has_content()}
    
    def get_url_only_files(self) -> Dict[str, FileMetadata]:
        """Get files that are URL-only (no content)."""
        return {name: file for name, file in self.files.items() if not file.has_content()}
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to dictionary format when needed."""
        return {name: file.to_dict() for name, file in self.files.items()}
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about files in this message."""
        return {
            "total_files": len(self.files),
            "with_content": len(self.get_files_with_content()),
            "url_only": len(self.get_url_only_files()),
            "plots": len(self.get_plot_files()),
            "total_size": sum(file.size for file in self.files.values())
        }

@dataclass 
class DownloadedFilesTracker:
    """
    Manages downloaded files across all messages with proper typing and methods.
    """
    messages: Dict[str, MessageFiles] = field(default_factory=dict)
    
    def add_message_files(self, message_id: str, files_dict: Dict[str, Dict[str, Any]]):
        """Add files for a message from dictionary format."""
        if message_id not in self.messages:
            self.messages[message_id] = MessageFiles(message_id)
        self.messages[message_id].add_files_from_dict(files_dict)
    
    def add_output_files(self, message_id: str, output_files: List[Dict[str, Any]]):
        """Add URL-only files from output_files list."""
        if message_id not in self.messages:
            self.messages[message_id] = MessageFiles(message_id)
        self.messages[message_id].add_files_from_output_list(output_files)
    
    def get_message_files(self, message_id: str) -> Optional[MessageFiles]:
        """Get files for a specific message."""
        return self.messages.get(message_id)
    
    def get_file_contents_for_message(self, message_id: str) -> Dict[str, bytes]:
        """Get file contents for a message."""
        message_files = self.messages.get(message_id)
        return message_files.get_file_contents() if message_files else {}
    
    def get_file_metadata_for_message(self, message_id: str) -> Dict[str, Dict[str, Any]]:
        """Get file metadata for a message."""
        message_files = self.messages.get(message_id)
        return message_files.to_dict() if message_files else {}
    
    def get_download_urls_for_message(self, message_id: str) -> Dict[str, str]:
        """Get download URLs for a message."""
        message_files = self.messages.get(message_id)
        return message_files.get_download_urls() if message_files else {}
    
    def get_all_file_contents(self) -> Dict[str, Dict[str, bytes]]:
        """Get all file contents across messages."""
        result = {}
        for message_id, message_files in self.messages.items():
            content_files = message_files.get_file_contents()
            if content_files:  # Only include messages with content files
                result[message_id] = content_files
        return result
    
    def get_plots_by_message(self) -> Dict[str, List[str]]:
        """Get plot filenames grouped by message ID."""
        result = {}
        for message_id, message_files in self.messages.items():
            plot_files = message_files.get_plot_files()
            if plot_files:
                result[message_id] = sorted(plot_files.keys())
        return result
    
    def has_files_with_content(self, message_id: str = None) -> bool:
        """Check if there are files with content."""
        if message_id:
            message_files = self.messages.get(message_id)
            return bool(message_files and message_files.get_files_with_content())
        else:
            return any(message_files.get_files_with_content() for message_files in self.messages.values())
    
    def get_file_counts(self, message_id: str = None) -> Dict[str, int]:
        """Get counts of files with content vs URL-only files."""
        if message_id:
            message_files = self.messages.get(message_id)
            if message_files:
                stats = message_files.get_stats()
                return {"with_content": stats["with_content"], "url_only": stats["url_only"]}
            return {"with_content": 0, "url_only": 0}
        else:
            total_with_content = 0
            total_url_only = 0
            for message_files in self.messages.values():
                stats = message_files.get_stats()
                total_with_content += stats["with_content"]
                total_url_only += stats["url_only"]
            return {"with_content": total_with_content, "url_only": total_url_only}
    
    def clear_message(self, message_id: str = None):
        """Clear files for a specific message or all messages."""
        if message_id is None:
            self.messages.clear()
        elif message_id in self.messages:
            del self.messages[message_id]
    
    def get_overall_stats(self) -> Dict[str, int]:
        """Get overall statistics."""
        total_files = sum(len(msg.files) for msg in self.messages.values())
        total_size = sum(
            sum(file.size for file in msg.files.values()) 
            for msg in self.messages.values()
        )
        plot_messages = len(self.get_plots_by_message())
        
        return {
            "total_messages": len(self.messages),
            "total_files": total_files, 
            "total_size_bytes": total_size,
            "messages_with_plots": plot_messages
        }

class HTTPCodeExecutorAgent(Agent):
    """
    HTTP-based Code Executor Agent for FastAPI server execution.
    
    This agent uses HTTP-based code execution with automatic file downloading.
    No local file management - all files are handled via HTTP API calls.
    Files generated by tool executions are automatically tracked by message ID with full metadata
    using structured classes for better type safety and organization.
    
    File Tracking Architecture:
        - FileMetadata: Individual file with content, URL, size, mime_type, etc.
        - MessageFiles: Collection of files for a specific message
        - DownloadedFilesTracker: Overall tracking across all messages
    
    Modes:
        should_download_files=True:  Downloads file content + tracks URLs/metadata
        should_download_files=False: Tracks URLs/metadata only, no content download
        
    Usage:
        # URL-only mode (lightweight)
        agent = HTTPCodeExecutorAgent("Agent", should_download_files=False)
        await agent.run("Create a plot")
        urls = agent.get_download_urls_for_message(agent.current_message_id)
        
        # Full download mode  
        agent = HTTPCodeExecutorAgent("Agent", should_download_files=True)
        await agent.run("Create a plot")
        
        # Structured access to files
        message_files = agent.file_tracker.get_message_files(agent.current_message_id)
        if message_files:
            plot_files = message_files.get_plot_files()
            content_files = message_files.get_files_with_content()
            url_only = message_files.get_url_only_files()
            stats = message_files.get_stats()
    """
    
    def __init__(self, name: str, core_prompt: str = INITIAL_CORE_PROMPT, 
                model: str = "gpt-4o-mini-2024-07-18", 
                should_download_files: bool = False
                ):
        """
        Initialize the HTTP Code Executor Agent.
        
        Args:
            name: The name of the agent
            core_prompt: Core prompt for the agent
            model: Model to use for the agent
            should_download_files: Whether to download files from the server
        """
        self.core_prompt = core_prompt
        
        self.should_download_files = should_download_files
        
        # Track downloaded files with metadata from HTTP executions by message ID
        self.file_tracker = DownloadedFilesTracker()
        
        # Current message ID for the agent
        self.current_message_id = str(uuid.uuid4())[:8]
        
        # Get instructions template for HTTP-based execution
        self.instructions_template = get_instructions_template("outputs", core_prompt=self.core_prompt)
        
        # Initialize web search tool
        websearch_tool = WebSearchTool(user_location={"type": "approximate", "city": "New Delhi"})
        
        # Create wrapped tools that auto-capture files
        execute_code_wrapper = self._create_execute_code_wrapper()
        execute_system_command_wrapper = self._create_execute_system_command_wrapper()
        
        # Initialize the parent Agent class with wrapped tools
        super().__init__(
            name=name,
            instructions=self._get_dynamic_instructions,
            tools=[execute_code_wrapper, execute_system_command_wrapper, websearch_tool],
            model=model
        )
    
    def _get_dynamic_instructions(self, run_context: RunContextWrapper, agent: Agent) -> str:
        """
        Dynamically generate instructions with the current message ID.
        
        Args:
            run_context: The current run context
            agent: The agent instance
            
        Returns:
            str: Instructions with the message ID injected
        """
        return self.instructions_template.replace("{message_id}", self.current_message_id)
    
    def set_message_id(self, message_id=None):
        """
        Set the message ID for the next execution.
        
        Args:
            message_id: Custom message ID to use, or None to generate a new one
            
        Returns:
            str: The message ID that was set
        """
        if message_id is None:
            message_id = str(uuid.uuid4())[:8]
        
        self.current_message_id = message_id
        logger.info(f"Set message ID: {message_id}")
        return message_id
        
    def get_all_plots_with_message_id(self) -> Dict[str, List[str]]:
        """
        Extract all message IDs from downloaded files along with plot filenames.
        Returns a dictionary mapping each message ID to a list of its associated plot filenames.
        
        Returns:
            Dict mapping message_id -> list of plot filenames
        """
        return self.file_tracker.get_plots_by_message()
    
    def get_downloaded_files_for_message(self, message_id: str) -> Dict[str, bytes]:
        """
        Get all downloaded file contents for a specific message.
        Only returns files that have actual content (excludes URL-only files).
        
        Args:
            message_id: The message ID to get files for
            
        Returns:
            Dictionary mapping filename -> file content (bytes)
        """
        return self.file_tracker.get_file_contents_for_message(message_id)
    
    def get_file_metadata_for_message(self, message_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all file metadata for a specific message.
        Includes both downloaded and URL-only files.
        
        Args:
            message_id: The message ID to get files for
            
        Returns:
            Dictionary mapping filename -> file metadata dict
        """
        return self.file_tracker.get_file_metadata_for_message(message_id)
    
    def get_download_urls_for_message(self, message_id: str) -> Dict[str, str]:
        """
        Get download URLs for all files in a specific message.
        
        Args:
            message_id: The message ID to get URLs for
            
        Returns:
            Dictionary mapping filename -> download URL
        """
        return self.file_tracker.get_download_urls_for_message(message_id)
    
    def get_all_downloaded_files(self) -> Dict[str, Dict[str, bytes]]:
        """
        Get all downloaded file contents across all messages.
        Only returns files that have actual content (excludes URL-only files).
        
        Returns:
            Dictionary mapping message_id -> {filename -> file content}
        """
        return self.file_tracker.get_all_file_contents()
        
    def has_files_with_content(self, message_id: str = None) -> bool:
        """
        Check if files have actual content (not just URLs).
        
        Args:
            message_id: Check specific message, or None to check all messages
            
        Returns:
            True if there are files with content, False otherwise
        """
        return self.file_tracker.has_files_with_content(message_id)
    
    def get_file_counts(self, message_id: str = None) -> Dict[str, int]:
        """
        Get counts of files with content vs URL-only files.
        
        Args:
            message_id: Check specific message, or None for all messages
            
        Returns:
            Dict with 'with_content' and 'url_only' counts
        """
        return self.file_tracker.get_file_counts(message_id)
        
    def get_current_message_id(self) -> str:
        """
        Get the current message ID.
        
        Returns:
            str: The current message ID
        """
        return self.current_message_id
    
    def clear_downloaded_files(self, message_id: str = None):
        """
        Clear downloaded files for a specific message or all messages.
        
        Args:
            message_id: Specific message ID to clear, or None to clear all
        """
        self.file_tracker.clear_message(message_id)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about downloaded files.
        
        Returns:
            Dictionary with statistics
        """
        return self.file_tracker.get_overall_stats()
    
    def _create_execute_code_wrapper(self):
        """Create a wrapper function for execute_code that captures downloaded files with metadata."""
        
        # Capture reference to self for the closure
        _agent = self
        _download_files = _agent.should_download_files
        
        @function_tool(strict_mode=False)
        async def execute_code_with_tracking(
            code: str, 
            files: Optional[List[tuple]] = None, 
            timeout: int = DEFAULT_TIMEOUT,  # Agent explicitly enables file downloading for tracking
            *args: Any, 
            **kwargs: Any
        ) -> CodeExecutionResult:
            """
            Execute Python code via secure HTTP FastAPI server with automatic file tracking.
            
            This tool automatically captures any downloaded files and adds them to the
            agent's tracking system using the current message ID, preserving full metadata
            including download URLs.
            
            Args:
                code: Python code to execute
                files: Optional list of (filename, content) tuples to upload
                timeout: Execution timeout in seconds
                download_files: Whether to download generated files (default: True for agent tracking)
                *args: Additional args passed to execute_code
                **kwargs: Additional kwargs passed to execute_code
                
            Returns:
                CodeExecutionResult with execution results and downloaded files
            """
            logger.info(f"Agent executing code with auto file tracking (message: {_agent.current_message_id})")
            logger.info(f"Download mode: {'ENABLED' if _download_files else 'DISABLED'} (URLs only)")
            
            # Call the original execute_code tool from new_code_tool with explicit download_files=True
            result = await execute_code_func(code, files, timeout, _download_files, *args, **kwargs)
            
            # Handle file tracking based on what we got back
            if result.downloaded_files:
                # Files were downloaded with content
                _agent.file_tracker.add_message_files(_agent.current_message_id, result.downloaded_files)
                logger.info(f"Auto-captured {len(result.downloaded_files)} files with content for message {_agent.current_message_id}")
            elif result.output_files:
                # Files exist but weren't downloaded (URLs only)
                _agent.file_tracker.add_output_files(_agent.current_message_id, result.output_files)
                logger.info(f"Auto-captured {len(result.output_files)} files (URLs only) for message {_agent.current_message_id}")
            else:
                logger.info(f"No files generated for message {_agent.current_message_id}")
            
            return result
        
        return execute_code_with_tracking
    
    def _create_execute_system_command_wrapper(self):
        """Create a wrapper function for execute_system_command for consistency."""
        
        @function_tool(strict_mode=False)
        async def execute_system_command_with_tracking(
            command: str, 
            allowed_prefixes: Optional[List[str]] = None
        ) -> SystemCommandResult:
            """
            Execute system command via secure HTTP FastAPI server.
            
            Args:
                command: System command to execute
                allowed_prefixes: List of allowed command prefixes for security
                
            Returns:
                SystemCommandResult with command execution results
            """
            logger.info(f"Agent executing system command: {command}")
            
            # Call the original execute_system_command tool from new_code_tool
            result = await execute_system_command_func(command, allowed_prefixes)
            
            # System commands don't generate downloadable files, but log for completeness
            logger.info(f"System command completed with status: {result.status}")
            
            return result
        
        return execute_system_command_with_tracking
