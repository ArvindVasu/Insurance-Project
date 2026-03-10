


from services.Common_Functions import _format_dataframe_for_display


import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from langchain_core.runnables import Runnable
from serpapi import GoogleSearch
from vanna.remote import VannaDefault
from docx import Document
import tempfile
import os
from dotenv import load_dotenv
import json
import re
from openai import OpenAI
import pandas as pd
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
from datetime import datetime
import json
from datetime import date, timedelta
from pptx import Presentation
from pptx.util import Inches, Pt
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
import tempfile
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.table import Table as DocxTable
import tempfile
import uuid
from docx.table import Table as DocxTable
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import numpy as np
from pathlib import Path
from io import BytesIO
import base64
from time import sleep
from urllib.parse import urlparse
import io
import re
from difflib import get_close_matches
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
import math
import logging

load_dotenv()


def _with_one_based_index(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if not isinstance(df, pd.DataFrame):
        return df
    display_df = df.copy()
    display_df.index = range(1, len(display_df) + 1)
    return display_df

def _render_intranet_block(obj):
        st.markdown("---")
        
        # Header with icon and status
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.subheader("Policy Document Analysis")
        with col2:
            if obj.get("intranet_doc_count"):
                st.metric("Documents", obj["intranet_doc_count"])
        
        # Main analysis content
        if obj.get("intranet_summary"):
            st.markdown(obj["intranet_summary"])
        else:
            st.warning("No analysis summary available")
        
        st.markdown("---")
        
        # Sources section with expandable details
        if obj.get("intranet_sources"):
            st.subheader("Sources Referenced")
            
            for idx, src in enumerate(obj["intranet_sources"], 1):
                if isinstance(src, (list, tuple)) and len(src) >= 2:
                    fname, link = src[0], src[1]
                    
                    # Create expandable section for each source
                    with st.expander(f"Source {idx}: {fname}", expanded=(idx == 1)):
                        if link:
                            st.markdown(f"**Document:** [{fname}]({link})")
                            st.markdown(f"**Link:** [Open in Google Drive]({link})")
                            
                            # Add a direct button
                            st.link_button("View Document", link, use_container_width=True)
                        else:
                            st.markdown(f"**Document:** {fname}")
                            st.info("Link not available")
                else:
                    st.markdown(f"{idx}. {src}")
        else:
            st.info("No source references found")
        
        st.markdown("---")
        
        # Document links section (if different from sources)
            # if obj.get("intranet_doc_links"):
            #     st.subheader("Related Documents")
                
            #     # Display as cards in columns
            #     num_links = len(obj["intranet_doc_links"])
            #     if num_links <= 3:
            #         cols = st.columns(num_links)
            #         for i, (col, link) in enumerate(zip(cols, obj["intranet_doc_links"]), 1):
            #             with col:
            #                 st.markdown(f"**Document {i}**")
            #                 st.link_button(f"Open Doc {i}", link, use_container_width=True)
            #     else:
            #         # For more than 3, use a list format
            #         for i, link in enumerate(obj["intranet_doc_links"], 1):
            #             col1, col2 = st.columns([0.8, 0.2])
            #             with col1:
            #                 st.markdown(f"**Document {i}:**")
            #             with col2:
            #                 st.link_button("Open", link, key=f"doc_link_{i}")
        
    #     # Optional: Add download summary button
    #     if obj.get("intranet_summary"):
    #         st.markdown("---")
    #         col1, col2, col3 = st.columns([1, 1, 1])
    #         with col2:
    #             summary_text = f"""
    # Policy Document Analysis Summary
    # {'='*50}

    # {obj['intranet_summary']}

    # {'='*50}
    # Sources Analyzed: {obj.get('intranet_doc_count', 0)}
    # Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    # """
    #             st.download_button(
    #                 label="Download Analysis",
    #                 data=summary_text,
    #                 file_name=f"policy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
    #                 mime="text/plain",
    #                 use_container_width=True
    #             )

def _render_faiss_block(entry):
    """Render faiss route elements from the archived entry."""
    st.subheader("Internal Knowledge Base Answer:")
    st.markdown(entry.get("faiss_summary", "_No summary available._"))

    faiss_images = entry.get("faiss_images", [])
    faiss_sources = entry.get("faiss_sources", [])
    if faiss_images and faiss_sources:
        top_doc = faiss_sources[0][0]
        st.subheader(f"Images from: {top_doc}")
        for meta in faiss_images:
            if meta.get("original_doc") == top_doc:
                img_path = meta.get("extracted_image_path")
                if img_path and os.path.exists(img_path):
                    st.image(img_path, caption=meta.get("caption", ""), use_container_width=True)

    st.subheader("Document Sources:")
    project_root = Path(__file__).resolve().parent.parent
    workspace_root = project_root.parent
    for i, src in enumerate(faiss_sources, 1):
        if isinstance(src, (list, tuple)):
            docname = src[0] if len(src) > 0 else f"Document {i}"
            snippet = src[1] if len(src) > 1 else ""
            path = src[2] if len(src) > 2 else None
        else:
            docname = str(src)
            snippet = ""
            path = None

        full_path = None
        raw_path = str(path) if path else ""
        doc_base = os.path.basename(docname or raw_path or "")
        candidate_paths = []

        if raw_path:
            if os.path.isabs(raw_path):
                candidate_paths.append(Path(raw_path))
            else:
                candidate_paths.append((project_root / raw_path).resolve())
                candidate_paths.append((workspace_root / raw_path).resolve())
                candidate_paths.append((project_root / "Documents" / Path(raw_path).name).resolve())
                candidate_paths.append((workspace_root / "Documents" / Path(raw_path).name).resolve())

        if doc_base:
            candidate_paths.append((project_root / "Documents" / doc_base).resolve())
            candidate_paths.append((workspace_root / "Documents" / doc_base).resolve())

        seen = set()
        for candidate in candidate_paths:
            candidate_str = str(candidate)
            if candidate_str in seen:
                continue
            seen.add(candidate_str)
            if candidate.exists() and candidate.is_file():
                full_path = candidate_str
                break

        if full_path:
            with open(full_path, "rb") as f:
                file_bytes = f.read()
            file_name = os.path.basename(full_path).replace('"', "")
            link_text = str(docname).replace("<", "&lt;").replace(">", "&gt;")
            b64 = base64.b64encode(file_bytes).decode("utf-8")
            st.markdown(
                f'{i}. <a href="data:application/octet-stream;base64,{b64}" download="{file_name}">{link_text}</a>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{i}. {docname}**")
            st.caption("File not found for download.")

        if snippet:
            snippet_text = str(snippet).strip()
            doc_text = str(docname).strip()
            if snippet_text and snippet_text.lower() != doc_text.lower():
                st.markdown(snippet_text)
def _render_run_by_route(run):
    import pandas as pd
    
    route = run.get("route")


    # For SQL-like or document-like routes, we show sql and result
    if route in ["sql", "document", "comp"]:

        # For comparison runs, show summaries and web links if present
        if route == "comp":

            if run.get("comparison_summary"):
                st.subheader("Comparison Summary:")
                st.markdown(run["comparison_summary"])
            if run.get("general_summary"):
                st.subheader("General Summary:")
                st.markdown(run["general_summary"])
            st.subheader("Top Web Links:")
            for i, (link, summary) in enumerate(run.get("web_links") or [], 1):
                st.markdown(f"**{i}.** {link}")
                st.markdown(f"_Summary:_\n{summary}")


        
        # SQL Query Result
        if run.get("sql_query"):
            st.subheader("SQL Query:")
            st.code(run["sql_query"], language="sql")

            st.subheader("SQL Query Result:")
            result_df = run.get("result")
            formatted = _format_dataframe_for_display(result_df)
            if isinstance(formatted, pd.DataFrame):
                st.dataframe(_with_one_based_index(formatted))
            else:
                st.text(formatted if formatted is not None else "_No result returned_")

    elif route == "faissdb":
        # faissdb runs may be stored within a run or (for older entries) at the top-level entry.
        _render_faiss_block(run)
        
    elif route == "intranet":
        # Intranet route - Policy Document Analysis
        _render_intranet_block(run)

    elif route == "search":
        if run.get("general_summary"):
            st.subheader("General Summary:")
            st.markdown(run["general_summary"])
        st.subheader("Top Web Links:")
        for i, (link, summary) in enumerate(run.get("result") or [], 1):
            st.markdown(f"**{i}.** {link}")
            st.markdown(f"_Summary:_\n{summary}")

    else:
        # Fallback: print any summary or raw result
        if run.get("general_summary"):
            st.subheader("General Summary:")
            st.markdown(run["general_summary"])
        if run.get("result"):
            st.subheader("Result:")
            formatted = _format_dataframe_for_display(run.get("result"))
            if isinstance(formatted, pd.DataFrame):
                st.dataframe(_with_one_based_index(formatted))
            else:
                st.text(formatted)

