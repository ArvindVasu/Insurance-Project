from __future__ import annotations

import html
import tempfile

import pandas as pd
import streamlit as st

from agents.document_agent import document_node
from services.auth_service import require_auth
from services.Common_Functions import _format_dataframe_for_display
from services.Graph_state import GraphState
from services.ui_theme import apply_theme, render_hero, render_top_nav

require_auth()
apply_theme("Document Insights", icon=":page_facing_up:")
render_top_nav(show_search=False)
render_hero(
    "Document Insights",
    "Analyze one underwriting document or compare two document versions to identify key changes and underwriting impact.",
)

if "doc_insight_last_output" not in st.session_state:
    st.session_state.doc_insight_last_output = None
if "doc_insight_last_mode" not in st.session_state:
    st.session_state.doc_insight_last_mode = "single"


def _save_uploaded_file(uploaded_file) -> tuple[str, str]:
    ext = uploaded_file.name.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name, ext


def _render_preview_dataframe(df: pd.DataFrame | None) -> None:
    formatted = _format_dataframe_for_display(df)
    if isinstance(formatted, pd.DataFrame) and not formatted.empty:
        display_df = formatted.copy()
        display_df.index = range(1, len(display_df) + 1)
        st.dataframe(display_df, use_container_width=True)


def _run_document_analysis(state: GraphState, status_label: str):
    progress_text = st.empty()
    progress_bar = st.progress(0, text="Starting...")
    with st.status(status_label, expanded=True) as run_status:
        progress_text.info("1/3 Parsing")
        progress_bar.progress(33, text="1/3 Parsing uploaded document input...")
        run_status.write("1/3 Parsing uploaded document input...")

        progress_text.info("2/3 Extracting")
        progress_bar.progress(66, text="2/3 Extracting content and comparison context...")
        run_status.write("2/3 Extracting content and comparison context...")

        output = document_node(state)

        progress_text.info("3/3 Summarizing")
        progress_bar.progress(90, text="3/3 Summarizing underwriting insights...")
        run_status.write("3/3 Summarizing underwriting insights...")
        progress_bar.progress(100, text="Completed")
        progress_text.success("Completed")
        run_status.update(label="Document analysis completed", state="complete")
    return output


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

    .doc-result-box {
      background: #ffffff;
      border: 1px solid #d6e4f5;
      border-radius: 12px;
      padding: 14px 16px;
      box-shadow: 0 6px 16px rgba(18, 42, 76, 0.08);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

single_tab, compare_tab = st.tabs(["Analyze One Document", "Compare Two Documents"])

with single_tab:
    st.markdown("### Single Document Analysis")
    st.markdown('<div class="doc-form-card">', unsafe_allow_html=True)
    with st.form("doc_insight_single_form"):
        col1, col2 = st.columns([1, 2])
        with col1:
            uploaded = st.file_uploader(
                "Upload File",
                type=["docx", "xlsx", "xls", "csv", "pdf", "txt"],
                help="Supported formats: DOCX, Excel, CSV, PDF, TXT",
                key="doc_insight_single_upload",
            )
        with col2:
            prompt = st.text_area(
                "Insight Prompt",
                placeholder="Example: Summarize coverage gaps and underwriting red flags in this submission.",
                height=140,
                key="doc_insight_single_prompt",
            )

        run_single = st.form_submit_button("Run Document Analysis", use_container_width=True, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("Tip: include context like line of business, policy type, and risk concerns for better insights.")

    if run_single:
        if not uploaded:
            st.error("Upload a document first.")
            st.stop()
        if not prompt.strip():
            st.error("Add an insight prompt.")
            st.stop()

        file_path, ext = _save_uploaded_file(uploaded)
        state: GraphState = {
            "user_prompt": prompt,
            "uploaded_file1": uploaded,
            "uploaded_file1_name": uploaded.name,
            "uploaded_file1_path": file_path,
            "uploaded_file1_is_excel": ext in {"xlsx", "xls", "csv"},
            "uploaded_file1_is_docx": ext == "docx",
            "route": "document",
        }
        st.session_state.doc_insight_last_output = _run_document_analysis(
            state,
            "Running document analysis...",
        )
        st.session_state.doc_insight_last_mode = "single"

with compare_tab:
    st.markdown("### Compare Two Documents")
    st.markdown(
        "Ask a comparison question, upload the current-year and prior-year documents, and get the key differences with underwriting impact."
    )
    st.markdown('<div class="doc-form-card">', unsafe_allow_html=True)
    with st.form("doc_insight_compare_form"):
        left_col, right_col = st.columns(2)
        with left_col:
            current_doc = st.file_uploader(
                "Current-Year Document",
                type=["docx", "xlsx", "xls", "csv", "pdf", "txt"],
                help="Upload the latest guideline or submission document.",
                key="doc_insight_compare_current",
            )
        with right_col:
            prior_doc = st.file_uploader(
                "Prior-Year Document",
                type=["docx", "xlsx", "xls", "csv", "pdf", "txt"],
                help="Upload the prior-year version for comparison.",
                key="doc_insight_compare_prior",
            )

        compare_prompt = st.text_area(
            "Comparison Question",
            placeholder=(
                "Example: What changed between this year's underwriting guideline and last year's "
                "version, and what is the underwriting impact on appetite, exclusions, deductibles, authority, and actions?"
            ),
            height=140,
            key="doc_insight_compare_prompt",
        )
        run_compare = st.form_submit_button("Compare Documents", use_container_width=True, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("Tip: upload current-year on the left and prior-year on the right for the clearest comparison output.")

    if run_compare:
        if not current_doc or not prior_doc:
            st.error("Upload both documents for comparison.")
            st.stop()
        if not compare_prompt.strip():
            st.error("Ask a comparison question.")
            st.stop()

        current_path, current_ext = _save_uploaded_file(current_doc)
        prior_path, prior_ext = _save_uploaded_file(prior_doc)
        state = {
            "user_prompt": compare_prompt,
            "uploaded_file1": current_doc,
            "uploaded_file1_name": current_doc.name,
            "uploaded_file1_path": current_path,
            "uploaded_file1_is_excel": current_ext in {"xlsx", "xls", "csv"},
            "uploaded_file1_is_docx": current_ext == "docx",
            "uploaded_file2": prior_doc,
            "uploaded_file2_name": prior_doc.name,
            "uploaded_file2_path": prior_path,
            "uploaded_file2_is_excel": prior_ext in {"xlsx", "xls", "csv"},
            "uploaded_file2_is_docx": prior_ext == "docx",
            "route": "document",
        }
        st.session_state.doc_insight_last_output = _run_document_analysis(
            state,
            "Running document comparison...",
        )
        st.session_state.doc_insight_last_mode = "compare"

last_output = st.session_state.doc_insight_last_output
last_mode = st.session_state.doc_insight_last_mode

if last_output:
    if last_mode == "compare":
        current_name = last_output.get("document_compare_name_1") or "Current-Year Document"
        prior_name = last_output.get("document_compare_name_2") or "Prior-Year Document"

        if (last_output.get("user_prompt") or "").strip():
            st.markdown("### Comparison Question")
            st.markdown(last_output.get("user_prompt"))

        st.markdown("### Comparison Insight")
        comparison_text = last_output.get("comparison_summary") or last_output.get("general_summary") or "No comparison summary generated."
        st.markdown(
            f'<div class="doc-result-box">{html.escape(str(comparison_text)).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )

        preview_1 = last_output.get("document_compare_preview_1")
        preview_2 = last_output.get("document_compare_preview_2")
        if (
            isinstance(preview_1, pd.DataFrame)
            and not preview_1.empty
        ) or (
            isinstance(preview_2, pd.DataFrame)
            and not preview_2.empty
        ):
            st.markdown("### Document Previews")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### {current_name}")
                _render_preview_dataframe(preview_1)
            with col2:
                st.markdown(f"#### {prior_name}")
                _render_preview_dataframe(preview_2)
    else:
        st.markdown("### Analysis")
        st.markdown(last_output.get("general_summary") or "No summary generated.")

        result = last_output.get("sql_result")
        if isinstance(result, pd.DataFrame) and not result.empty:
            st.markdown("### Data Preview")
            _render_preview_dataframe(result)
