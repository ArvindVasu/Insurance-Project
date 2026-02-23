from __future__ import annotations

import html
import tempfile

import pandas as pd
import streamlit as st

from agents.EOI_agent import EOI_node, generate_eoi_document
from services.auth_service import require_auth
from services.Common_Functions import _format_dataframe_for_display
from services.ui_theme import apply_theme, render_hero, render_top_nav

require_auth()
apply_theme("EOI Generator", icon=":page_facing_up:")
render_top_nav(show_search=False)
render_hero(
    "Expression of Interest Generator",
    "Analyze broker submissions with internal portfolio context and external market snapshots.",
)

if "eoi_last_output" not in st.session_state:
    st.session_state.eoi_last_output = None
if "eoi_last_prompt" not in st.session_state:
    st.session_state.eoi_last_prompt = ""
if "eoi_generated_doc" not in st.session_state:
    st.session_state.eoi_generated_doc = None
if "eoi_generated_name" not in st.session_state:
    st.session_state.eoi_generated_name = "Generated_Insurance_EOI.docx"
if "eoi_show_download_dialog" not in st.session_state:
    st.session_state.eoi_show_download_dialog = False




def _show_download_dialog() -> None:
    st.write("EOI generation completed. Download your document below.")
    downloaded = st.download_button(
        "Download EOI Document",
        data=st.session_state.eoi_generated_doc,
        file_name=st.session_state.eoi_generated_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
        key="eoi_download_dialog_btn",
    )
    if downloaded:
        st.session_state.eoi_show_download_dialog = False
        st.rerun()
    if st.button("Close", use_container_width=True, key="eoi_download_dialog_close"):
        st.session_state.eoi_show_download_dialog = False
        st.rerun()


st.markdown(
    """
    <style>
    .eoi-form-card {
      background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%);
      border: 2px solid #355f8f;
      border-radius: 14px;
      padding: 12px 14px 2px 14px;
      margin: 10px 0 12px 0;
      box-shadow: 0 10px 22px rgba(18, 42, 76, 0.12);
    }
    .eoi-exec-box {
      background: #ffffff;
      border: 2px solid #0f3d75;
      border-radius: 16px;
      padding: 16px 18px;
      margin: 10px 0 16px 0;
      box-shadow: 0 8px 18px rgba(15, 61, 117, 0.10);
      display: block;
    }
    .eoi-exec-title {
      font-weight: 800;
      color: #0f3d75;
      margin-bottom: 12px;
      font-size: 18px;
      letter-spacing: 0.2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.eoi_last_output:
    st.markdown(
        """
        <style>
        /* After analysis: highlight Generate EOI (secondary button) with a light green gradient */
        [data-testid="stButton"] button[kind="secondary"] {
          background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%) !important;
          border: 1px solid #86efac !important;
          color: #14532d !important;
          font-weight: 700 !important;
          box-shadow: 0 6px 14px rgba(34, 197, 94, 0.18);
        }
        [data-testid="stButton"] button[kind="secondary"]:hover {
          background: linear-gradient(135deg, #bbf7d0 0%, #86efac 100%) !important;
          border-color: #4ade80 !important;
          color: #14532d !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### Submission Input")
st.markdown('<div class="eoi-form-card">', unsafe_allow_html=True)
user_prompt = st.text_input(
    "Prompt",
    placeholder="Example: Summarize this broker submission and compare with recent market trend.",
)
uploaded_file = st.file_uploader(
    "Attach Broker Submission",
    type=["pdf", "docx", "txt"],
    help="Supported formats: PDF, DOCX, TXT",
)

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    run_clicked = st.button("Run EOI Analysis", use_container_width=True, type="primary")
with btn_col2:
    generate_clicked = st.button("Generate EOI", use_container_width=True, type="secondary")

st.markdown("</div>", unsafe_allow_html=True)

if run_clicked:
    if not user_prompt.strip():
        st.error("Enter a prompt.")
        st.stop()

    if not uploaded_file:
        st.error("Attach a broker submission document.")
        st.stop()

    ext = uploaded_file.name.split(".")[-1].lower().strip()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_file.read())
        uploaded_file_path = tmp.name

    state = {
        "user_prompt": user_prompt,
        "uploaded_file1": uploaded_file,
        "uploaded_file1_path": uploaded_file_path,
        "uploaded_file1_is_docx": ext == "docx",
    }

    with st.spinner("Running EOI analysis..."):
        output = EOI_node(state)

    st.session_state.eoi_last_output = output
    st.session_state.eoi_last_prompt = user_prompt
    st.session_state.eoi_generated_doc = None
    # Refresh immediately so "Generate EOI" picks up green styling as soon as analysis is done.
    st.rerun()

if generate_clicked:
    if not st.session_state.eoi_last_output:
        st.error("Run EOI Analysis first. Generate EOI uses the latest generated insights.")
    else:
        with st.spinner("Filling EOI template and preparing download..."):
            try:
                doc_bytes, file_name = generate_eoi_document(
                    user_prompt=st.session_state.eoi_last_prompt,
                    eoi_state=st.session_state.eoi_last_output,
                )
                st.session_state.eoi_generated_doc = doc_bytes
                st.session_state.eoi_generated_name = file_name
                st.session_state.eoi_show_download_dialog = True
            except Exception as exc:
                st.error(f"Failed to generate EOI document: {exc}")

last_output = st.session_state.eoi_last_output
if last_output:
    snapshot = last_output.get("eoi_executive_snapshot") or {}
    if snapshot:
        doc_txt = html.escape(str(snapshot.get("document_agent_summary", "Not available")))
        vanna_txt = html.escape(str(snapshot.get("vanna_agent_summary", "Not available")))
        web_txt = html.escape(str(snapshot.get("web_agent_summary", "Not available")))
        intranet_txt = html.escape(str(snapshot.get("intranet_agent_summary", "Not available")))
        rec_txt = html.escape(str(snapshot.get("final_recommendation", "Not available"))).replace("\n", "<br>")

        snapshot_html = f"""
<div class="eoi-exec-box">
  <div class="eoi-exec-title">Executive Snapshot</div>
  <p><strong>Document Agent:</strong> {doc_txt}</p>
  <p><strong>Vanna Agent:</strong> {vanna_txt}</p>
  <p><strong>Web Agent:</strong> {web_txt}</p>
  <p><strong>Intranet Agent:</strong> {intranet_txt}</p>
  <p><strong>Final Recommendation:</strong> {rec_txt}</p>
</div>
"""
        st.markdown(snapshot_html, unsafe_allow_html=True)

    st.markdown("### Document Insights")
    st.markdown(last_output.get("eoi_doc_insights") or "No document insights generated.")

    if last_output.get("sql_query"):
        st.markdown("### SQL Query")
        st.code(last_output["sql_query"], language="sql")

    result_df = last_output.get("sql_result")
    formatted = _format_dataframe_for_display(result_df)
    if isinstance(formatted, pd.DataFrame) and not formatted.empty:
        st.markdown("### Internal Data Snapshot")
        st.dataframe(formatted, use_container_width=True)

    if last_output.get("general_summary"):
        st.markdown("### External Summary")
        st.markdown(last_output["general_summary"])

    if last_output.get("serp_prompt"):
        st.caption(f"SERP Prompt: {last_output['serp_prompt']}")

    links = last_output.get("web_links") or []
    if links:
        st.markdown("### Top Web Links")
        for idx, (link, summary) in enumerate(links[:5], start=1):
            st.markdown(f"**{idx}.** {link}")
            st.markdown(f"_Summary:_ {summary}")

    if last_output.get("intranet_summary"):
        lob = last_output.get("intranet_lob")
        title = "### Intranet Policy Insights"
        if lob:
            title += f" ({lob})"
        st.markdown(title)
        st.markdown(last_output["intranet_summary"])

    intranet_sources = last_output.get("intranet_sources") or []
    if intranet_sources:
        st.markdown("### Intranet Sources")
        for idx, src in enumerate(intranet_sources, start=1):
            if isinstance(src, (list, tuple)) and len(src) >= 2:
                fname, link = src[0], src[1]
                if link:
                    st.markdown(f"**{idx}.** [{fname}]({link})")
                else:
                    st.markdown(f"**{idx}.** {fname}")
            else:
                st.markdown(f"**{idx}.** {src}")

if st.session_state.eoi_generated_doc and st.session_state.eoi_show_download_dialog:
    if hasattr(st, "dialog"):
        @st.dialog("EOI Document Ready")
        def _download_dialog() -> None:
            _show_download_dialog()

        _download_dialog()
    else:
        st.success("EOI generation completed.")
        st.download_button(
            "Download EOI Document",
            data=st.session_state.eoi_generated_doc,
            file_name=st.session_state.eoi_generated_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="eoi_download_fallback_btn",
        )
