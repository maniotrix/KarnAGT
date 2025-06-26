from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain.chains import RetrievalQA
from langchain.schema import Document
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("🧪 Testing LangChain RAG with in-memory Qdrant...")

# Create sample documents
docs = [
    Document(page_content="Paris is the capital of France. It is known for the Eiffel Tower and beautiful architecture."),
    Document(page_content="London is the capital of the United Kingdom. It has Big Ben and the Tower Bridge."),
    Document(page_content="Tokyo is the capital of Japan. It is a modern city with advanced technology."),
    Document(page_content="Berlin is the capital of Germany. It has rich history and the Brandenburg Gate."),
]

print("📝 Creating in-memory vector store with documents...")

# Initialize components - USING from_documents (handles collection creation!)
embeddings = OpenAIEmbeddings()
vectorstore = QdrantVectorStore.from_documents(
    documents=docs,
    embedding=embeddings,
    location=":memory:",  # In-memory only!
    collection_name="test_collection"
)

print("✅ Vector store created and documents added!")
print("🔍 Creating RAG chain...")

# Create RAG chain (1 line vs your entire rag_tool function!)
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    retriever=vectorstore.as_retriever(),
    return_source_documents=True
)

print("✅ RAG chain created!")
print("❓ Asking: 'What is the capital of France?'")

# Query (1 line vs your complex agent setup!) - Using modern invoke method
result = qa_chain.invoke({"query": "What is the capital of France?"})

print(f"\n🤖 Answer: {result['result']}")
print(f"📚 Sources: {[doc.page_content[:50] + '...' for doc in result['source_documents']]}")
print(f"\n🎉 LangChain RAG test completed successfully!")
print(f"📊 Total lines of code: ~35 vs your original ~193 lines!") 