from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    
    # Model configuration
    llm_model: str = "gpt-4o-mini-2024-07-18"
    embedding_model: str = "text-embedding-ada-002"
    
    # Document processing
    chunk_size: int = 512
    chunk_overlap: int = 50
    num_workers: int = 2
    
    # Vector store configuration
    collection_name: str = "knowledge_base"
    similarity_top_k: int = 3
    
    # Qdrant specific settings
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_config: Dict[str, Any] = field(default_factory=lambda: {
        "size": 1536,  # OpenAI text-embedding-ada-002 dimensions
        "distance": "Cosine"
    })
    
    # Performance settings
    enable_logging: bool = True
    enable_hybrid_search: bool = False
    
    # Query settings
    response_mode: str = "tree_summarize"
    include_metadata: bool = True
    max_source_nodes: int = 5
    
    # File processing
    exclude_patterns: Optional[List[str]] = None
    supported_extensions: List[str] = field(default_factory=lambda: [
        ".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt"
    ])
    
    # Rate limiting and delays
    enable_delay: bool = True
    delay_seconds: int = 2