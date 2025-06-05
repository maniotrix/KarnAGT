import gc
import glob
import os
import tempfile
import time
from contextlib import contextmanager

from aicore.code_executor.logger import get_logger

# Get logger
logger = get_logger()

@contextmanager
def execution_cleanup():
    """Context manager for resource cleanup after code execution."""
    try:
        yield
    finally:
        try:
            # Close any matplotlib resources
            try:
                import matplotlib.pyplot as plt
                plt.close('all')
            except ImportError:
                # matplotlib might not be imported yet
                pass
            
            # Clean up temporary files that might have been created during execution
            temp_dir = tempfile.gettempdir()
            current_time = time.time()
            for temp_file in glob.glob(os.path.join(temp_dir, "tmp*")):
                try:
                    # Check if file is older than 60 seconds and not in use
                    if os.path.isfile(temp_file) and os.path.getmtime(temp_file) < (current_time - 60):
                        os.unlink(temp_file)
                except (PermissionError, OSError):
                    # Skip files that are in use or can't be deleted
                    pass
                    
            # Force garbage collection
            gc.collect()
            
            logger.debug("Cleanup completed after processing prompt")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
