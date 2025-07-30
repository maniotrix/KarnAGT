from pathlib import Path
from typing import Optional



async def get_file_content(source: str, max_size_mb: int = 100, filename: Optional[str] = None) -> tuple[bytes, str]:
    """
    Get the content of a file from a local path or URL.
    
    Args:
        source: File path or URL
        
    Returns:
        File content as bytes
        Filename
    """
    try:
        # Handle local file
        path = Path(source)
        
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {source}")
        
        # Check file size
        if path.stat().st_size > max_size_mb * 1024 * 1024:
            raise ValueError(f"File too large: {path.stat().st_size} bytes")
        
        content = path.read_bytes()
        final_filename = filename or path.name
        
        return content, final_filename
    
    except FileNotFoundError:
        raise
    except ValueError:
        raise 
    except OSError as e:
        raise FileNotFoundError(f"Cannot access file {source}: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error getting file content from {source}: {e}")