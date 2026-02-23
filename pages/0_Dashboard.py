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
col1.metric("Total Ultimate Premium", f"${kpis['total_premium']:,.0f}")
col2.metric("Total Incurred Loss", f"${kpis['total_incurred']:,.0f}")
col3.metric("Avg Loss Ratio", f"{kpis['avg_loss_ratio'] * 100:.2f}%")
col4.metric("Avg IBNR", f"${kpis['avg_ibnr']:,.0f}")

left, right = st.columns([1.1, 1])
with left:
    st.markdown("#### Exposure Year Trend")
    trend_df = fetch_recent_trend()
    if not trend_df.empty:
        st.line_chart(trend_df.set_index("exposure_year")[["incurred_loss", "ultimate_premium"]])

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
