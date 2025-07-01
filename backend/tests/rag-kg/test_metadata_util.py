import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

# Configure logging BEFORE importing modules
def setup_logging(log_level=logging.DEBUG):
    """Configure comprehensive logging for the test."""
    
    # Clear any existing handlers to avoid conflicts
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger with detailed format
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)8s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Force reconfiguration
    )
    
    # Set specific logger levels for our modules
    loggers_to_configure = [
        ('app.services.knowledge.rag_service', logging.DEBUG),
        ('app.services.knowledge.metadata_util', logging.DEBUG), 
        ('app.services.knowledge.config', logging.INFO),
        ('llama_index.core', logging.WARNING),  # Reduce LlamaIndex noise
        ('openai', logging.WARNING),  # Reduce OpenAI API noise
        ('httpx', logging.WARNING),  # Reduce HTTP request noise
        ('urllib3', logging.WARNING),  # Reduce HTTP connection noise
    ]
    
    for logger_name, level in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True  # Ensure messages propagate to root logger
    
    print(f"📋 Logging configured at {logging.getLevelName(log_level)} level")
    print(f"🔍 Debug logging enabled for metadata cleaning components")

# Setup logging first - allow control via environment variable
log_level_name = os.getenv('LOG_LEVEL', 'DEBUG').upper()
log_level = getattr(logging, log_level_name, logging.DEBUG)
setup_logging(log_level)

# Now import after logging is configured
from app.services.knowledge.rag_service import RAGService
from app.services.knowledge.config import RAGConfig

def main():
    """Test metadata cleaning with comprehensive logging."""
    print("🔒 Testing Metadata Cleaning with Full Logging")
    print("=" * 60)
    
    # Create RAG service (this will trigger initialization logging)
    config = RAGConfig()
    rag_service = RAGService(config)
    
    # Test with realistic sensitive metadata that matches your use case
    sample_metadata = {
        'file_name': 'abhilasha_6_april_ticket.pdf',
        'file_path': 'C:\\Users\\Prince\\AppData\\Local\\Temp\\s3_docs_123\\file_abc123.pdf',
        's3_key': 'files/2025/01/07/file_abc123.pdf',
        's3_bucket': 'test-rag-bucket',
        's3_original_filename': 'abhilasha_6_april_ticket.pdf',
        'source_type': 's3',
        'page_label': '1',
        'questions_this_excerpt_can_answer': 'What is the passenger name?',
        'file_size': 1000,
        'file_type': 'application/pdf',
        'unknown_sensitive_key': 'sensitive_value'
    }
    
    print(f"📋 Testing with {len(sample_metadata)} metadata keys")
    print(f"🔍 Original keys: {list(sample_metadata.keys())}")
    
    # Test metadata cleaning (this will show debug logs)
    result = rag_service.test_metadata_cleaning(sample_metadata)
    
    print("\n📊 Test Results:")
    print(f"✅ Cleaned metadata keys: {list(result['cleaned_metadata'].keys())}")
    print(f"🗑️  Removed sensitive keys: {result['removed_keys']}")
    print(f"💾 Original preserved: {'Yes' if result['stored_original'] else 'No'}")
    print(f"📄 Safe filename: {result['cleaned_metadata'].get('file_name', 'N/A')}")
    
    # Test configuration methods
    print(f"\n🔧 Configuration Test:")
    print(f"📋 Default safe keys: {rag_service.metadata_cleaner.get_safe_metadata_keys()}")
    print(f"🚫 Sensitive keys: {rag_service.metadata_cleaner.get_sensitive_keys()}")
    
    # Test adding a custom safe key
    rag_service.metadata_cleaner.add_safe_key('custom_citation_info')
    print(f"➕ Added custom safe key")
    
    # Test with updated configuration
    result2 = rag_service.test_metadata_cleaning({
        'file_name': 'test.pdf',
        'custom_citation_info': 'Page 42',
        'file_path': '/sensitive/path',
        's3_bucket': 'private-bucket'
    })
    
    print(f"🔄 Updated test - kept keys: {list(result2['cleaned_metadata'].keys())}")
    print(f"🔄 Updated test - removed keys: {result2['removed_keys']}")
    
    print("\n✅ Metadata cleaning test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
    
    print("\n" + "="*60)
    print("💡 USAGE TIPS:")
    print("   • Run with: python test_metadata_util.py")
    print("   • Control logging: LOG_LEVEL=INFO python test_metadata_util.py")
    print("   • Available levels: DEBUG, INFO, WARNING, ERROR")
    print("   • DEBUG shows all metadata cleaning operations")
    print("   • INFO shows only key events and results")
    print("="*60)