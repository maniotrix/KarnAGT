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


current_dir = os.path.dirname(os.path.abspath(__file__))

backend_dir = os.path.dirname(os.path.dirname(current_dir))
test_docs_dir = os.path.join(backend_dir, "test_docs")


# Configure LlamaIndex settings globally
Settings.llm = OpenAI(model="gpt-4o-mini-2024-07-18")
Settings.embed_model = OpenAIEmbedding()

# Load real documents from test_docs folder
print("📁 Loading documents from test_docs folder...")
from llama_index.core import SimpleDirectoryReader

# Load documents from the test_docs folder
docs = SimpleDirectoryReader(test_docs_dir).load_data()
print(f"✅ Loaded {len(docs)} documents from test_docs folder")

# Print document info
for i, doc in enumerate(docs[:3]):  # Show first 3 documents
    print(f"   📄 Document {i+1}: {doc.metadata.get('file_name', 'Unknown')} ({len(doc.text)} chars)")
if len(docs) > 3:
    print(f"   📄 ... and {len(docs) - 3} more documents")

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

# Try multiple queries relevant to your documents
queries = [
    "What is Trykaa and what does the company do?",
    "Tell me about AI agents and their capabilities",
    "What are the key features of distributed systems?",
    "How do human cells compare to AI agents?"
]

print(f"\n🔍 Testing {len(queries)} queries on your real documents...")

for i, query in enumerate(queries, 1):
    print(f"\n❓ Query {i}: '{query}'")
    response = query_engine.query(query)
    print(f"🤖 Answer: {response}")
    
    # Show sources for ALL queries
    if hasattr(response, 'source_nodes') and response.source_nodes:
        print(f"📚 Sources ({len(response.source_nodes)} found):")
        for j, node in enumerate(response.source_nodes[:3], 1):  # Show top 3 sources
            source_file = node.metadata.get('file_name', 'Unknown')
            source_text = node.text[:100].replace('\n', ' ') + '...'
            print(f"   {j}. {source_file}: {source_text}")
    else:
        print("📚 No sources found")
    
    print("-" * 80)

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