from __future__ import annotations

import streamlit as st

from services.auth_service import (
    authenticate_user,
    create_user,
    init_users_db,
    is_authenticated,
)
from services.ui_theme import apply_theme, render_hero, render_top_nav

apply_theme("ASTRA Home", icon=":shield:")
init_users_db()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not is_authenticated():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .auth-shell {
          margin-top: 8px;
        }
        .auth-info-card {
          background: linear-gradient(155deg, #0f2e50 0%, #184a78 55%, #0f766e 100%);
          border: 1px solid #2a5d8b;
          border-radius: 18px;
          padding: 24px;
          color: #ecf5ff;
          min-height: 460px;
          box-shadow: 0 12px 28px rgba(10, 35, 64, 0.28);
        }
        .auth-brand {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 30px;
          font-weight: 700;
          letter-spacing: 0.6px;
          margin-bottom: 6px;
        }
        .auth-sub {
          color: #d8e9ff;
          margin-bottom: 18px;
          font-size: 15px;
        }
        .auth-bullet {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 12px;
          padding: 10px 12px;
          margin-bottom: 10px;
          font-size: 14px;
        }
        .auth-panel {
          background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
          border: 1px solid #d6e4f5;
          border-radius: 18px;
          padding: 18px 18px 10px 18px;
          box-shadow: 0 10px 22px rgba(15, 43, 76, 0.08);
        }
        .auth-panel h3 {
          margin: 0 0 6px 0;
          color: #153a64;
        }
        .auth-panel p {
          margin: 0 0 12px 0;
          color: #5f7493;
        }
        .auth-panel [data-testid="stForm"] {
          border: 0;
          padding: 0;
          background: transparent;
        }
        .auth-panel [data-testid="stTextInput"] input {
          border-radius: 10px !important;
          border: 1.6px solid #bfd3ea !important;
          background: #ffffff !important;
        }
        .auth-panel [data-testid="stTextInput"] input:focus {
          border-color: #0f766e !important;
          box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    left, right = st.columns([1.15, 1])

    with left:
        st.markdown(
            """
            <div class="auth-info-card">
              <div class="auth-brand">ASTRA</div>
              <div class="auth-sub">Underwriting Intelligence Platform</div>
              <div class="auth-bullet"><strong>Secure Access</strong><br/>Email-based authentication with user-scoped chat history.</div>
              <div class="auth-bullet"><strong>Unified Workspace</strong><br/>Portfolio analytics, document insights, and routed underwriter chat.</div>
              <div class="auth-bullet"><strong>Operational Focus</strong><br/>Built for daily underwriting workflows and decision support.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="auth-panel">
              <h3>Welcome Back</h3>
              <p>Sign in to continue, or create a new account.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

        with login_tab:
            with st.form("login_form"):
                login_email = st.text_input("Email", placeholder="name@company.com")
                login_password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            if login_submitted:
                ok, result = authenticate_user(login_email, login_password)
                if ok:
                    st.session_state["authenticated"] = True
                    st.session_state["user_email"] = result
                    st.session_state["email"] = result
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error(result)

        with signup_tab:
            with st.form("signup_form"):
                signup_email = st.text_input("Email", placeholder="name@company.com")
                signup_password = st.text_input("Password", type="password")
                signup_submitted = st.form_submit_button("Create Account", use_container_width=True)
            if signup_submitted:
                ok, message = create_user(signup_email, signup_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)

    st.markdown("</div>", unsafe_allow_html=True)
else:
    render_top_nav(show_search=False)

    render_hero(
        "ASTRA Underwriting Home",
        "Unified workspace for day-to-day underwriting decisions, portfolio monitoring, and document intelligence.",
    )

    st.markdown("### Brief Description")
    st.markdown(
        """
ASTRA is designed as an operational home page for underwriters.
Use it to analyze portfolio performance, review submissions, run guided AI queries, and make faster decisions with consistent risk context.
"""
    )

    st.markdown("### What You Can Do Here")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
<div class="panel">
  <h4 style="margin:0 0 6px 0;">Daily Underwriting Workflow</h4>
  <p style="margin:0;">
  1. Review portfolio signals and exposure trends<br>
  2. Inspect policy/submission documents<br>
  3. Ask routed underwriting questions via chat<br>
  4. Compare internal vs external benchmark insights
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
<div class="panel">
  <h4 style="margin:0 0 6px 0;">Core Workspaces</h4>
  <p style="margin:0;">
  • Dashboard: KPI snapshot and trend monitoring<br>
  • Document Insights: upload and analyze submissions<br>
  • Underwriter Chat: routed agentic Q&A<br>
  • Portfolio Analytics: exposure and broker performance view
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("### Navigation")
    st.info(
        "Use the left sidebar to open each workspace. Start with `Dashboard` for portfolio health, then move to `Document Insights` and `Underwriter Chat` for case-level actions."
    )
