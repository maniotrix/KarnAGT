from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
import os
from dotenv import load_dotenv

# Uncomment the vector store you want to use:

# Option 1: Qdrant (in-memory mode)
from qdrant_client import QdrantClient

# Option 2: Chroma (in-memory)
# import chromadb

# Option 3: Chroma (persistent)
# import chromadb

load_dotenv()

print("🧪 Testing LlamaIndex RAG with different vector databases...")

# Configure LlamaIndex settings globally
Settings.llm = OpenAI(model="gpt-4o-mini-2024-07-18")
Settings.embed_model = OpenAIEmbedding()

# Create sample documents
docs = [
    Document(text="Paris is the capital of France. It is known for the Eiffel Tower and beautiful architecture."),
    Document(text="London is the capital of the United Kingdom. It has Big Ben and the Tower Bridge."),
    Document(text="Tokyo is the capital of Japan. It is a modern city with advanced technology."),
    Document(text="Berlin is the capital of Germany. It has rich history and the Brandenburg Gate."),
]

# Create node parser
node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# ==========================================
# CHOOSE YOUR VECTOR DATABASE:
# ==========================================

# Option 1: In-Memory (SimpleVectorStore) - DEFAULT
# print("📝 Using SimpleVectorStore (in-memory)...")
# vector_store = SimpleVectorStore()
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Option 2: Qdrant In-Memory (DEFAULT - No external server needed!)
print("📝 Using Qdrant (in-memory mode)...")
client = QdrantClient(":memory:")  # In-memory mode - no server needed!
vector_store = QdrantVectorStore(client=client, collection_name="test_collection")
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Option 3: Chroma In-Memory (Uncomment to use)
# print("📝 Using ChromaVectorStore (in-memory)...")
# chroma_client = chromadb.EphemeralClient()
# chroma_collection = chroma_client.create_collection("llamaindex_test")
# vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Option 4: Chroma Persistent (Uncomment to use)
# print("📝 Using ChromaVectorStore (persistent)...")
# chroma_client = chromadb.PersistentClient(path="./chroma_db")
# chroma_collection = chroma_client.get_or_create_collection("llamaindex_test")
# vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create the index with your chosen vector store
index = VectorStoreIndex.from_documents(
    documents=docs,
    storage_context=storage_context,
    transformations=[node_parser],
    show_progress=True
)

print("✅ Vector store created and documents indexed!")
print("🔍 Creating RAG query engine...")

# Create query engine
query_engine = index.as_query_engine(
    similarity_top_k=3,
    response_mode="tree_summarize",
    verbose=True
)

print("✅ RAG query engine created!")
print("❓ Asking: 'What is the capital of France?'")

# Query the engine
response = query_engine.query("What is the capital of France?")

print(f"\n🤖 Answer: {response}")

# Get source information
if hasattr(response, 'source_nodes') and response.source_nodes:
    print(f"📚 Sources: {[node.text[:50] + '...' for node in response.source_nodes]}")

print(f"\n🎉 LlamaIndex RAG test completed!")
print(f"💾 Vector Store Used: {type(vector_store).__name__}")
print(f"🔧 To use different vector stores, uncomment the relevant section above")

# Additional vector databases LlamaIndex supports:
print(f"\n📋 LlamaIndex supports these vector databases:")
print(f"   - Qdrant (production-ready)")
print(f"   - Chroma (good for prototyping)")
print(f"   - Pinecone (cloud-based)")
print(f"   - Weaviate (semantic search)")
print(f"   - Milvus (scalable)")
print(f"   - Faiss (Facebook AI)")
print(f"   - SimpleVectorStore (in-memory)")
print(f"   - And 20+ more!") 