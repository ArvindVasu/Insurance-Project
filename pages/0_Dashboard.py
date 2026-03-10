from __future__ import annotations

import streamlit as st

from services.auth_service import require_auth
from services.ui_theme import apply_theme, render_hero, render_top_nav
from services.underwriter_data import fetch_kpis, fetch_lob_loss_ratio, fetch_recent_trend

require_auth()
apply_theme("ASTRA Underwriting Workbench", icon=":shield:")
render_top_nav(show_search=False)

render_hero(
    "ASTRA Underwriting Workbench",
    "Daily underwriting cockpit with routed AI assistant, document intelligence, and checkpointed chat sessions.",
)

st.markdown("### Portfolio Snapshot")

kpis = fetch_kpis()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Ultimate Premium (USD mn)", f"${kpis['total_premium'] / 1_000_000:,.2f}")
col2.metric("Total Incurred Loss (USD mn)", f"${kpis['total_incurred'] / 1_000_000:,.2f}")
col3.metric("Avg Loss Ratio", f"{kpis['avg_loss_ratio'] * 100:.2f}%")
col4.metric("Avg Claims Frequency", f"{kpis['avg_claims_frequency']:.2f}")

left, right = st.columns([1.1, 1])
with left:
    st.markdown("#### Line of Business Trend (USD mn)")
    trend_df = fetch_recent_trend()
    if not trend_df.empty:
        chart_df = trend_df.set_index("line_of_business")[["incurred_loss", "ultimate_premium"]] / 1_000_000
        st.bar_chart(chart_df)

with right:
    st.markdown("#### LOB Loss Ratio")
    lob_df = fetch_lob_loss_ratio()
    if not lob_df.empty:
        chart_df = lob_df[["reserve_class", "avg_loss_ratio"]].set_index("reserve_class")
        st.bar_chart(chart_df)

st.markdown("### Workspace")
st.info(
    "Use the left sidebar pages: `Underwriter Chat` for persistent conversations in chatbot.db and `Document Insights` to upload files and get underwriting-focused analysis."
)
