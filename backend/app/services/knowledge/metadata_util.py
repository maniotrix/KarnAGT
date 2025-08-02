import logging
from typing import List, Optional
import asyncio

# Add imports for the metadata cleaner
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.bridge.pydantic import Field, ConfigDict


# Setup logging
logger = logging.getLogger(__name__)


class MetadataCleanerPostprocessor(BaseNodePostprocessor):
    """
    Remove sensitive metadata before sending to LLM while preserving it for application use.
    
    This prevents sensitive information like file paths, S3 keys, and bucket names 
    from being exposed in the LLM context while keeping them available for citations
    and application logic.
    
    This postprocessor follows LlamaIndex conventions and best practices.
    """
    
    # LlamaIndex best practice: Proper model configuration
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # LlamaIndex best practice: Declare fields with proper types
    keep_keys: List[str] = Field(
        default_factory=lambda: [
            'file_name',           # Original filename for citations
            's3_original_filename', # Original filename from S3 metadata
            'page_label',          # Page numbers for citations
            'doc_id',              # Document ID for query filtering and response processing
            'ref_doc_id',          # Reference document ID (backup for doc_id)
            'Header 1', 'Header 2', 'Header 3',  # Document structure
            'questions_this_excerpt_can_answer',  # Generated Q&A metadata
            'section_summary', 'prev_section_summary', 'next_section_summary'  # Generated summaries
        ],
        description="List of metadata keys to preserve for LLM context (safe keys only)"
    )
    
    store_original: bool = Field(
        default=True,
        description="Whether to store original metadata in extra_info for application use"
    )
    
    remove_keys: List[str] = Field(
        default_factory=lambda: [
            'file_path',          # Local file paths with usernames
            's3_key',             # S3 object keys  
            's3_bucket',          # S3 bucket names
            'source_type',        # Internal source tracking
            'original_text',      # Duplicate content that wastes tokens
            'window'             # Large context windows that waste tokens
        ],
        description="List of metadata keys to explicitly remove (sensitive information)"
    )
    
    def __init__(self, keep_keys: List[str] = None, store_original: bool = True, **kwargs):
        """
        Initialize the metadata cleaner.
        
        Args:
            keep_keys: List of metadata keys to keep for LLM context (safe keys only)
            store_original: Whether to store original metadata in extra_info for app use
            **kwargs: Additional arguments passed to BaseNodePostprocessor
        """
        # Set custom values if provided
        if keep_keys is not None:
            kwargs['keep_keys'] = keep_keys
        kwargs['store_original'] = store_original
        
        # Initialize parent class
        super().__init__(**kwargs)
        
        logger.info(f"MetadataCleanerPostprocessor initialized with {len(self.keep_keys)} safe keys")
    
    # LlamaIndex best practice: Override class_name for better identification
    @classmethod
    def class_name(cls) -> str:
        return "MetadataCleanerPostprocessor"
    
    def _postprocess_nodes(
        self, 
        nodes: List[NodeWithScore], 
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """
        Clean metadata from nodes before they're sent to LLM.
        
        Args:
            nodes: List of nodes with scores from retrieval
            query_bundle: Optional query information
            
        Returns:
            List of nodes with cleaned metadata
        """
        if not nodes:
            logger.debug("No nodes to process")
            return nodes
            
        logger.debug(f"Cleaning metadata for {len(nodes)} nodes")
        
        # LlamaIndex best practice: Use callback manager for tracing
        with self.callback_manager.event(
            "metadata_cleaning",
            payload={"num_nodes": len(nodes)}
        ) as event:
            
            processed_nodes = []
            cleaned_keys_count = 0
            
            for node_with_score in nodes:
                try:
                    # Validate node structure
                    if not hasattr(node_with_score, 'node') or not hasattr(node_with_score.node, 'metadata'):
                        logger.warning(f"Skipping malformed node: {type(node_with_score)}")
                        processed_nodes.append(node_with_score)
                        continue
                    
                    # Keep original metadata for application use if requested
                    if self.store_original:
                        original_metadata = node_with_score.node.metadata.copy()
                        node_with_score.node.extra_info = original_metadata
                    
                    # Create clean metadata for LLM context
                    clean_metadata = {}
                    original_key_count = len(node_with_score.node.metadata)
                    
                    for key, value in node_with_score.node.metadata.items():
                        # Keep safe keys
                        if key in self.keep_keys:
                            clean_metadata[key] = value
                        # Explicitly remove sensitive keys
                        elif key in self.remove_keys:
                            logger.debug(f"Removed sensitive metadata key: {key}")
                            cleaned_keys_count += 1
                            continue
                        # For unknown keys, be conservative and remove them
                        else:
                            logger.debug(f"Removed unknown metadata key: {key}")
                            cleaned_keys_count += 1
                            continue
                    
                    # Update node metadata (this is what gets sent to LLM)
                    node_with_score.node.metadata = clean_metadata
                    
                    # Ensure we have at least the filename for citations
                    if 'file_name' not in clean_metadata and 's3_original_filename' in clean_metadata:
                        clean_metadata['file_name'] = clean_metadata['s3_original_filename']
                    elif 'file_name' not in clean_metadata:
                        clean_metadata['file_name'] = 'document'
                    
                    processed_nodes.append(node_with_score)
                    
                except Exception as e:
                    logger.error(f"Error processing node metadata: {e}")
                    # Return original node on error
                    processed_nodes.append(node_with_score)
            
            # Update event with results
            event.on_end(payload={
                "cleaned_keys_count": cleaned_keys_count,
                "processed_nodes": len(processed_nodes)
            })
        
        logger.debug(f"Metadata cleaning completed - removed {cleaned_keys_count} sensitive keys from {len(processed_nodes)} nodes")
        return processed_nodes
    
    # LlamaIndex best practice: Provide async implementation for better performance
    async def _apostprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """
        Async version of metadata cleaning.
        
        For CPU-bound operations like metadata cleaning, we use asyncio.to_thread
        to avoid blocking the event loop.
        """
        if not nodes:
            return nodes
            
        # For small numbers of nodes, run synchronously
        if len(nodes) < 10:
            return self._postprocess_nodes(nodes, query_bundle)
        
        # For larger numbers, run in thread pool to avoid blocking
        return await asyncio.to_thread(self._postprocess_nodes, nodes, query_bundle)
    
    def get_safe_metadata_keys(self) -> List[str]:
        """
        Get the list of metadata keys that are considered safe for LLM context.
        
        Returns:
            List of safe metadata keys
        """
        return self.keep_keys.copy()
    
    def add_safe_key(self, key: str) -> None:
        """
        Add a new key to the list of safe metadata keys.
        
        Args:
            key: Metadata key to consider safe for LLM context
        """
        if key not in self.keep_keys:
            self.keep_keys.append(key)
            logger.info(f"Added safe metadata key: {key}")
    
    def remove_safe_key(self, key: str) -> None:
        """
        Remove a key from the list of safe metadata keys.
        
        Args:
            key: Metadata key to remove from safe list
        """
        if key in self.keep_keys:
            self.keep_keys.remove(key)
            logger.info(f"Removed safe metadata key: {key}")
    
    def get_sensitive_keys(self) -> List[str]:
        """
        Get the list of metadata keys that are considered sensitive.
        
        Returns:
            List of sensitive metadata keys that will be removed
        """
        return self.remove_keys.copy() 