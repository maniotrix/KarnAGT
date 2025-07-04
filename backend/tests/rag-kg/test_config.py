#!/usr/bin/env python3

"""Test script to validate QdrantConfig implementation."""

import os

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

test_collection_name = "test_collection"

def test_config_import():
    """Test basic imports."""
    try:
        from app.services.knowledge.config import QdrantConfig, RAGConfig
        print("✅ Config classes imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import config classes: {e}")
        return False

def test_instance_methods():
    """Test instance methods."""
    try:
        from app.services.knowledge.config import QdrantConfig
        
        # Create config with defaults
        config = QdrantConfig(url="http://localhost:6333", collection_name=test_collection_name)
        
        # Test instance methods
        client_kwargs = config.get_client_kwargs()
        print(f"✅ get_client_kwargs(): {client_kwargs}")
        
        collection_config = config.get_collection_config()
        print(f"✅ get_collection_config(): keys={list(collection_config.keys())}")
        
        upload_config = config.get_upload_config()
        print(f"✅ get_upload_config(): {upload_config}")
        
        config_dict = config.to_dict()
        print(f"✅ to_dict(): {len(config_dict)} fields")
        
        return True
    except Exception as e:
        print(f"❌ Instance methods failed: {e}")
        return False

def test_class_methods():
    """Test class methods (factory methods)."""
    try:
        from app.services.knowledge.config import QdrantConfig
        
        # Test factory methods
        prod_config = QdrantConfig.for_production(
            "https://example.qdrant.cloud:6333", 
            "test-api-key"
        )
        print(f"✅ for_production(): {prod_config.connection_summary}")
        
        dev_config = QdrantConfig.for_local_development()
        print(f"✅ for_local_development(): {dev_config.connection_summary}")
        
        test_config = QdrantConfig.for_testing()
        print(f"✅ for_testing(): {test_config.connection_summary}")
        
        env_config = QdrantConfig.from_env()
        print(f"✅ from_env(): {env_config.connection_summary}")
        
        custom_config = QdrantConfig.with_custom_vectors(384, "Euclidean")
        print(f"✅ with_custom_vectors(): {custom_config.vectors_config}")
        
        return True
    except Exception as e:
        print(f"❌ Class methods failed: {e}")
        return False

def test_static_methods():
    """Test static methods."""
    try:
        from app.services.knowledge.config import QdrantConfig
        
        # Test static methods
        is_valid = QdrantConfig.validate_url("http://localhost:6333")
        print(f"✅ validate_url(): {is_valid}")
        
        ports = QdrantConfig.get_default_ports()
        print(f"✅ get_default_ports(): {ports}")
        
        distances = QdrantConfig.get_supported_distances()
        print(f"✅ get_supported_distances(): {distances}")
        
        vector_size = QdrantConfig.get_vector_size_for_model("text-embedding-ada-002")
        print(f"✅ get_vector_size_for_model(): {vector_size}")
        
        memory_usage = QdrantConfig.estimate_memory_usage(10000, 1536)
        print(f"✅ estimate_memory_usage(): {memory_usage}")
        
        return True
    except Exception as e:
        print(f"❌ Static methods failed: {e}")
        return False

def test_properties():
    """Test properties."""
    try:
        from app.services.knowledge.config import QdrantConfig

        # Local config
        local_config = QdrantConfig(url="http://localhost:6333", collection_name=test_collection_name)
        print(f"✅ is_local_config: {local_config.is_local_config}")
        print(f"✅ is_cloud_config: {local_config.is_cloud_config}")
        print(f"✅ connection_summary: {local_config.connection_summary}")
        print(f"✅ estimated_performance_tier: {local_config.estimated_performance_tier}")
        print(f"✅ memory_optimization_enabled: {local_config.memory_optimization_enabled}")
        
        # Cloud config
        cloud_config = QdrantConfig(
            url="https://cloud.qdrant.io:6333", 
            api_key="test-key",
            collection_name=test_collection_name
        )
        print(f"✅ Cloud config summary: {cloud_config.connection_summary}")
        
        return True
    except Exception as e:
        print(f"❌ Properties failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing QdrantConfig Implementation\n")
    
    tests = [
        ("Import Test", test_config_import),
        ("Instance Methods", test_instance_methods),
        ("Class Methods", test_class_methods),
        ("Static Methods", test_static_methods),
        ("Properties", test_properties),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))
        print()
    
    # Summary
    print("🎯 Test Summary:")
    print("=" * 50)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! QdrantConfig is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 