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

SQL_HIDDEN_OUTPUT_COLUMNS = {
    "total_incurred_loss",
    "loss_ratio_percentile_basis",
    "loss_ratio_source",
    "client_loss_ratio_source",
    "client_claims_frequency_source",
    "client_severity_source",
    "client_incurred_source",
    "lob_hint",
    "source_db",
}




def _decision_to_button_label(decision: str | None) -> str:
    mapping = {
        "WRITE": "Generate Final Document (EOI)",
        "WRITE_WITH_CONDITIONS": "Generate Final Document (Conditional EOI)",
        "REFER": "Generate Final Document (Underwriting Memo)",
        "DECLINE": "Generate Final Document (Decline Letter)",
    }
    return mapping.get(str(decision or "").upper(), "Generate Final Document")


def _metric_label(metric_key: str) -> str:
    labels = {
        "loss_quality_composite": "Loss Quality Composite (Loss Ratio Percentile)",
        "loss_pattern_risk": "Loss Pattern Risk (Freq/Severity/Incurred)",
        "revenue_scale_risk": "Revenue Scale Risk",
        "geographic_spread_risk": "Geographic Spread Risk",
        "risk_management_quality": "Risk Management Quality (Inverted)",
        "external_risk": "External Risk",
        "coverage_complexity": "Coverage Complexity",
        "guideline_fit": "Guideline Fit (Inverted)",
    }
    return labels.get(metric_key, metric_key.replace("_", " ").title())


def _generate_final_document() -> None:
    with st.spinner("Preparing final document from decision engine..."):
        doc_bytes, file_name = generate_eoi_document(
            user_prompt=st.session_state.eoi_last_prompt,
            eoi_state=st.session_state.eoi_last_output,
        )
        st.session_state.eoi_generated_doc = doc_bytes
        st.session_state.eoi_generated_name = file_name
        st.session_state.eoi_show_download_dialog = True


def _show_download_dialog() -> None:
    st.write("Final document generated from decision engine. Download below.")
    downloaded = st.download_button(
        "Download Final Document",
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
    last_decision = (st.session_state.eoi_last_output or {}).get("eoi_decision")
    generate_clicked = st.button(
        _decision_to_button_label(last_decision),
        use_container_width=True,
        type="secondary",
    )

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
    st.session_state.eoi_generated_name = "Generated_Insurance_EOI.docx"
    if str(output.get("eoi_decision") or "").upper() == "WRITE":
        try:
            _generate_final_document()
        except Exception as exc:
            st.error(f"Failed to auto-generate EOI document: {exc}")
    # Refresh immediately so "Generate EOI" picks up green styling as soon as analysis is done.
    st.rerun()

if generate_clicked:
    if not st.session_state.eoi_last_output:
        st.error("Run EOI Analysis first. Final document generation uses the latest decision output.")
    else:
        try:
            _generate_final_document()
        except Exception as exc:
            st.error(f"Failed to generate final document: {exc}")

last_output = st.session_state.eoi_last_output
if last_output:
    snapshot = last_output.get("eoi_executive_snapshot") or {}
    risk_profile = last_output.get("eoi_risk_profile") or {}
    metric_scores = last_output.get("eoi_metric_scores") or {}
    weighted = last_output.get("eoi_weighted_contributions") or {}
    hard_rules = last_output.get("eoi_hard_rule_hits") or []
    hard_rule_triggered = bool(last_output.get("eoi_hard_rule_triggered"))
    web_risk = last_output.get("eoi_web_risk") or {}
    geo_web_summary = last_output.get("eoi_geo_web_summary") or ""
    geo_web_links = last_output.get("eoi_geo_web_links") or []
    geo_web_prompt = last_output.get("eoi_geo_web_prompt") or ""
    if snapshot:
        doc_txt = html.escape(str(snapshot.get("document_agent_summary", "Not available"))).replace("\n", "<br>")
        vanna_txt = html.escape(str(snapshot.get("vanna_agent_summary", "Not available"))).replace("\n", "<br>")
        web_txt = html.escape(str(snapshot.get("web_agent_summary", "Not available"))).replace("\n", "<br>")
        intranet_txt = html.escape(str(snapshot.get("intranet_agent_summary", "Not available"))).replace("\n", "<br>")
        rec_txt = html.escape(str(snapshot.get("final_recommendation", "Not available"))).replace("\n", "<br>")
        decision_txt = html.escape(str(last_output.get("eoi_decision") or snapshot.get("decision") or "Not available"))
        risk_txt = html.escape(str(last_output.get("eoi_risk_score") or snapshot.get("risk_score") or "Not available"))
        conf_txt = html.escape(str(last_output.get("eoi_confidence_score") or snapshot.get("confidence_score") or "Not available"))

        snapshot_html = f"""
<div class="eoi-exec-box">
  <div class="eoi-exec-title">Executive Snapshot</div>
  <p><strong>Decision:</strong> {decision_txt}</p>
  <p><strong>Risk Score:</strong> {risk_txt}</p>
  <p><strong>Confidence Score:</strong> {conf_txt}</p>
  <p><strong>Document Agent:</strong> {doc_txt}</p>
  <p><strong>SQL Agent:</strong> {vanna_txt}</p>
  <p><strong>Web Agent:</strong> {web_txt}</p>
  <p><strong>Intranet Agent:</strong> {intranet_txt}</p>
  <p><strong>Final Recommendation:</strong> {rec_txt}</p>
</div>
"""
        st.markdown(snapshot_html, unsafe_allow_html=True)

    # st.markdown("### Risk Profile JSON")
    # st.json(
    #     {
    #         "lob": risk_profile.get("lob", "Not specified"),
    #         "tiv": risk_profile.get("tiv", "Not specified"),
    #         "turnover": risk_profile.get("turnover", "Not specified"),
    #         "sites": risk_profile.get("sites", "Not specified"),
    #     }
    # )

    # st.markdown("### Decision Engine")
    # st.write(f"Hard Rule Triggered: {'Yes' if hard_rule_triggered else 'No'}")
    # if hard_rules:
    #     for idx, hr in enumerate(hard_rules, 1):
    #         st.markdown(f"{idx}. {hr}")

    if web_risk:
        st.markdown("### Web Hazard Risk (Geo-Based)")
        st.write(f"Risk Score: {web_risk.get('score', 'N/A')}")
        st.write(f"Risk Level: {web_risk.get('level', 'N/A')}")
        geo_tokens = web_risk.get("geo_tokens") or []
        detected = web_risk.get("detected_hazards") or {}
        detected_labels = [k.title() for k, v in detected.items() if v]
        st.write(f"Geographies Analyzed: {', '.join(geo_tokens) if geo_tokens else 'Not specified'}")
        st.write(f"Hazard Categories Flagged: {', '.join(detected_labels) if detected_labels else 'None'}")
        for idx, d in enumerate(web_risk.get("drivers") or [], start=1):
            st.markdown(f"{idx}. {d}")
        if geo_web_prompt:
            st.caption(f"Geo Risk SERP Prompt: {geo_web_prompt}")
        if geo_web_summary:
            st.markdown("#### Geo Risk Web Summary")
            st.markdown(geo_web_summary)
        if geo_web_links:
            st.markdown("#### Geo Risk Web Links")
            for idx, item in enumerate(geo_web_links[:5], start=1):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    st.markdown(f"**{idx}.** {item[0]}")
                    st.markdown(f"_Summary:_ {item[1]}")
                else:
                    st.markdown(f"**{idx}.** {item}")

    # if metric_scores:
    #     st.markdown("### Normalization Layer (0-100)")
    #     metric_order = [
    #         "loss_quality_composite",
    #         "loss_pattern_risk",
    #         "revenue_scale_risk",
    #         "geographic_spread_risk",
    #         "risk_management_quality",
    #         "external_risk",
    #         "coverage_complexity",
    #         "guideline_fit",
    #     ]
    #     ordered_metrics = [(k, metric_scores[k]) for k in metric_order if k in metric_scores]
    #     ordered_metrics.extend([(k, v) for k, v in metric_scores.items() if k not in metric_order])
    #     metric_df = pd.DataFrame(
    #         [
    #             {"Metric": _metric_label(k), "Normalized Score": v}
    #             for k, v in ordered_metrics
    #         ]
    #     )
    #     st.dataframe(metric_df, use_container_width=True, hide_index=True)

    # if weighted:
    #     st.markdown("### Weighted Scoring Engine")
    #     metric_order = [
    #         "loss_quality_composite",
    #         "loss_pattern_risk",
    #         "revenue_scale_risk",
    #         "geographic_spread_risk",
    #         "risk_management_quality",
    #         "external_risk",
    #         "coverage_complexity",
    #         "guideline_fit",
    #     ]
    #     ordered_weighted = [(k, weighted[k]) for k in metric_order if k in weighted]
    #     ordered_weighted.extend([(k, v) for k, v in weighted.items() if k not in metric_order])
    #     weighted_df = pd.DataFrame(
    #         [
    #             {"Metric": _metric_label(k), "Weighted Contribution": v}
    #             for k, v in ordered_weighted
    #         ]
    #     ).sort_values("Weighted Contribution", ascending=False)
    #     st.dataframe(weighted_df, use_container_width=True, hide_index=True)

    conditions = last_output.get("eoi_conditions") or []
    if conditions:
        st.markdown("### Conditions")
        for idx, cond in enumerate(conditions, start=1):
            st.markdown(f"{idx}. {cond}")

    st.markdown("### Broker Submission Document Insights")
    st.markdown(last_output.get("eoi_doc_insights") or "No document insights generated.")

    if last_output.get("sql_query"):
        st.markdown("### SQL Query")
        st.code(last_output["sql_query"], language="sql")

    result_df = last_output.get("sql_result")
    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        drop_cols = [c for c in result_df.columns if str(c).strip().lower() in SQL_HIDDEN_OUTPUT_COLUMNS]
        if drop_cols:
            result_df = result_df.drop(columns=drop_cols, errors="ignore")
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
        @st.dialog("Final Document Ready")
        def _download_dialog() -> None:
            _show_download_dialog()

        _download_dialog()
    else:
        st.success("Final document generated.")
        st.download_button(
            "Download Final Document",
            data=st.session_state.eoi_generated_doc,
            file_name=st.session_state.eoi_generated_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            key="eoi_download_fallback_btn",
        )
