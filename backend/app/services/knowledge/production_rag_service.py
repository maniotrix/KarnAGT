"""
Production RAG Service using LlamaIndex IngestionPipeline for optimal document management.

This service implements production-ready patterns:
- Uses IngestionPipeline for automatic document deduplication
- Leverages DocstoreStrategy for smart processing
- Connects to existing infrastructure (S3, Qdrant, database)
- Provides proper state management and error handling
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# LlamaIndex production imports
from llama_index.core import Settings, Document, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline, DocstoreStrategy
from llama_index.core.storage import StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, AsyncQdrantClient

# Database and existing services
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from app.core.database import get_db
from app.models.database import KnowledgeFile, VectorCollection, User

# Existing infrastructure
from app.services.knowledge.config import QdrantConfig, RAGConfig, get_default_qdrant_config
from app.services.knowledge.metadata_util import MetadataCleanerPostprocessor
from app.services.knowledge.collection_compatibility import CollectionCompatibilityChecker, CompatibilityResult
from app.services.storage.storage import S3StorageBackend
from app.services.knowledge.s3_directory_reader import S3DirectoryReader

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    total_requested: int
    processed_count: int
    skipped_count: int
    failed_count: int
    processing_time: float
    processed_files: List[str]
    failed_files: List[str]
    collection_id: str
    compatibility_result: Optional[CompatibilityResult] = None  # Changed to CompatibilityResult
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requested == 0:
            return 100.0
        return (self.processed_count / self.total_requested) * 100


@dataclass
class QueryResult:
    """Result of query operation."""
    query: str
    response: str
    sources: List[Dict[str, Any]]
    query_time: float
    collection_id: str
    total_nodes_retrieved: int


class ProductionRAGService:
    """
    Production-ready RAG service using LlamaIndex IngestionPipeline.
    
    Key features:
    - Automatic document deduplication using LlamaIndex DocStore
    - Smart processing with DocstoreStrategy.UPSERTS 
    - Vector compatibility validation before processing
    - Integration with existing database models
    - Proper error handling and state management
    - Async-first design for production performance
    """
    
    def __init__(self, rag_config: RAGConfig, qdrant_config: Optional[QdrantConfig] = None):
        """Initialize production RAG service."""
        self.config = rag_config
        
        # Use provided qdrant config or get default
        self.qdrant_config = qdrant_config or get_default_qdrant_config()
        
        # Setup LlamaIndex global settings
        Settings.llm = OpenAI(model=self.config.llm_model)
        Settings.embed_model = OpenAIEmbedding(model=self.config.embedding_model)
        Settings.text_splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        # Initialize metadata cleaner for security
        self.metadata_cleaner = MetadataCleanerPostprocessor()
        
        # Initialize compatibility checker for production safety
        self.compatibility_checker = CollectionCompatibilityChecker(rag_config)
        
        logger.info(f"ProductionRAGService initialized with config: {self.config.llm_model}")
        logger.info(f"Using Qdrant: {self.qdrant_config.url}")

    async def get_or_create_collection(
        self, 
        user_id: int, 
        collection_name: Optional[str] = None,
        display_name: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> VectorCollection:
        """Get existing collection from or create new one with proper state tracking as per qdrant config."""
        
        if db is None:
            async for db_session in get_db():
                db = db_session
                break
        
        # Use qdrant config collection name if not provided
        if collection_name is None:
            collection_name = self.qdrant_config.collection_name
        
        # Check if collection exists
        result = await db.execute(
            select(VectorCollection).where(
                and_(
                    VectorCollection.user_id == user_id,
                    VectorCollection.collection_name == collection_name
                )
            )
        )
        collection = result.scalar_one_or_none()
        
        if collection:
            logger.info(f"Found existing collection: {collection_name}")
            return collection
        
        # Create new collection using config
        logger.info(f"Creating new collection: {collection_name}")
        
        # Get vector size from config
        vector_size = QdrantConfig.get_vector_size_for_model(self.config.embedding_model)
        
        collection = VectorCollection(
            id=f"col_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            collection_name=collection_name,
            display_name=display_name or f"Collection {collection_name}",
            qdrant_url=self.qdrant_config.url,
            vector_size=vector_size,
            distance_metric=self.qdrant_config.vectors_config["distance"],
            embedding_model=self.config.embedding_model,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            status="active",
            health_status="healthy"
        )
        
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        
        logger.info(f"Created collection: {collection.id}")
        return collection

    async def validate_collection_compatibility(
        self, 
        collection: VectorCollection,
        new_embedding_model: Optional[str] = None
    ) -> CompatibilityResult:
        """
        Validate if new documents can be added to existing collection.
        
        Args:
            collection: Target collection
            new_embedding_model: Embedding model that will be used (optional)
            
        Returns:
            CompatibilityResult with analysis
        """
        
        logger.info(f"Validating compatibility for collection: {collection.collection_name}")
        
        # Check compatibility using the checker
        result = self.compatibility_checker.check_compatibility(
            collection=collection,
            new_embedding_model=new_embedding_model or self.config.embedding_model
        )
        
        if not result.is_compatible:
            logger.warning(f"Found compatibility issues for collection {collection.collection_name}")
            for issue in result.issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info(f"Collection {collection.collection_name} is compatible with new configuration")
        
        return result

    async def create_production_pipeline(
        self, 
        collection: VectorCollection, 
        db: AsyncSession
    ) -> IngestionPipeline:
        """Create LlamaIndex IngestionPipeline with proper storage backends."""
        
        logger.info(f"Creating production pipeline for collection: {collection.collection_name}")
        
        # Setup Qdrant configuration for this collection
        qdrant_config = QdrantConfig(
            url=getattr(collection, 'qdrant_url', None) or self.qdrant_config.url,
            api_key=self.qdrant_config.api_key,
            collection_name=collection.collection_name,
            vectors_config={
                "size": getattr(collection, 'vector_size', None) or self.qdrant_config.vectors_config["size"],
                "distance": getattr(collection, 'distance_metric', None) or self.qdrant_config.vectors_config["distance"]
            }
        )
        
        # Create storage context
        storage_context = await self._setup_storage_context(qdrant_config)
        
        # Setup transformations with proper attribute access
        chunk_size = getattr(collection, 'chunk_size', None) or self.config.chunk_size
        chunk_overlap = getattr(collection, 'chunk_overlap', None) or self.config.chunk_overlap
        
        transformations = [
            SentenceSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            ),
            Settings.embed_model  # This adds embeddings
        ]
        
        # Create IngestionPipeline with production settings
        pipeline = IngestionPipeline(
            transformations=transformations,
            vector_store=storage_context.vector_store,
            docstore=storage_context.docstore,
            docstore_strategy=DocstoreStrategy.UPSERTS,  # Smart processing!
            disable_cache=True  # Disable for production consistency
        )
        
        logger.info("Production pipeline created successfully")
        return pipeline

    async def process_s3_documents(
        self,
        collection_id: str,
        s3_keys: List[str],
        user_id: int,
        force_reprocess: bool = False,
        db: Optional[AsyncSession] = None
    ) -> ProcessingResult:
        """
        Process S3 documents using IngestionPipeline's smart deduplication.
        
        Args:
            collection_id: Vector collection ID
            s3_keys: List of S3 keys to process
            user_id: User ID for ownership
            force_reprocess: Force reprocessing even if documents exist
            db: Database session
            
        Returns:
            ProcessingResult with detailed metrics including compatibility analysis
        """
        
        if db is None:
            async for db_session in get_db():
                db = db_session
                break
        
        start_time = time.time()
        logger.info(f"Processing {len(s3_keys)} documents for collection {collection_id}")
        
        # Get collection
        result = await db.execute(select(VectorCollection).where(VectorCollection.id == collection_id))
        collection = result.scalar_one_or_none()
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")
        
        # Validate compatibility before processing
        compatibility_result = await self.validate_collection_compatibility(
            collection=collection,
            new_embedding_model=self.config.embedding_model
        )
        
        # If there are critical issues, fail fast
        if not compatibility_result.is_compatible and compatibility_result.needs_migration:
            logger.error(f"Critical compatibility issues found - cannot proceed with processing")
            return ProcessingResult(
                total_requested=len(s3_keys),
                processed_count=0,
                skipped_count=0,
                failed_count=len(s3_keys),
                processing_time=time.time() - start_time,
                processed_files=[],
                failed_files=[f"s3://{self.config.s3_bucket_name}/{key}" for key in s3_keys],
                collection_id=collection_id,
                compatibility_result=compatibility_result
            )
        
        # Load documents from S3
        documents = await self._load_s3_documents(s3_keys, collection.collection_name)
        logger.info(f"Loaded {len(documents)} documents from S3")
        
        # Create production pipeline
        pipeline = await self.create_production_pipeline(collection, db)
        
        # Process documents using IngestionPipeline
        # This automatically handles deduplication and smart processing!
        processed_nodes = await pipeline.arun(
            documents=documents,
            show_progress=self.config.show_progress,
            num_workers=self.config.num_workers
        )
        
        processing_time = time.time() - start_time
        
        # Update database state
        result = await self._update_database_state(
            documents, processed_nodes, collection, user_id, db
        )
        
        # Update collection statistics
        await self._update_collection_stats(collection, db)
        
        logger.info(f"Processing completed in {processing_time:.2f}s - {len(processed_nodes)} nodes created")
        
        return ProcessingResult(
            total_requested=len(s3_keys),
            processed_count=len([d for d in documents if d.id_ in [n.ref_doc_id for n in processed_nodes]]),
            skipped_count=len(documents) - len(processed_nodes),
            failed_count=0,  # IngestionPipeline handles failures gracefully
            processing_time=processing_time,
            processed_files=[d.metadata.get('s3_key', d.id_) for d in documents],
            failed_files=[],
            collection_id=collection_id,
            compatibility_result=compatibility_result
        )

    async def create_query_engine(self, collection_id: str, db: Optional[AsyncSession] = None):
        """Create query engine that connects to existing vectors (no reprocessing!)."""
        
        if db is None:
            async for db_session in get_db():
                db = db_session
                break
        
        # Get collection
        result = await db.execute(select(VectorCollection).where(VectorCollection.id == collection_id))
        collection = result.scalar_one_or_none()
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")
        
        logger.info(f"Creating query engine for collection: {collection.collection_name}")
        
        # Setup storage context to connect to existing vectors using config
        qdrant_config = QdrantConfig(
            url=getattr(collection, 'qdrant_url', None) or self.qdrant_config.url,
            api_key=self.qdrant_config.api_key,
            collection_name=collection.collection_name,
            vectors_config={
                "size": getattr(collection, 'vector_size', None) or self.qdrant_config.vectors_config["size"],
                "distance": getattr(collection, 'distance_metric', None) or self.qdrant_config.vectors_config["distance"]
            }
        )
        storage_context = await self._setup_storage_context(qdrant_config)
        
        # Create index that connects to existing vectors (no reprocessing!)
        index = VectorStoreIndex(
            nodes=[],  # Empty - we're connecting to existing
            storage_context=storage_context
        )
        
        # Create query engine with metadata filtering
        query_engine = index.as_query_engine(
            similarity_top_k=self.config.similarity_top_k,
            response_mode=self.config.response_mode,
            node_postprocessors=[self.metadata_cleaner]
        )
        
        logger.info("Query engine created successfully")
        return query_engine

    async def query_collection(
        self,
        collection_id: str,
        query: str,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> QueryResult:
        """Query a collection and return results with proper tracking."""
        
        if db is None:
            async for db_session in get_db():
                db = db_session
                break
        
        start_time = time.time()
        logger.info(f"Querying collection {collection_id}: {query}")
        
        # Create query engine
        query_engine = await self.create_query_engine(collection_id, db)
        
        # Execute query
        response = await query_engine.aquery(query)
        query_time = time.time() - start_time
        
        # Extract sources
        sources = []
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                sources.append({
                    "file_name": node.metadata.get('file_name', 'Unknown'),
                    "page_label": node.metadata.get('page_label', 'N/A'),
                    "score": getattr(node, 'score', 0.0),
                    "text_preview": node.text[:200] + "..." if len(node.text) > 200 else node.text
                })
        
        # Update collection query statistics
        await self._update_query_stats(collection_id, query_time, db)
        
        logger.info(f"Query completed in {query_time:.3f}s with {len(sources)} sources")
        
        return QueryResult(
            query=query,
            response=str(response),
            sources=sources,
            query_time=query_time,
            collection_id=collection_id,
            total_nodes_retrieved=len(sources)
        )

    # Private helper methods
    
    async def _setup_storage_context(self, qdrant_config: QdrantConfig) -> StorageContext:
        """Setup storage context with Qdrant vector store."""
        
        # Create Qdrant clients
        client = QdrantClient(url=qdrant_config.url)
        aclient = AsyncQdrantClient(url=qdrant_config.url)
        
        # Ensure collection exists
        await qdrant_config.ensure_collection_exists()
        
        # Create vector store
        vector_store = QdrantVectorStore(
            client=client,
            aclient=aclient,
            collection_name=qdrant_config.collection_name,
            enable_hybrid=False  # Disable for better performance
        )
        
        return StorageContext.from_defaults(vector_store=vector_store)

    async def _load_s3_documents(self, s3_keys: List[str], collection_name: str) -> List[Document]:
        """Load documents from S3 using existing infrastructure."""
        
        # Create S3 storage backend
        storage_backend = S3StorageBackend(bucket_name=self.config.s3_bucket_name)
        
        # Create S3 directory reader
        s3_reader = S3DirectoryReader(
            storage_backend=storage_backend,
            max_concurrent_downloads=self.config.max_concurrent_downloads
        )
        
        # Get file extractor from existing RAG service
        file_extractor = self._get_file_extractor()
        
        # Load documents
        documents = await s3_reader.load_documents_from_s3_keys(
            s3_keys=s3_keys,
            file_extractor=file_extractor,
            exclude_patterns=self.config.exclude_patterns,
            num_workers=self.config.num_workers,
            show_progress=self.config.show_progress,
            add_s3_metadata=True
        )
        
        return documents

    def _get_file_extractor(self) -> Dict[str, Any]:
        """Get file extractor using existing components."""
        from app.utils.CustomPptxReader import OpenAIPptxReader
        
        pptx_reader = OpenAIPptxReader(
            enable_logging=self.config.enable_logging,
            model_name=self.config.llm_model,
            enable_delay=self.config.enable_delay,
            delay_seconds=self.config.delay_seconds
        )
        
        return {
            ".pptx": pptx_reader,
            ".ppt": pptx_reader
        }

    async def _update_database_state(
        self,
        documents: List[Document],
        processed_nodes: List[BaseNode],
        collection: VectorCollection,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """Update database state to reflect processing results."""
        
        # Create mapping of doc_id to nodes
        node_map = {}
        for node in processed_nodes:
            ref_doc_id = getattr(node, 'ref_doc_id', None)
            if ref_doc_id:
                if ref_doc_id not in node_map:
                    node_map[ref_doc_id] = []
                node_map[ref_doc_id].append(node)
        
        # Update or create KnowledgeFile records
        for document in documents:
            s3_key = document.metadata.get('s3_key', document.id_)
            
            # Check if document was processed
            doc_nodes = node_map.get(document.id_, [])
            
            if doc_nodes:  # Document was processed
                # Check if KnowledgeFile exists
                result = await db.execute(
                    select(KnowledgeFile).where(
                        and_(
                            KnowledgeFile.user_id == user_id,
                            KnowledgeFile.file_path == s3_key
                        )
                    )
                )
                knowledge_file = result.scalar_one_or_none()
                
                if knowledge_file:
                    # Update existing using proper SQLAlchemy update
                    await db.execute(
                        update(KnowledgeFile)
                        .where(KnowledgeFile.id == knowledge_file.id)
                        .values(
                            processing_status="completed",
                            indexed_in_vector_db=True,
                            embeddings_generated=True,
                            node_count=len(doc_nodes),
                            collection_id=collection.collection_name,
                            ref_doc_id=document.id_,
                            document_hash=document.hash,
                            processed_at=datetime.now(timezone.utc)
                        )
                    )
                else:
                    # Create new
                    knowledge_file = KnowledgeFile(
                        id=f"kf_{uuid.uuid4().hex[:12]}",
                        user_id=user_id,
                        file_id=f"file_{uuid.uuid4().hex[:8]}",
                        file_path=s3_key,
                        file_name=document.metadata.get('file_name', 'Unknown'),
                        file_size=document.metadata.get('file_size', 0),
                        content_type=document.metadata.get('content_type', 'application/octet-stream'),
                        ref_doc_id=document.id_,
                        document_hash=document.hash,
                        node_count=len(doc_nodes),
                        collection_id=collection.collection_name,
                        processing_status="completed",
                        indexed_in_vector_db=True,
                        embeddings_generated=True,
                        processed_at=datetime.now(timezone.utc)
                    )
                    db.add(knowledge_file)
        
        await db.commit()
        return True

    async def _update_collection_stats(self, collection: VectorCollection, db: AsyncSession):
        """Update collection statistics."""
        
        # Count knowledge files in this collection
        result = await db.execute(
            select(func.count(KnowledgeFile.id)).where(
                and_(
                    KnowledgeFile.collection_id == collection.collection_name,
                    KnowledgeFile.indexed_in_vector_db == True
                )
            )
        )
        total_documents = result.scalar() or 0
        
        # Count total nodes
        result = await db.execute(
            select(func.sum(KnowledgeFile.node_count)).where(
                and_(
                    KnowledgeFile.collection_id == collection.collection_name,
                    KnowledgeFile.indexed_in_vector_db == True
                )
            )
        )
        total_nodes = result.scalar() or 0
        
        # Update collection using proper SQLAlchemy update
        await db.execute(
            update(VectorCollection)
            .where(VectorCollection.id == collection.id)
            .values(
                total_documents=total_documents,
                total_nodes=total_nodes,
                total_vectors=total_nodes,  # Assuming 1 vector per node
                last_sync=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        )
        
        await db.commit()

    async def _update_query_stats(self, collection_id: str, query_time: float, db: AsyncSession):
        """Update collection query statistics."""
        
        result = await db.execute(select(VectorCollection).where(VectorCollection.id == collection_id))
        collection = result.scalar_one_or_none()
        
        if collection:
            # Update query statistics using proper getattr access
            current_queries = getattr(collection, 'total_queries', 0) or 0
            current_avg = getattr(collection, 'avg_query_time', 0.0) or 0.0
            
            new_total = current_queries + 1
            new_avg = ((current_avg * current_queries) + query_time) / new_total
            
            # Update using proper SQLAlchemy update
            await db.execute(
                update(VectorCollection)
                .where(VectorCollection.id == collection_id)
                .values(
                    total_queries=new_total,
                    avg_query_time=new_avg,
                    last_query_time=datetime.now(timezone.utc)
                )
            )
            
            await db.commit() 