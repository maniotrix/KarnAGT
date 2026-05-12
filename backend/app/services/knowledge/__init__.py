"""Knowledge services package for document processing and RAG."""

from .rag_service import RAGService, QueryWithResult
from .production_rag_service import ProductionRAGService, ProcessingResult, QueryResult
from .knowledge_service import KnowledgeService
from .config import RAGConfig, QdrantConfig
from .metadata_util import MetadataCleanerPostprocessor
from .s3_directory_reader import S3DirectoryReader

__all__ = [
    # Original RAG service (good for testing/development)
    "RAGService",
    "QueryWithResult", 
    
    # Production RAG service (recommended for chat applications)
    "ProductionRAGService",
    "ProcessingResult",
    "QueryResult",
    
    # High-level knowledge service (recommended for tools)
    "KnowledgeService",
    
    # Configuration and utilities
    "RAGConfig",
    "QdrantConfig", 
    "MetadataCleanerPostprocessor",
    "S3DirectoryReader",
] 