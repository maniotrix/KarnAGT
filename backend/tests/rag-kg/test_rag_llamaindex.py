from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("🧪 Testing LlamaIndex RAG with in-memory vector store...")

# Create sample documents using LlamaIndex Document objects
docs = [
    Document(text="Paris is the capital of France. It is known for the Eiffel Tower and beautiful architecture."),
    Document(text="London is the capital of the United Kingdom. It has Big Ben and the Tower Bridge."),
    Document(text="Tokyo is the capital of Japan. It is a modern city with advanced technology."),
    Document(text="Berlin is the capital of Germany. It has rich history and the Brandenburg Gate."),
]

print("📝 Creating in-memory vector store with documents...")

# Configure LlamaIndex settings globally (best practice)
Settings.llm = OpenAI(model="gpt-4o-mini-2024-07-18")
Settings.embed_model = OpenAIEmbedding()

# Create node parser for better chunking control
node_parser = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50
)

# Create vector store index - this handles embedding and storage automatically
index = VectorStoreIndex.from_documents(
    documents=docs,
    transformations=[node_parser],  # Apply chunking transformation
    show_progress=True
)

print("✅ Vector store created and documents indexed!")
print("🔍 Creating RAG query engine...")

# Create query engine with retrieval settings
query_engine = index.as_query_engine(
    similarity_top_k=3,  # Retrieve top 3 most similar chunks
    response_mode="tree_summarize",  # Use tree summarization for better responses
    verbose=True
)

print("✅ RAG query engine created!")
print("❓ Asking: 'What is the capital of France?'")

# Query the engine
response = query_engine.query("What is the capital of France?")

print(f"\n🤖 Answer: {response}")

# Get source information (similar to LangChain's source_documents)
if hasattr(response, 'source_nodes') and response.source_nodes:
    print(f"📚 Sources: {[node.text[:50] + '...' for node in response.source_nodes]}")
else:
    print("📚 Sources: Retrieved from indexed documents")

print(f"\n🎉 LlamaIndex RAG test completed successfully!")
print(f"📊 Benefits over LangChain implementation:")
print(f"   - Automatic chunking with SentenceSplitter")
print(f"   - Global Settings configuration")
print(f"   - Built-in tree summarization")
print(f"   - Integrated document parsing")
print(f"   - Native source tracking") 