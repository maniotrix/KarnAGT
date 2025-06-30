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
    embedding_model: str = "text-embedding-ada-002"
    
    # Document processing
    chunk_size: int = 512
    chunk_overlap: int = 50
    num_workers: int = 2
    
    similarity_top_k: int = 3
    
    # Performance settings
    enable_logging: bool = True
    enable_hybrid_search: bool = False
    max_concurrent_downloads: int = 5  # Maximum concurrent S3 downloads
    
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
    
    show_progress: bool = True
    
    s3_bucket_name: str = "rag-files"
