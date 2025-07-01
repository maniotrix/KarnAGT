from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore # type: ignore
from llama_index.embeddings.openai import OpenAIEmbedding # type: ignore
from llama_index.llms.openai import OpenAI
from llama_index.core.readers.base import BaseReader
from llama_index.core import SimpleDirectoryReader
from app.utils.CustomPptxReader import OpenAIPptxReader
from qdrant_client import QdrantClient, AsyncQdrantClient
from typing import List, Dict, Any
import time
import logging
from dataclasses import dataclass

from app.services.knowledge.config import QdrantConfig, RAGConfig
from app.services.storage.storage import S3StorageBackend
from app.services.knowledge.s3_directory_reader import S3DirectoryReader


# Setup logging
logger = logging.getLogger(__name__)
@dataclass
class QueryWithResult:
    query: str
    result: Any
    sources: List[Any]
    query_time: float  # Time taken to process the query in seconds

class RAGService:
    """Main class for running RAG performance tests."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        logger.info(f"Initializing RAG Service with config: {config}")
        
        # Setup LlamaIndex settings
        logger.info(f"Setting up LLM: {self.config.llm_model}")
        Settings.llm = OpenAI(model=self.config.llm_model)
        
        # NOTE: This uses the default openai embedding model, not using config.embedding_model
        Settings.embed_model = OpenAIEmbedding()
        
        
    def get_file_extractor(self) -> Dict[str, BaseReader]:
        """Get file extractor for the RAG service."""
        pptx_reader = OpenAIPptxReader(enable_logging=self.config.enable_logging, 
                                        model_name=self.config.llm_model, 
                                        enable_delay=self.config.enable_delay, 
                                        delay_seconds=self.config.delay_seconds)
        
        file_extractor: Dict[str, BaseReader] = {
            ".pptx": pptx_reader,
            ".ppt": pptx_reader
        }
        
        logger.info("Successfully set up file extractor with pptx reader.")
        
        return file_extractor
        
    async def load_dir_documents_async(self, docs_dir: str) -> List[Document]:
        """Load documents asynchronously."""
        
        logger.info(f"Starting document loading from directory: {docs_dir}")
        print("📄 Creating new document reader...")
        
        file_extractor: Dict[str, BaseReader] = self.get_file_extractor()
        
        logger.info(f"Creating SimpleDirectoryReader with {self.config.num_workers} workers")
        reader = SimpleDirectoryReader(
            docs_dir, 
            file_extractor=file_extractor, 
            exclude=self.config.exclude_patterns
        )
        
        logger.info("Loading documents asynchronously...")
        documents = await reader.aload_data(show_progress=self.config.show_progress, 
                                            num_workers=self.config.num_workers)
        logger.info(f"Successfully loaded {len(documents)} documents")
        
        return documents
    
    async def load_s3_files_async(self, s3_bucket_name: str, s3_keys: List[str], add_s3_metadata: bool = True) -> List[Document]:
        """Load documents from S3 asynchronously with optimized resource management."""
        
        # Create reusable storage backend
        storage_backend = S3StorageBackend(bucket_name=s3_bucket_name)
        
        # Create S3 directory reader with configuration
        s3_reader = S3DirectoryReader(
            storage_backend=storage_backend,
            max_concurrent_downloads=self.config.max_concurrent_downloads
        )
        
        documents = await s3_reader.load_documents_from_s3_keys(
            s3_keys=s3_keys,
            file_extractor=self.get_file_extractor(),
            exclude_patterns=self.config.exclude_patterns,
            num_workers=self.config.num_workers,
            show_progress=self.config.show_progress,
            add_s3_metadata=True
        )
        return documents
    
    async def setup_vector_store(self, qdrant_config: QdrantConfig) -> StorageContext:
        """Setup vector store with Qdrant server (production setup)."""
        logger.info("Setting up Qdrant vector store")
        print("📝 Using Qdrant server (production-ready setup)...")
        
        # Create both sync and async clients for LlamaIndex compatibility
        logger.info("Creating Qdrant clients (sync and async)")
        client = QdrantClient(url=qdrant_config.url)
        aclient = AsyncQdrantClient(url=qdrant_config.url)
        
        logger.info(f"Using collection name: {qdrant_config.collection_name}")
        
        # Create collection with proper schema to avoid "text-dense" error
        try:
            logger.info("Attempting to delete existing collection")
            await aclient.delete_collection(qdrant_config.collection_name)
            logger.info("Successfully deleted existing collection")
            print("🗑️ Cleaned existing collection")
        except Exception as e:
            logger.info(f"No existing collection to delete: {e}")
            pass  # Collection doesn't exist
        
        # Create collection with proper vector configuration
        logger.info("Creating new collection with vector configuration")
        
        logger.info(f"Using Qdrant config: {qdrant_config}")
        
        await aclient.create_collection(
            collection_name=qdrant_config.collection_name,
            vectors_config=qdrant_config.vectors_config
        )
        logger.info("Collection created successfully")
        print("✅ Collection created with proper vector schema")
        
        logger.info("Creating QdrantVectorStore instance")
        vector_store = QdrantVectorStore(
            client=client, 
            aclient=aclient, 
            collection_name=qdrant_config.collection_name,
            enable_hybrid=False  # Disable for better performance
        )
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        logger.info("Vector store setup completed successfully")
        return storage_context
    
    def create_index(self, storage_context: StorageContext, docs: List[Document]) -> VectorStoreIndex:
        """Create or load vector index."""
        logger.info(f"Creating vector index from {len(docs)} documents")
        logger.info(f"Using chunk_size: {self.config.chunk_size}, chunk_overlap: {self.config.chunk_overlap}")
        
        node_parser = SentenceSplitter(
            chunk_size=self.config.chunk_size, 
            chunk_overlap=self.config.chunk_overlap
        )
        logger.info("Created SentenceSplitter for document chunking")
        
        # Create fresh index
        print("🆕 Creating fresh index (first time)...")
        logger.info("Starting document embedding and indexing process")
        index = VectorStoreIndex.from_documents(
            documents=docs,
            storage_context=storage_context,
            transformations=[node_parser],
            show_progress=self.config.show_progress
        )
        logger.info("Vector index created successfully")
        
        return index
    
    async def run_single_query_async(self, index: VectorStoreIndex, query: str) -> QueryWithResult:
        """Run a single query asynchronously."""
        logger.info(f"Running single query: {query}")
        
        # Create query engine
        logger.info(f"Creating query engine with similarity_top_k: {self.config.similarity_top_k}")
        query_engine = index.as_query_engine(
            similarity_top_k=self.config.similarity_top_k,
            response_mode="tree_summarize",
            verbose=True
        )
        logger.info("Query engine created successfully")
        
        logger.info(f"Processing query: {query}")
        start_time = time.time()
        
        response = await query_engine.aquery(query)
        query_time = time.time() - start_time
        
        logger.info(f"Query {query} completed in {query_time:.3f}s")
        
        if hasattr(response, 'source_nodes') and response.source_nodes:
            logger.info(f"Found {len(response.source_nodes)} source nodes for query {query}")
        else:
            logger.info(f"No source nodes found for query {query}")
            
        return QueryWithResult(query, response, response.source_nodes, query_time)
    
    async def run_queries_async(self, index: VectorStoreIndex, queries: List[str]) -> List[QueryWithResult]:
        """Run queries asynchronously but sequentially for clean output."""
        logger.info(f"Starting query processing for {len(queries)} queries")
        
        # Create query engine
        logger.info(f"Creating query engine with similarity_top_k: {self.config.similarity_top_k}")
        query_engine = index.as_query_engine(
            similarity_top_k=self.config.similarity_top_k,
            response_mode="tree_summarize",
            verbose=True
        )
        logger.info("Query engine created successfully")
        
        # create a list of QueryWithResult
        query_with_results: List[QueryWithResult] = []
        
        for i, query in enumerate(queries, 1):
            logger.info(f"Processing query {i}/{len(queries)}: {query}")
            start_time = time.time()
            
            response = await query_engine.aquery(query)
            query_time = time.time() - start_time
            
            logger.info(f"Query {i} completed in {query_time:.3f}s")
            
            if hasattr(response, 'source_nodes') and response.source_nodes:
                logger.info(f"Found {len(response.source_nodes)} source nodes for query {i}")
            else:
                logger.info(f"No source nodes found for query {i}")
            
            query_with_results.append(QueryWithResult(query, response, response.source_nodes, query_time))
        
        logger.info(f"Completed processing all {len(queries)} queries")
        return query_with_results
    
    
    async def get_query_index(self, docs_dir: str, qdrant_config: QdrantConfig) -> VectorStoreIndex:
        """Get the query index asynchronously."""
        logger.info(f"Getting query index for {docs_dir}")
        docs = await self.load_dir_documents_async(docs_dir)
        
        logger.info(f"Loaded {len(docs)} documents")
        storage_context = await self.setup_vector_store(qdrant_config)
        
        logger.info("Vector store setup completed successfully")
        index = self.create_index(storage_context, docs)
        logger.info("Index created successfully")
        return index
    
    async def get_query_index_from_s3(self, s3_bucket_name: str, 
                                    s3_keys: List[str], 
                                    qdrant_config: QdrantConfig,
                                    add_s3_metadata: bool = True) -> VectorStoreIndex:
        """Get the query index asynchronously from S3."""
        logger.info(f"Getting query index for {s3_bucket_name} and {s3_keys}")
        docs = await self.load_s3_files_async(s3_bucket_name, s3_keys, add_s3_metadata)
        logger.info(f"Loaded {len(docs)} documents")
        
        storage_context = await self.setup_vector_store(qdrant_config)
        logger.info("Vector store setup completed successfully")
        
        index = self.create_index(storage_context, docs)
        logger.info("Index created successfully")
        return index
    
    async def get_query_results(self, docs_dir: str, queries: List[str], qdrant_config: QdrantConfig) -> List[QueryWithResult]:
        """Get query results asynchronously."""
        index = await self.get_query_index(docs_dir, qdrant_config)
        logger.info(f"Running {len(queries)} queries")
        return await self.run_queries_async(index, queries)
    
    async def get_query_results_from_index(self, index: VectorStoreIndex, queries: List[str]) -> List[QueryWithResult]:
        """Get query results from an existing index asynchronously."""
        logger.info(f"Running {len(queries)} queries")
        return await self.run_queries_async(index, queries)
    