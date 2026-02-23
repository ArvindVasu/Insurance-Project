import uuid
from services.Common_Functions import generate_title
from datetime import datetime


def parse_output(user_prompt:str,output):
    return {
            "id": str(uuid.uuid4()),
            "prompt": user_prompt,
            "title": generate_title(user_prompt),
            "route": output.get("route"),

            # Results
            "result": output.get("sql_result") if output.get("route") in ["sql", "document", "comp"] else output.get("web_links"),
            "sql_query": output.get("sql_query"),

            # External search
            "web_links": output.get("web_links"),

            # Summaries / visualization
            "general_summary": output.get("general_summary"),
            "comparison_summary": output.get("comparison_summary"),
            "chart_info": output.get("chart_info"),

            # FAISS Knowledge base
            "faiss_summary": output.get("faiss_summary"),
            "faiss_sources": output.get("faiss_sources"),
            "faiss_images": output.get("faiss_images"),

            # Intranet 
            "intranet_summary": output.get("intranet_summary"),
            "intranet_sources": output.get("intranet_sources"),
            "intranet_doc_links": output.get("intranet_doc_links"),
            "intranet_doc_count": output.get("intranet_doc_count"),

            "uploaded_file1": output.get("variance_commentary"),
            "uploaded_file1_path": output.get("variance_commentary"),
            "uploaded_file1_is_excel": output.get("variance_commentary"),
            "uploaded_file1_is_docx": output.get("variance_commentary"),

            # any additional custom fields the nodes may emit
            "extra": output.get("extra", {}),

            # Meta
            "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p")
        }