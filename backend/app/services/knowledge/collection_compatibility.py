"""
Collection Compatibility Checker for Production RAG Service.

This module handles vector dimension and distance metric compatibility
when adding new documents to existing collections.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.services.knowledge.config import QdrantConfig, RAGConfig
from app.models.database import VectorCollection

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityResult:
    """Result of collection compatibility check."""
    is_compatible: bool
    issues: list[str]
    suggested_action: str
    needs_migration: bool = False
    migration_strategy: Optional[str] = None


class CollectionCompatibilityChecker:
    """
    Checks if new documents can be added to existing collections
    based on vector dimensions and distance metrics.
    """
    
    def __init__(self, rag_config: RAGConfig):
        self.config = rag_config
        
    def check_compatibility(
        self, 
        collection: VectorCollection, 
        new_embedding_model: Optional[str] = None
    ) -> CompatibilityResult:
        """
        Check if new documents with current config can be added to existing collection.
        
        Args:
            collection: Existing vector collection
            new_embedding_model: Override embedding model to check
            
        Returns:
            CompatibilityResult with detailed analysis
        """
        
        embedding_model = new_embedding_model or self.config.embedding_model
        
        # Get expected vector dimensions for new model
        expected_vector_size = QdrantConfig.get_vector_size_for_model(embedding_model)
        
        # Get collection's current configuration
        collection_vector_size = getattr(collection, 'vector_size', None)
        collection_distance = getattr(collection, 'distance_metric', None)
        collection_embedding_model = getattr(collection, 'embedding_model', None)
        
        issues = []
        needs_migration = False
        migration_strategy = None
        
        # Check vector dimension compatibility
        if collection_vector_size and collection_vector_size != expected_vector_size:
            issues.append(
                f"Vector dimension mismatch: collection expects {collection_vector_size} "
                f"but new model '{embedding_model}' produces {expected_vector_size}"
            )
            needs_migration = True
            migration_strategy = "recreate_collection"
        
        # Check embedding model compatibility
        if (collection_embedding_model and 
            collection_embedding_model != embedding_model):
            issues.append(
                f"Embedding model changed: collection uses '{collection_embedding_model}' "
                f"but new config uses '{embedding_model}'"
            )
            
            # Only require migration if dimensions are different
            if not needs_migration:
                # Same dimensions but different model - could be compatible
                logger.warning(
                    f"Embedding model changed but dimensions match. "
                    f"Vectors may not be semantically compatible."
                )
        
        # Determine compatibility and suggested action
        is_compatible = len(issues) == 0
        
        if is_compatible:
            suggested_action = "proceed"
        elif needs_migration:
            suggested_action = "migrate_collection"
        else:
            suggested_action = "create_new_collection"
        
        return CompatibilityResult(
            is_compatible=is_compatible,
            issues=issues,
            suggested_action=suggested_action,
            needs_migration=needs_migration,
            migration_strategy=migration_strategy
        )
    
    def get_migration_plan(
        self, 
        collection: VectorCollection,
        target_embedding_model: str
    ) -> Dict[str, Any]:
        """
        Generate a migration plan for incompatible collections.
        
        Args:
            collection: Existing collection to migrate
            target_embedding_model: Target embedding model
            
        Returns:
            Dict with migration plan details
        """
        
        current_size = getattr(collection, 'vector_size', None)
        target_size = QdrantConfig.get_vector_size_for_model(target_embedding_model)
        
        return {
            "migration_type": "full_reindex",
            "reason": f"Vector dimension change: {current_size} → {target_size}",
            "steps": [
                "1. Create new collection with target configuration",
                "2. Reprocess all documents with new embedding model", 
                "3. Verify new collection works correctly",
                "4. Update collection references in database",
                "5. Delete old collection"
            ],
            "estimated_time": f"~{self._estimate_migration_time(collection)} minutes",
            "cost_impact": "High - all documents will be re-embedded",
            "data_loss_risk": "None - original documents preserved"
        }
    
    def _estimate_migration_time(self, collection: VectorCollection) -> int:
        """Estimate migration time based on collection size."""
        total_docs = getattr(collection, 'total_documents', 0) or 0
        
        # Rough estimate: 30 seconds per 10 documents
        estimated_minutes = max(1, (total_docs * 3) // 60)
        return estimated_minutes


def check_collection_compatibility(
    collection: VectorCollection,
    rag_config: RAGConfig,
    new_embedding_model: Optional[str] = None
) -> CompatibilityResult:
    """
    Convenience function to check collection compatibility.
    
    Args:
        collection: Existing collection
        rag_config: RAG configuration  
        new_embedding_model: Optional override for embedding model
        
    Returns:
        CompatibilityResult
    """
    checker = CollectionCompatibilityChecker(rag_config)
    return checker.check_compatibility(collection, new_embedding_model)


def suggest_collection_strategy(
    user_id: int,
    rag_config: RAGConfig,
    existing_collections: list[VectorCollection]
) -> Dict[str, Any]:
    """
    Suggest the best strategy when user has existing collections
    but wants to use a new configuration.
    
    Args:
        user_id: User ID
        rag_config: New RAG configuration
        existing_collections: User's existing collections
        
    Returns:
        Dict with strategy recommendation
    """
    
    if not existing_collections:
        return {
            "strategy": "create_new",
            "reason": "No existing collections"
        }
    
    checker = CollectionCompatibilityChecker(rag_config)
    
    # Check compatibility with existing collections
    compatible_collections = []
    incompatible_collections = []
    
    for collection in existing_collections:
        result = checker.check_compatibility(collection)
        if result.is_compatible:
            compatible_collections.append(collection)
        else:
            incompatible_collections.append((collection, result))
    
    if compatible_collections:
        # Use existing compatible collection
        best_collection = max(
            compatible_collections, 
            key=lambda c: getattr(c, 'total_documents', 0) or 0
        )
        return {
            "strategy": "use_existing",
            "collection": best_collection,
            "reason": f"Found compatible collection: {best_collection.collection_name}"
        }
    
    elif len(incompatible_collections) == 1:
        # Suggest migration of single collection
        collection, compatibility_result = incompatible_collections[0]
        return {
            "strategy": "migrate_existing", 
            "collection": collection,
            "compatibility_result": compatibility_result,
            "reason": "Single incompatible collection - migration recommended"
        }
    
    else:
        # Multiple incompatible collections - create new
        return {
            "strategy": "create_new_separate",
            "incompatible_collections": incompatible_collections,
            "reason": f"Multiple incompatible collections ({len(incompatible_collections)})"
        } 