from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from services.auth_service import require_auth
from services.ui_theme import apply_theme, render_hero, render_top_nav

require_auth()
apply_theme("Portfolio Analytics", icon=":chart_with_upwards_trend:")
render_top_nav(show_search=True)

st.markdown(
    """
    <style>
    .pa-panel {
      background: linear-gradient(180deg, #1b3357 0%, #192f4f 100%);
      border: 1px solid #2c4b76;
      border-radius: 14px;
      padding: 14px 16px;
      margin-top: 8px;
      color: #dce9ff;
    }

    .pa-subhead {
      color: #f2f7ff;
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .loss-row { margin: 13px 0; }
    .loss-label {
      width: 185px;
      display: inline-block;
      color: #000000;
      font-weight: 700;
      font-size: 14px;
    }
    .loss-bar-wrap {
      width: calc(100% - 220px);
      background: #0f1d36;
      border: 1px solid #345986;
      border-radius: 9px;
      display: inline-block;
      height: 32px;
      vertical-align: middle;
      margin-right: 8px;
    }
    .loss-bar {
      height: 100%;
      border-radius: 8px;
    }
    .loss-value {
      color: #ebf3ff;
      font-weight: 700;
      font-size: 14px;
    }

    .heat-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 8px;
    }

    .heat-card {
      border-radius: 12px;
      border: 1px solid transparent;
      padding: 14px 16px;
      min-height: 94px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 8px 18px rgba(7, 18, 35, 0.35);
    }

    .high { background: rgba(193, 54, 81, 0.55); border-color: #ce4b67; }
    .medium { background: rgba(182, 139, 49, 0.55); border-color: #d3aa49; }
    .low { background: rgba(34, 163, 133, 0.5); border-color: #33b192; }

    .heat-region { color: #ffffff; font-weight: 800; }
    .heat-value { color: #ffffff; font-size: 28px; font-weight: 800; line-height: 1.1; }
    .heat-level { color: #eef5ff; font-size: 12px; font-weight: 800; letter-spacing: 0.4px; }

    .badge-line {
      display: flex;
      gap: 12px;
      margin-top: 10px;
      color: #ffffff;
      font-size: 13px;
      font-weight: 700;
    }

    .badge-item {
      display: inline-flex;
      align-items: center;
      background: rgba(7, 18, 35, 0.65);
      border: 1px solid #3a5f8e;
      border-radius: 999px;
      padding: 4px 10px;
    }

    .dot {
      width: 11px;
      height: 11px;
      border-radius: 99px;
      display: inline-block;
      margin-right: 6px;
    }

    .table-wrap {
      border: 1px solid #365782;
      border-radius: 12px;
      overflow: hidden;
      background: #152d4d;
      margin-top: 8px;
    }

    table.portfolio-table {
      width: 100%;
      border-collapse: collapse;
      color: #e2ecff;
      font-size: 15px;
    }

    table.portfolio-table th {
      text-align: left;
      background: #18375f;
      color: #b7caea;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.5px;
      padding: 12px 16px;
      border-bottom: 1px solid #31537d;
    }

    table.portfolio-table td {
      padding: 14px 16px;
      border-bottom: 1px solid #2b4b74;
      font-weight: 600;
    }

    .warn { color: #f6cb4a; font-weight: 700; }
    .good { color: #30d39a; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

render_hero("Portfolio Analytics", "Portfolio performance and exposure analysis")

left, right = st.columns(2)

with left:
    st.markdown('<div class="pa-panel">', unsafe_allow_html=True)
    st.markdown('<div class="pa-subhead">Loss Ratio by Line</div>', unsafe_allow_html=True)

    loss_rows = [
        ("Commercial Property", 65, "#4285f4"),
        ("General Liability", 55, "#2bc15e"),
        ("Workers Comp", 70, "#f6a90c"),
        ("Commercial Auto", 80, "#ef4444"),
        ("Umbrella / Excess", 45, "#7c5cf6"),
    ]

    for label, val, color in loss_rows:
        st.markdown(
            f"""
            <div class="loss-row">
              <span class="loss-label">{label}</span>
              <span class="loss-bar-wrap"><span class="loss-bar" style="width:{val}%;background:{color};display:block;"></span></span>
              <span class="loss-value">{val}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="pa-panel">', unsafe_allow_html=True)
    st.markdown('<div class="pa-subhead">Exposure Heatmap</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="heat-grid">
          <div class="heat-card high"><div class="heat-region">Northeast</div><div class="heat-value">$35M</div><div class="heat-level">HIGH EXPOSURE</div></div>
          <div class="heat-card medium"><div class="heat-region">Southeast</div><div class="heat-value">$28M</div><div class="heat-level">MEDIUM EXPOSURE</div></div>
          <div class="heat-card high"><div class="heat-region">Midwest</div><div class="heat-value">$42M</div><div class="heat-level">HIGH EXPOSURE</div></div>
          <div class="heat-card low"><div class="heat-region">Southwest</div><div class="heat-value">$18M</div><div class="heat-level">LOW EXPOSURE</div></div>
          <div class="heat-card medium"><div class="heat-region">West</div><div class="heat-value">$22M</div><div class="heat-level">MEDIUM EXPOSURE</div></div>
        </div>
        <div class="badge-line">
          <span class="badge-item"><span class="dot" style="background:#1fa184"></span>Low</span>
          <span class="badge-item"><span class="dot" style="background:#aa8233"></span>Medium</span>
          <span class="badge-item"><span class="dot" style="background:#99384f"></span>High</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="pa-panel">', unsafe_allow_html=True)
st.markdown('<div class="pa-subhead">Broker Performance</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="table-wrap">
      <table class="portfolio-table">
        <thead>
          <tr>
            <th>BROKER</th>
            <th>POLICIES</th>
            <th>PREMIUM</th>
            <th>LOSS RATIO</th>
            <th>RETENTION</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Marsh &amp; McLennan</td>
            <td>45</td>
            <td>$18.5M</td>
            <td><span class="warn">58%</span></td>
            <td><span class="good">92%</span></td>
          </tr>
          <tr>
            <td>Aon Risk Solutions</td>
            <td>38</td>
            <td>$15.2M</td>
            <td><span class="warn">62%</span></td>
            <td><span class="good">88%</span></td>
          </tr>
          <tr>
            <td>Willis Towers Watson</td>
            <td>31</td>
            <td>$12.9M</td>
            <td><span class="warn">55%</span></td>
            <td><span class="good">90%</span></td>
          </tr>
        </tbody>
      </table>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="pa-panel">', unsafe_allow_html=True)
st.markdown('<div class="pa-subhead">Approval Trend</div>', unsafe_allow_html=True)

trend_df = pd.DataFrame(
    {
        "month": ["May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
        "approved": [62, 74, 89, 84, 97, 108, 121],
        "declined": [18, 17, 19, 21, 20, 18, 16],
    }
)

chart_data = trend_df.melt("month", var_name="status", value_name="count")

chart = (
    alt.Chart(chart_data)
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("month:N", axis=alt.Axis(labelColor="#0b0d0f", title=None)),
        y=alt.Y("count:Q", axis=alt.Axis(labelColor="#0b0d0f", title=None, gridColor="#2c4b76")),
        color=alt.Color(
            "status:N",
            scale=alt.Scale(domain=["approved", "declined"], range=["#31d39b", "#f79b47"]),
            legend=alt.Legend(title=None, labelColor="#0D0314"),
        ),
        tooltip=["month", "status", "count"],
    )
    .properties(height=280)
    .configure_view(stroke="#2c4b76", fill="#152d4d")
)

st.altair_chart(chart, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)
