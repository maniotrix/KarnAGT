from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.readers.base import BaseReader
from app.utils.CustomPptxReader import OpenAIPptxReader
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from typing import List, Dict, Any, Optional
import time
import logging
from dataclasses import dataclass

from app.services.knowledge.config import RAGConfig

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
        Settings.embed_model = OpenAIEmbedding()
        
    async def load_documents_async(self, docs_dir: str) -> List[Document]:
        """Load documents asynchronously."""
        from llama_index.core import SimpleDirectoryReader
        
        logger.info(f"Starting document loading from directory: {docs_dir}")
        print("📄 Creating new document reader...")
        
        logger.info("Setting up custom PPTX reader with config")
        pptx_reader = OpenAIPptxReader(enable_logging=self.config.enable_logging, 
                                        model_name=self.config.llm_model, 
                                        enable_delay=self.config.enable_delay, 
                                        delay_seconds=self.config.delay_seconds)
        file_extractor: Dict[str, BaseReader] = {
            ".pptx": pptx_reader,
            ".ppt": pptx_reader
        }
        
        logger.info(f"Creating SimpleDirectoryReader with {self.config.num_workers} workers")
        reader = SimpleDirectoryReader(
            docs_dir, 
            file_extractor=file_extractor, 
            exclude=self.config.exclude_patterns
        )
        
        logger.info("Loading documents asynchronously...")
        documents = await reader.aload_data(show_progress=True, num_workers=self.config.num_workers)
        logger.info(f"Successfully loaded {len(documents)} documents")
        
        return documents
    
    async def setup_vector_store(self) -> StorageContext:
        """Setup vector store with Qdrant server (production setup)."""
        logger.info("Setting up Qdrant vector store")
        print("📝 Using Qdrant server (production-ready setup)...")
        
        # Use Qdrant server for production-ready setup (fixes "text-dense" error)
        from qdrant_client.models import Distance, VectorParams
        
        # Create both sync and async clients for LlamaIndex compatibility
        logger.info("Creating Qdrant clients (sync and async)")
        client = QdrantClient(host="localhost", port=6333)
        aclient = AsyncQdrantClient(host="localhost", port=6333)
        
        collection_name = "rag_collection"
        logger.info(f"Using collection name: {collection_name}")
        
        # Create collection with proper schema to avoid "text-dense" error
        try:
            logger.info("Attempting to delete existing collection")
            await aclient.delete_collection(collection_name)
            logger.info("Successfully deleted existing collection")
            print("🗑️ Cleaned existing collection")
        except Exception as e:
            logger.info(f"No existing collection to delete: {e}")
            pass  # Collection doesn't exist
        
        # Create collection with proper vector configuration
        logger.info("Creating new collection with vector configuration")
        await aclient.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-ada-002 dimensions
                distance=Distance.COSINE
            )
        )
        logger.info("Collection created successfully")
        print("✅ Collection created with proper vector schema")
        
        logger.info("Creating QdrantVectorStore instance")
        vector_store = QdrantVectorStore(
            client=client, 
            aclient=aclient, 
            collection_name=collection_name,
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
            show_progress=True
        )
        logger.info("Vector index created successfully")
        
        return index
    
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
    
    
    async def get_query_index(self, docs_dir: str) -> VectorStoreIndex:
        """Get the query index asynchronously."""
        logger.info(f"Getting query index for {docs_dir}")
        docs = await self.load_documents_async(docs_dir)
        
        logger.info(f"Loaded {len(docs)} documents")
        storage_context = await self.setup_vector_store()
        
        logger.info("Vector store setup completed successfully")
        index = self.create_index(storage_context, docs)
        logger.info("Index created successfully")
        return index
    
    async def get_query_results(self, docs_dir: str, queries: List[str]) -> List[QueryWithResult]:
        """Get query results asynchronously."""
        index = await self.get_query_index(docs_dir)
        logger.info(f"Running {len(queries)} queries")
        return await self.run_queries_async(index, queries)
    
    async def get_query_results_from_index(self, index: VectorStoreIndex, queries: List[str]) -> List[QueryWithResult]:
        """Get query results from an existing index asynchronously."""
        logger.info(f"Running {len(queries)} queries")
        return await self.run_queries_async(index, queries)
    