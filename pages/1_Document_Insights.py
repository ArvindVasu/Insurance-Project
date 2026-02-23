from __future__ import annotations

import tempfile

import pandas as pd
import streamlit as st

from agents.document_agent import document_node
from services.auth_service import require_auth
from services.Graph_state import GraphState
from services.ui_theme import apply_theme, render_hero, render_top_nav

require_auth()
apply_theme("Document Insights", icon=":page_facing_up:")
render_top_nav(show_search=False)
render_hero(
    "Document Insights",
    "Upload underwriting documents and ask focused prompts for risk, coverage, and submission quality checks.",
)
st.markdown(
    """
    <style>
    .doc-form-card {
      background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%);
      border: 2px solid #355f8f;
      border-radius: 14px;
      padding: 12px 14px 2px 14px;
      margin: 10px 0 12px 0;
      box-shadow: 0 10px 22px rgba(18, 42, 76, 0.12);
    }

    .doc-form-card label, .doc-form-card [data-testid="stWidgetLabel"] {
      color: #12335f !important;
      font-weight: 700 !important;
      font-size: 16px !important;
      letter-spacing: 0.2px;
    }

    .doc-form-card [data-testid="stTextArea"] textarea {
      background: #ffffff !important;
      border: 2px solid #7aa5d8 !important;
      border-radius: 12px !important;
      color: #0f2d52 !important;
      box-shadow: 0 4px 12px rgba(30, 80, 140, 0.08);
      font-weight: 600;
    }
    .doc-form-card [data-testid="stTextArea"] textarea:focus {
      border-color: #0f766e !important;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.18), 0 6px 14px rgba(15, 118, 110, 0.12) !important;
    }

    .doc-form-card [data-testid="stFormSubmitButton"] button,
    .doc-form-card .stButton button {
      background: linear-gradient(135deg, #0b4f91 0%, #0f766e 100%) !important;
      color: #ffffff !important;
      border: 1px solid #0b4f91 !important;
      border-radius: 10px !important;
      font-weight: 700 !important;
      font-size: 18px !important;
      min-height: 44px;
      box-shadow: 0 8px 18px rgba(11, 79, 145, 0.24);
      transition: transform 0.15s ease, box-shadow 0.2s ease;
    }
    .doc-form-card [data-testid="stFormSubmitButton"] button:hover,
    .doc-form-card .stButton button:hover {
      transform: translateY(-1px);
      box-shadow: 0 10px 22px rgba(11, 79, 145, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("### Upload and Analyze")

st.markdown('<div class="doc-form-card">', unsafe_allow_html=True)
with st.form("doc_insight_form"):
    col1, col2 = st.columns([1, 2])
    with col1:
        uploaded = st.file_uploader(
            "Upload File",
            type=["docx", "xlsx", "xls", "csv", "pdf", "txt"],
            help="Supported formats: DOCX, Excel, CSV, PDF, TXT",
        )
    with col2:
        prompt = st.text_area(
            "Insight Prompt",
            placeholder="Example: Summarize coverage gaps and underwriting red flags in this submission.",
            height=140,
        )

    run = st.form_submit_button("Run Document Analysis", use_container_width=True, type="primary")
st.markdown("</div>", unsafe_allow_html=True)
st.caption("Tip: include context like line of business, policy type, and risk concerns for better insights.")

if run:
    if not uploaded:
        st.error("Upload a document first.")
        st.stop()
    if not prompt.strip():
        st.error("Add an insight prompt.")
        st.stop()

    ext = uploaded.name.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded.read())
        file_path = tmp.name

    state: GraphState = {
        "user_prompt": prompt,
        "uploaded_file1": uploaded,
        "uploaded_file1_path": file_path,
        "uploaded_file1_is_excel": ext in {"xlsx", "xls", "csv"},
        "uploaded_file1_is_docx": ext == "docx",
        "route": "document",
    }

    progress_text = st.empty()
    progress_bar = st.progress(0, text="Starting...")
    with st.status("Running document analysis...", expanded=True) as run_status:
        progress_text.info("1/3 Parsing")
        progress_bar.progress(33, text="1/3 Parsing uploaded document...")
        run_status.write("1/3 Parsing uploaded document...")

        progress_text.info("2/3 Extracting")
        progress_bar.progress(66, text="2/3 Extracting content and context...")
        run_status.write("2/3 Extracting content and context...")

        output = document_node(state)

        progress_text.info("3/3 Summarizing")
        progress_bar.progress(90, text="3/3 Summarizing underwriting insights...")
        run_status.write("3/3 Summarizing underwriting insights...")
        progress_bar.progress(100, text="Completed")
        progress_text.success("Completed")
        run_status.update(label="Document analysis completed", state="complete")

    st.markdown("### Analysis")
    st.markdown(output.get("general_summary") or "No summary generated.")

    result = output.get("sql_result")
    if isinstance(result, pd.DataFrame) and not result.empty:
        st.markdown("### Data Preview")
        st.dataframe(result, use_container_width=True)
