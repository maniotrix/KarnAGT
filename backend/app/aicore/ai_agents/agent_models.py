from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from app.logging.logger import get_logger

# Get logger with class-specific name
logger = get_logger(__name__)

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

