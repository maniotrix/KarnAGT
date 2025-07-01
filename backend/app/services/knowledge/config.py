from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
import os
import json
import asyncio
from urllib.parse import urlparse
from pathlib import Path
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class QdrantConfig:
    """Comprehensive configuration for Qdrant vector store."""
    
    # Connection settings
    url: str
    collection_name: str
    api_key: Optional[str] = None
    timeout: Optional[int] = 30
    https: Optional[bool] = None
    
    # gRPC settings
    prefer_grpc: bool = False
    grpc_port: int = 6334
    grpc_options: Optional[Dict[str, Any]] = None
    
    # Vector settings
    vectors_config: Dict[str, Any] = field(default_factory=lambda: {
        "size": 1536,
        "distance": "Cosine"
    })
    
    # Collection creation settings
    shard_number: Optional[int] = 1
    replication_factor: Optional[int] = 1
    write_consistency_factor: Optional[int] = 1
    on_disk_payload: bool = False
    
    # Performance settings
    batch_size: int = 64
    max_retries: int = 3
    parallel_uploads: int = 1
    
    # Search settings
    search_limit: int = 10
    search_timeout: Optional[int] = None
    
    # Consistency settings
    read_consistency: Optional[Union[str, int]] = None
    write_consistency: Optional[str] = None
    
    # HNSW index configuration
    hnsw_config: Dict[str, Any] = field(default_factory=lambda: {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000,
    })
    
    # Quantization settings
    enable_quantization: bool = False
    quantization_config: Dict[str, Any] = field(default_factory=lambda: {
        "type": "scalar",
        "quantile": 0.99,
        "always_ram": True
    })
    
    # Advanced settings
    enable_hybrid_search: bool = False
    sparse_vectors_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate and normalize configuration after initialization."""
        # Auto-detect HTTPS from URL
        if self.https is None:
            self.https = self.url.startswith('https://')
        
        # Validate URL format
        if not self.validate_url(self.url):
            raise ValueError(f"Invalid Qdrant URL format: {self.url}")
        
        # Set default collection name if not provided
        if self.collection_name is None:
            self.collection_name = "default_collection"
        
        # Validate consistency settings
        self._validate_consistency_settings()
        
        logger.info(f"QdrantConfig initialized with URL: {self.url}")
    
    # =============================================================================
    # 🔧 INSTANCE METHODS - Operate on this specific configuration
    # =============================================================================
    
    def get_client_kwargs(self) -> Dict[str, Any]:
        """Get arguments for QdrantClient initialization."""
        kwargs = {
            "url": self.url,
            "timeout": self.timeout,
            "prefer_grpc": self.prefer_grpc,
            "grpc_port": self.grpc_port,
        }
        
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.https is not None:
            kwargs["https"] = self.https
        if self.grpc_options:
            kwargs["grpc_options"] = self.grpc_options
            
        # Remove None values
        return {k: v for k, v in kwargs.items() if v is not None}
    
    def get_collection_config(self) -> Dict[str, Any]:
        """Get configuration for collection creation."""
        config = {
            "vectors_config": self.vectors_config,
            "shard_number": self.shard_number,
            "replication_factor": self.replication_factor,
            "write_consistency_factor": self.write_consistency_factor,
            "on_disk_payload": self.on_disk_payload,
        }
        
        if self.hnsw_config:
            config["hnsw_config"] = self.hnsw_config
            
        if self.enable_quantization and self.quantization_config:
            config["quantization_config"] = self.quantization_config
            
        if self.sparse_vectors_config:
            config["sparse_vectors_config"] = self.sparse_vectors_config
            
        return {k: v for k, v in config.items() if v is not None}
    
    def get_upload_config(self) -> Dict[str, Any]:
        """Get configuration for bulk upload operations."""
        return {
            "batch_size": self.batch_size,
            "parallel": self.parallel_uploads,
            "max_retries": self.max_retries,
            "wait": True  # Wait for operations to complete
        }
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get configuration for search operations."""
        config = {
            "limit": self.search_limit,
            "timeout": self.search_timeout,
            "consistency": self.read_consistency,
        }
        return {k: v for k, v in config.items() if v is not None}
    
    def create_sync_client(self):
        """Create a synchronous Qdrant client with this configuration."""
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(**self.get_client_kwargs())
            logger.info("Synchronous Qdrant client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create sync client: {e}")
            raise
    
    def create_async_client(self):
        """Create an asynchronous Qdrant client with this configuration."""
        try:
            from qdrant_client import AsyncQdrantClient
            client = AsyncQdrantClient(**self.get_client_kwargs())
            logger.info("Asynchronous Qdrant client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create async client: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test connection to Qdrant server asynchronously."""
        client = None
        try:
            client = self.create_async_client()
            collections = await client.get_collections()
            logger.info(f"Connection test successful. Found {len(collections.collections)} collections")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        finally:
            if client:
                try:
                    await client.close()
                except:
                    pass
    
    async def ensure_collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """Ensure the collection exists, create it if it doesn't."""
        collection_name = collection_name or self.collection_name
        client = None
        try:
            client = self.create_async_client()
            
            # Check if collection exists
            try:
                await client.get_collection(collection_name)
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            except:
                # Collection doesn't exist, create it
                logger.info(f"Creating collection '{collection_name}'")
                
                # Import here to avoid circular imports
                from qdrant_client.models import VectorParams, Distance
                
                distance_map = {
                    "Cosine": Distance.COSINE,
                    "Euclidean": Distance.EUCLID,
                    "Dot": Distance.DOT
                }
                
                distance = distance_map.get(self.vectors_config["distance"], Distance.COSINE)
                
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vectors_config["size"],
                        distance=distance
                    ),
                    **{k: v for k, v in self.get_collection_config().items() 
                       if k not in ["vectors_config"]}
                )
                logger.info(f"Collection '{collection_name}' created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            return False
        finally:
            if client:
                try:
                    await client.close()
                except:
                    pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name) 
            for field in self.__dataclass_fields__.values()
        }
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to JSON file."""
        file_path = Path(file_path)
        try:
            with open(file_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _validate_consistency_settings(self) -> None:
        """Validate consistency settings."""
        valid_read = [None, "majority", "quorum", "all"] + list(range(1, 10))
        valid_write = [None, "weak", "medium", "strong"]
        
        if self.read_consistency not in valid_read:
            raise ValueError(f"Invalid read_consistency: {self.read_consistency}")
        
        if self.write_consistency not in valid_write:
            raise ValueError(f"Invalid write_consistency: {self.write_consistency}")
    
    # =============================================================================
    # 🏭 CLASS METHODS - Factory methods and alternative constructors
    # =============================================================================
    
    @classmethod
    def for_production(
        cls, 
        cloud_url: str, 
        api_key: str,
        collection_name: str = "production_collection"
    ) -> "QdrantConfig":
        """Create production configuration for Qdrant Cloud."""
        return cls(
            url=cloud_url,
            api_key=api_key,
            collection_name=collection_name,
            https=True,
            prefer_grpc=True,
            timeout=60,
            batch_size=128,
            parallel_uploads=4,
            max_retries=5,
            replication_factor=2,
            write_consistency_factor=2,
            read_consistency="majority",
            write_consistency="strong",
            enable_quantization=True,
            on_disk_payload=True,
            hnsw_config={
                "m": 32,
                "ef_construct": 200,
                "full_scan_threshold": 20000,
            }
        )
    
    @classmethod
    def for_local_development(cls, collection_name: str = "dev_collection") -> "QdrantConfig":
        """Create local development configuration."""
        return cls(
            url="http://localhost:6333",
            collection_name=collection_name,
            https=False,
            prefer_grpc=False,
            timeout=30,
            batch_size=32,
            parallel_uploads=1,
            max_retries=3,
            shard_number=1,
            replication_factor=1,
            enable_quantization=False,
            on_disk_payload=False
        )
    
    @classmethod
    def for_testing(cls, collection_name: str = "test_collection") -> "QdrantConfig":
        """Create testing configuration with minimal resources."""
        return cls(
            url="http://localhost:6333",
            collection_name=collection_name,
            timeout=10,
            batch_size=16,
            parallel_uploads=1,
            max_retries=1,
            shard_number=1,
            replication_factor=1,
            vectors_config={"size": 384, "distance": "Cosine"},  # Smaller vectors for testing
            hnsw_config={
                "m": 8,
                "ef_construct": 50,
                "full_scan_threshold": 1000,
            }
        )
    
    @classmethod
    def from_env(cls, prefix: str = "QDRANT_") -> "QdrantConfig":
        """Create configuration from environment variables."""
        return cls(
            url=os.getenv(f"{prefix}URL", "http://localhost:6333"),
            api_key=os.getenv(f"{prefix}API_KEY"),
            collection_name=os.getenv(f"{prefix}COLLECTION", "default_collection"),
            timeout=int(os.getenv(f"{prefix}TIMEOUT", "30")),
            prefer_grpc=os.getenv(f"{prefix}PREFER_GRPC", "false").lower() == "true",
            batch_size=int(os.getenv(f"{prefix}BATCH_SIZE", "64")),
            enable_quantization=os.getenv(f"{prefix}QUANTIZATION", "false").lower() == "true",
        )
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "QdrantConfig":
        """Load configuration from JSON file."""
        file_path = Path(file_path)
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
            
            # Ensure required fields have defaults if not present
            if 'url' not in config_dict:
                config_dict['url'] = "http://localhost:6333"
            if 'collection_name' not in config_dict:
                config_dict['collection_name'] = "default_collection"
                
            logger.info(f"Configuration loaded from {file_path}")
            return cls(**config_dict)
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            raise
    
    @classmethod
    def with_custom_vectors(
        cls, 
        vector_size: int, 
        distance_metric: str = "Cosine",
        url: str = "http://localhost:6333",
        collection_name: str = "custom_collection",
        **kwargs
    ) -> "QdrantConfig":
        """Create configuration with custom vector settings."""
        return cls(
            url=url,
            collection_name=collection_name,
            vectors_config={
                "size": vector_size,
                "distance": distance_metric
            },
            **kwargs
        )
    
    # =============================================================================
    # 🔧 STATIC METHODS - Utility functions
    # =============================================================================
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate Qdrant URL format."""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Check if scheme is valid
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Check if hostname exists
            if not parsed.hostname:
                return False
            
            # Check if port is specified or it's HTTPS (which has default port)
            if parsed.port is not None:
                return True
            elif parsed.scheme == 'https':
                return True
            else:
                return False
                
        except Exception:
            return False
    
    @staticmethod
    def get_default_ports() -> Dict[str, int]:
        """Get default Qdrant ports."""
        return {
            "http": 6333,
            "grpc": 6334,
            "dashboard": 6333
        }
    
    @staticmethod
    def get_supported_distances() -> List[str]:
        """Get list of supported distance metrics."""
        return ["Cosine", "Euclidean", "Dot"]
    
    @staticmethod
    def get_vector_size_for_model(model_name: str) -> int:
        """Get vector size for common embedding models."""
        model_sizes = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
        }
        return model_sizes.get(model_name, 1536)  # Default to OpenAI
    
    @staticmethod
    def estimate_memory_usage(
        num_vectors: int, 
        vector_size: int, 
        quantization: bool = False
    ) -> Dict[str, str]:
        """Estimate memory usage for given configuration."""
        # Base calculation: vector_size * 4 bytes (float32) * num_vectors
        base_memory = num_vectors * vector_size * 4
        
        if quantization:
            base_memory = base_memory // 4  # Rough estimate for quantization
        
        # Add overhead for HNSW index (approximately 2x)
        total_memory = base_memory * 2
        
        def format_bytes(bytes_val: int) -> str:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.2f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.2f} PB"
        
        return {
            "vectors_memory": format_bytes(base_memory),
            "total_estimated": format_bytes(total_memory),
            "quantization_enabled": str(quantization)
        }
    
    @staticmethod
    def parse_connection_string(connection_string: str) -> Dict[str, Any]:
        """Parse Qdrant connection string into components."""
        try:
            parsed = urlparse(connection_string)
            
            result = {
                "url": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 6333}",
                "host": parsed.hostname,
                "port": parsed.port or 6333,
                "https": parsed.scheme == "https"
            }
            
            # Extract API key from query parameters or username
            if parsed.query:
                from urllib.parse import parse_qs
                params = parse_qs(parsed.query)
                if "api_key" in params:
                    result["api_key"] = params["api_key"][0]
            
            if parsed.username:
                result["api_key"] = parsed.username
            
            return result
        except Exception as e:
            raise ValueError(f"Invalid connection string format: {e}")
    
    # =============================================================================
    # 📊 PROPERTIES - Computed values
    # =============================================================================
    
    @property
    def is_cloud_config(self) -> bool:
        """Check if this is a cloud configuration."""
        return self.api_key is not None
    
    @property
    def is_local_config(self) -> bool:
        """Check if this is a local configuration."""
        return "localhost" in self.url or "127.0.0.1" in self.url
    
    @property
    def connection_summary(self) -> str:
        """Get a summary of the connection configuration."""
        config_type = "Cloud" if self.is_cloud_config else "Local"
        protocol = "gRPC" if self.prefer_grpc else "HTTP"
        return f"{config_type} ({protocol}) - {self.url}"
    
    @property
    def estimated_performance_tier(self) -> str:
        """Estimate performance tier based on configuration."""
        if self.enable_quantization and self.parallel_uploads > 2:
            return "High Performance"
        elif self.prefer_grpc and self.batch_size > 64:
            return "Medium Performance" 
        else:
            return "Basic Performance"
    
    @property
    def memory_optimization_enabled(self) -> bool:
        """Check if memory optimization features are enabled."""
        return (
            self.enable_quantization or 
            self.on_disk_payload or 
            self.vectors_config.get("size", 1536) < 1536
        )
        
def get_default_qdrant_config(collection_name: str = "rag_collection") -> QdrantConfig:
    """Get default Qdrant configuration."""
    return QdrantConfig(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        collection_name=collection_name,
    )
    
    
@dataclass
class RAGConfig:
    """Configuration for RAG system."""
    
    # Model configuration
    llm_model: str = "gpt-4o-mini-2024-07-18"
    embedding_model: str = "text-embedding-3-large"  # Use the most accurate embedding model
    
    # Document processing - OPTIMIZED SETTINGS based on research
    chunk_size: int = 1024  # Optimal balance per LlamaIndex research
    chunk_overlap: int = 200  # Substantial overlap (20% of chunk_size)
    num_workers: int = 4  # Increased for better multiprocessing performance
    
    similarity_top_k: int = 12  # Balanced retrieval for comprehensive coverage
    
    # Performance settings
    enable_logging: bool = True
    enable_hybrid_search: bool = False
    max_concurrent_downloads: int = 8  # Increased for better S3 performance
    
    # Query settings - OPTIMIZED for better results
    response_mode: str = "tree_summarize"  # Best for multiple sources
    include_metadata: bool = True
    max_source_nodes: int = 8  # Balanced between quality and cost
    
    # File processing
    exclude_patterns: Optional[List[str]] = None
    supported_extensions: List[str] = field(default_factory=lambda: [
        ".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".csv", ".xlsx", ".md"
    ])
    
    # Rate limiting and delays
    enable_delay: bool = True
    delay_seconds: int = 2
    
    show_progress: bool = True
    
    s3_bucket_name: str = "rag-files"

    @classmethod
    def for_robust_retrieval(cls, **kwargs) -> "RAGConfig":
        """
        Create a robust RAG configuration that minimizes information loss.
        
        Based on research findings - handles metadata variations and ensures 
        comprehensive retrieval regardless of file processing differences.
        """
        defaults = {
            "chunk_size": 1024,  # Optimal size per research
            "chunk_overlap": 300,  # 30% overlap for maximum context preservation
            "similarity_top_k": 15,  # High retrieval to avoid missing information
            "response_mode": "tree_summarize",  # Best for combining multiple sources
            "max_source_nodes": 12,  # Allow many sources for completeness
            "num_workers": 6,  # Higher parallelism
            "max_concurrent_downloads": 10,
            "embedding_model": "text-embedding-3-large",  # Most accurate
        }
        
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_precise_retrieval(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for finding specific details (names, numbers, dates).
        Uses very large chunks to minimize information splitting.
        """
        defaults = {
            "chunk_size": 2048,  # Very large chunks
            "chunk_overlap": 512,  # 25% overlap
            "similarity_top_k": 20,  # Retrieve many candidates
            "response_mode": "tree_summarize",
            "max_source_nodes": 15,
            "embedding_model": "text-embedding-3-large",
        }
        
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_fast_processing(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for speed over completeness.
        """
        defaults = {
            "chunk_size": 512,  # Smaller chunks for speed
            "chunk_overlap": 50,  # Minimal overlap
            "similarity_top_k": 5,  # Fewer retrievals
            "num_workers": 8,  # Maximum parallelism
            "max_concurrent_downloads": 12,
            "response_mode": "compact",  # Faster processing
            "max_source_nodes": 5,
        }
        
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_cost_optimized(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for minimal token usage and costs.
        """
        defaults = {
            "llm_model": "gpt-4o-mini-2024-07-18",  # Cheapest quality model
            "embedding_model": "text-embedding-3-small",  # Cheaper embedding
            "chunk_size": 800,  # Moderate size
            "chunk_overlap": 100,  # Lower overlap
            "similarity_top_k": 6,  # Fewer retrievals
            "response_mode": "compact",
            "max_source_nodes": 5,
        }
        
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_gpt4(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for GPT-4 (expensive but highest quality).
        """
        defaults = {
            "llm_model": "gpt-4",
            "embedding_model": "text-embedding-3-large",  # Best embedding for best model
            "chunk_size": 1536,  # Larger chunks for better context
            "chunk_overlap": 256,  # ~17% overlap
            "similarity_top_k": 8,  # Moderate retrieval to control costs
            "response_mode": "tree_summarize",
            "max_source_nodes": 8,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_gpt4o_mini(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for GPT-4o-mini (best cost/performance ratio).
        """
        defaults = {
            "llm_model": "gpt-4o-mini-2024-07-18",
            "embedding_model": "text-embedding-3-large",  # Use best embedding with cheap LLM
            "chunk_size": 1024,  # Optimal size
            "chunk_overlap": 200,  # 20% overlap
            "similarity_top_k": 12,  # Higher since it's cheap
            "response_mode": "tree_summarize",
            "max_source_nodes": 10,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_gpt35_turbo(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for GPT-3.5-turbo (limited context window).
        """
        defaults = {
            "llm_model": "gpt-3.5-turbo",
            "embedding_model": "text-embedding-3-small",  # Match model tier
            "chunk_size": 800,  # Smaller for context limits
            "chunk_overlap": 150,  # ~19% overlap
            "similarity_top_k": 8,
            "response_mode": "compact",  # Simpler for GPT-3.5
            "max_source_nodes": 6,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_claude(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Claude models (massive context window).
        """
        defaults = {
            "llm_model": "claude-3-5-sonnet-20241022",
            "embedding_model": "text-embedding-3-large",
            "chunk_size": 2048,  # Large chunks for big context
            "chunk_overlap": 400,  # 20% overlap
            "similarity_top_k": 25,  # Many chunks since context is huge
            "response_mode": "tree_summarize",
            "max_source_nodes": 20,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    # =============================================================================
    # VECTOR STORE SPECIFIC CONFIGURATIONS
    # =============================================================================
    
    @classmethod
    def for_qdrant_production(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Qdrant (best accuracy, HNSW algorithm).
        Based on benchmark: 6-13min indexing, 10s for 10k queries.
        """
        defaults = {
            "chunk_size": 1024,  # Optimal for Qdrant HNSW
            "chunk_overlap": 200,  # 20% overlap
            "similarity_top_k": 10,  # Qdrant's accuracy allows lower k
            "response_mode": "tree_summarize",
            "max_source_nodes": 8,
            "embedding_model": "text-embedding-3-large",  # Best accuracy
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_chroma_development(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Chroma (good for prototyping).
        Based on benchmark: 39-268min indexing, 60s for 10k queries.
        """
        defaults = {
            "chunk_size": 1024,
            "chunk_overlap": 250,  # Higher overlap to compensate for lower accuracy
            "similarity_top_k": 15,  # Higher k due to potential misses
            "response_mode": "tree_summarize",
            "max_source_nodes": 12,
            "num_workers": 2,  # Chroma is single-threaded
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_faiss_speed(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for FAISS (fastest queries but accuracy varies by index type).
        Based on benchmark: Best query performance but requires custom scaling.
        """
        defaults = {
            "chunk_size": 1024,
            "chunk_overlap": 300,  # Higher overlap for accuracy compensation
            "similarity_top_k": 20,  # Higher k due to potential accuracy loss
            "response_mode": "tree_summarize",
            "max_source_nodes": 15,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_milvus_scale(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Milvus (distributed, high throughput).
        Based on benchmark: 15,000 QPS, 8ms latency.
        """
        defaults = {
            "chunk_size": 1024,
            "chunk_overlap": 200,
            "similarity_top_k": 12,
            "response_mode": "tree_summarize",
            "max_source_nodes": 10,
            "num_workers": 8,  # Take advantage of distributed processing
            "max_concurrent_downloads": 15,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_pinecone_cloud(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Pinecone (cloud-based, API rate limits).
        """
        defaults = {
            "chunk_size": 1024,
            "chunk_overlap": 200,
            "similarity_top_k": 8,  # Lower due to API costs
            "response_mode": "tree_summarize",
            "max_source_nodes": 8,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_weaviate_semantic(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for Weaviate (semantic search, hybrid capabilities).
        Based on benchmark: 10-30min indexing, 35s for 10k queries.
        """
        defaults = {
            "chunk_size": 1536,  # Larger for semantic understanding
            "chunk_overlap": 300,  # ~20% overlap
            "similarity_top_k": 12,
            "response_mode": "tree_summarize",
            "max_source_nodes": 10,
            "enable_hybrid_search": True,  # Take advantage of Weaviate's features
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    # =============================================================================
    # EMBEDDING MODEL SPECIFIC CONFIGURATIONS  
    # =============================================================================
    
    @classmethod
    def for_openai_ada_002(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for text-embedding-ada-002 (1536 dimensions, older model).
        """
        defaults = {
            "embedding_model": "text-embedding-ada-002",
            "chunk_size": 1024,  # Safe size for ada-002
            "chunk_overlap": 200,
            "similarity_top_k": 12,  # Slightly higher for older model
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_openai_3_large(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for text-embedding-3-large (3072 dimensions, best accuracy).
        """
        defaults = {
            "embedding_model": "text-embedding-3-large",
            "chunk_size": 1024,  # Optimal for best model
            "chunk_overlap": 200,
            "similarity_top_k": 10,  # Lower k due to high accuracy
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_sentence_transformers(cls, model_name: str = "all-MiniLM-L6-v2", **kwargs) -> "RAGConfig":
        """
        Optimized for Sentence Transformers models (384-768 dimensions).
        """
        # Model-specific chunk sizes
        chunk_sizes = {
            "all-MiniLM-L6-v2": 400,  # 384 dim
            "all-mpnet-base-v2": 600,  # 768 dim
        }
        
        defaults = {
            "embedding_model": model_name,
            "chunk_size": chunk_sizes.get(model_name, 400),
            "chunk_overlap": 80,  # 20% of smaller chunk
            "similarity_top_k": 15,  # More chunks since they're smaller
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    # =============================================================================
    # CHAT APPLICATION SPECIFIC CONFIGURATIONS
    # =============================================================================
    
    @classmethod
    def for_chat_application(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for ChatGPT-like chat applications where users upload documents 
        to chat threads and ask questions about them.
        
        Key considerations:
        - Users expect comprehensive answers (like ChatGPT)
        - Documents are contextually related (user uploaded together)
        - Missing relevant info is worse than extra context
        - Balance between coverage and response speed
        - Cost-conscious but quality-focused
        """
        defaults = {
            "llm_model": "gpt-4o-mini-2024-07-18",  # Best cost/performance for chat
            "embedding_model": "text-embedding-3-large",  # Best accuracy
            "chunk_size": 1024,  # Optimal balance
            "chunk_overlap": 200,  # 20% overlap
            "similarity_top_k": 8,  # Sweet spot for chat applications
            "response_mode": "tree_summarize",  # Best for multiple sources
            "max_source_nodes": 6,  # Focused but comprehensive
            "num_workers": 4,  # Fast processing
            "max_concurrent_downloads": 8,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_chat_single_document(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for single document uploads in chat (resumes, reports, etc.).
        Focus on precision within the document.
        """
        defaults = {
            "llm_model": "gpt-4o-mini-2024-07-18",
            "embedding_model": "text-embedding-3-large",
            "chunk_size": 1024,
            "chunk_overlap": 200,
            "similarity_top_k": 6,  # Lower for focused single doc
            "response_mode": "compact",  # Simpler for single source
            "max_source_nodes": 5,
        }
        defaults.update(kwargs)
        return cls(**defaults)
    
    @classmethod
    def for_chat_comprehensive(cls, **kwargs) -> "RAGConfig":
        """
        Optimized for complex multi-document questions in chat where users 
        need comprehensive coverage (research, analysis, etc.).
        """
        defaults = {
            "llm_model": "gpt-4o-mini-2024-07-18",
            "embedding_model": "text-embedding-3-large",
            "chunk_size": 1024,
            "chunk_overlap": 250,  # Higher overlap for completeness
            "similarity_top_k": 12,  # Higher for comprehensive coverage
            "response_mode": "tree_summarize",
            "max_source_nodes": 10,  # More sources for comprehensive answers
            
        }
        defaults.update(kwargs)
        return cls(**defaults)
