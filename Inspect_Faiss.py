from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

# === CONFIG ===
FAISS_DIR = "faiss_index2/"

# Load FAISS index
embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
faiss_index = FAISS.load_local(FAISS_DIR, embedding, allow_dangerous_deserialization=True)

# Retrieve sample documents
retrieved_docs = faiss_index.similarity_search("sample", k=10)  # k = number of docs to return

print(f"\n📦 Total documents returned: {len(retrieved_docs)}\n")

# Display the retrieved docs
for i, doc in enumerate(retrieved_docs, 1):
    print(f"--- Document {i} ---")
    print(f"Metadata: {doc.metadata}")
    print(f"Content: {doc.page_content[:500]}...\n")