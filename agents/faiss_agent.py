
from services.Graph_state import GraphState
from services.llm_service import call_llm
from services.Common_Functions import prune_state
import os
from dotenv import load_dotenv
import json
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings


load_dotenv()

STATE_KEYS_SET_AT_ENTRY = []

embedding = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
faiss_index = FAISS.load_local("faiss_index", embedding, allow_dangerous_deserialization=True)

# faissdb node to extract internal docs
def faissdb_node(state: GraphState) -> GraphState:
    faiss = FAISS.load_local(
        folder_path="faiss_index/",
        embeddings=OpenAIEmbeddings(),
        allow_dangerous_deserialization=True
    )
    docs = faiss_index.similarity_search(state["user_prompt"], k=3)

    top_docs = docs[:3]  # ⬅️ Top 3 instead of 5
    content_snippets = "\n\n---\n\n".join(d.page_content[:500] for d in top_docs)

    summary_prompt = f"""
    Based on the following retrieved document chunks from internal knowledge base, answer the user's query:

    User Prompt: {state['user_prompt']}

    Documents:
    {content_snippets}

    Provide a concise and structured answer with key points or numeric details if found.
    """
    summary = call_llm(summary_prompt)

    # Extract faiss_sources with source path
    faiss_sources = []
    all_images = []

    for doc in top_docs:
        doc_name = doc.metadata.get("source_doc", "Doc")
        snippet = doc.page_content[:300]
        path = doc.metadata.get("file_path")  # must be present in ingestion step
        #print(f"[DEBUG] FAISS doc metadata: {doc.metadata}")
        faiss_sources.append((doc_name, snippet, path))

        # Load associated images
        image_meta_path = os.path.join("extracted_images", "extracted_image_metadata.json")
        if os.path.exists(image_meta_path):
            with open(image_meta_path, 'r') as f:
                all_metadata = json.load(f)
            related_images = [
                meta for meta in all_metadata
                if meta["original_doc"] == doc_name
            ]
            all_images.extend(related_images)

    return {
        **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
        "faiss_summary": summary,
        "faiss_sources": faiss_sources,
        "faiss_images": all_images
    }