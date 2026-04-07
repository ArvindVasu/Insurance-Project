from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.patches import Patch

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
col3.metric("Avg Incurred Loss Ratio", f"{kpis['avg_loss_ratio'] * 100:.2f}%")
col4.metric("Avg Claims Frequency", f"{kpis['avg_claims_frequency']:.2f}")

left, right = st.columns([1.1, 1])
with left:
    st.markdown("#### Line of Business Trend (USD mn)")
    trend_df = fetch_recent_trend()
    if not trend_df.empty:
        chart_df = trend_df.copy()
        chart_df["incurred_loss"] = chart_df["incurred_loss"].astype(float) / 1_000_000
        chart_df["ultimate_premium"] = chart_df["ultimate_premium"].astype(float) / 1_000_000

        all_values = list(chart_df["incurred_loss"]) + list(chart_df["ultimate_premium"])
        y_min = min(all_values)
        y_max = max(all_values)
        spread = y_max - y_min
        padding = max(spread * 0.12, 50.0)
        domain_min = max(0.0, y_min - padding)
        domain_max = y_max + padding if spread > 0 else y_max + 100.0

        positions = list(range(len(chart_df)))
        width = 0.36

        fig_left, ax_left = plt.subplots(figsize=(7.2, 4.2))
        fig_left.patch.set_facecolor("#f4f7fb")
        ax_left.set_facecolor("#f4f7fb")

        incurred_bars = ax_left.bar(
            [p - width / 2 for p in positions],
            chart_df["incurred_loss"],
            width=width,
            color="#0f766e",
            label="Incurred Loss",
        )
        premium_bars = ax_left.bar(
            [p + width / 2 for p in positions],
            chart_df["ultimate_premium"],
            width=width,
            color="#1d4ed8",
            label="Ultimate Premium",
        )

        ax_left.set_ylim(domain_min, domain_max)
        ax_left.set_ylabel("USD mn")
        ax_left.set_xticks(positions)
        ax_left.set_xticklabels(chart_df["line_of_business"], rotation=22, ha="right")
        ax_left.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
        ax_left.set_axisbelow(True)
        ax_left.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, frameon=False)

        label_offset = max(spread * 0.02, 8.0)
        for bars in [incurred_bars, premium_bars]:
            for bar in bars:
                height = bar.get_height()
                ax_left.text(
                    bar.get_x() + bar.get_width() / 2,
                    height + label_offset,
                    f"{height:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#0f3d75",
                )

        for spine in ["top", "right"]:
            ax_left.spines[spine].set_visible(False)
        ax_left.spines["left"].set_color("#9fb3c8")
        ax_left.spines["bottom"].set_color("#9fb3c8")
        ax_left.tick_params(axis="x", labelsize=9)
        ax_left.tick_params(axis="y", labelsize=9)
        fig_left.subplots_adjust(left=0.10, right=0.98, top=0.95, bottom=0.28)

        st.pyplot(fig_left, use_container_width=True)
        plt.close(fig_left)
        st.caption("Y-axis is tightened to make line-of-business movement easier to compare while keeping both series on the same scale.")

with right:
    st.markdown("#### LOB Incurred Loss Ratio")
    lob_df = fetch_lob_loss_ratio()
    if not lob_df.empty:
        chart_df = lob_df[["reserve_class", "avg_loss_ratio"]].copy()
        ratio_series = chart_df["avg_loss_ratio"].astype(float)
        is_decimal_ratio = ratio_series.dropna().abs().median() <= 1.5 if not ratio_series.dropna().empty else False
        if is_decimal_ratio:
            chart_df["avg_loss_ratio"] = chart_df["avg_loss_ratio"] * 100.0

        y_min = float(chart_df["avg_loss_ratio"].min())
        y_max = float(chart_df["avg_loss_ratio"].max())
        spread = y_max - y_min
        padding = max(spread * 0.12, 0.25)
        domain_min = max(0.0, y_min - padding)
        domain_max = y_max + padding if spread > 0 else y_max + 0.5
        palette = ["#0f766e", "#1d4ed8", "#f59e0b", "#ef4444", "#7c3aed", "#0891b2"]
        colors = [palette[i % len(palette)] for i in range(len(chart_df))]

        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        fig.patch.set_facecolor("#f4f7fb")
        ax.set_facecolor("#f4f7fb")
        bars = ax.barh(chart_df["reserve_class"], chart_df["avg_loss_ratio"], color=colors, height=0.56)
        ax.invert_yaxis()
        ax.set_xlim(domain_min, domain_max)
        ax.set_xlabel("Incurred Loss Ratio (%)")
        ax.set_ylabel("")
        ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.35)
        ax.set_axisbelow(True)

        for bar, value in zip(bars, chart_df["avg_loss_ratio"]):
            ax.text(
                bar.get_width() + max(spread * 0.03, 0.05),
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                va="center",
                ha="left",
                fontsize=9,
                color="#0f3d75",
                fontweight="bold",
            )

        legend_handles = [
            Patch(facecolor=color, edgecolor=color, label=label)
            for color, label in zip(colors, chart_df["reserve_class"])
        ]
        ax.legend(
            handles=legend_handles,
            title="Line of Business",
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=2,
            frameon=False,
            fontsize=8,
            title_fontsize=9,
        )

        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#9fb3c8")
        ax.tick_params(axis="y", labelsize=9)
        ax.tick_params(axis="x", labelsize=9)
        fig.subplots_adjust(left=0.34, right=0.97, top=0.95, bottom=0.30)

        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.caption("Chart uses a tightened ratio scale with direct labels so small LOB differences are easier to compare.")

st.markdown("### Workspace")
st.info(
    "Use the left sidebar pages: `Underwriter Chat` for persistent conversations in chatbot.db and `Document Insights` to upload files and get underwriting-focused analysis."
)
