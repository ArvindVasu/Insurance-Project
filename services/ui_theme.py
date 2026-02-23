from __future__ import annotations

import os
import streamlit as st
from services.auth_service import logout_user


def _hydrate_env_from_streamlit_secrets() -> None:
    """Mirror st.secrets into environment variables for existing os.getenv(...) usage."""
    try:
        for key in st.secrets.keys():
            val = st.secrets.get(key)
            if isinstance(val, str) and key not in os.environ:
                os.environ[key] = val
    except Exception:
        # st.secrets may be unavailable in some local runs.
        pass


_hydrate_env_from_streamlit_secrets()

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Sans+3:wght@400;600&display=swap');

:root {
  --bg: #f4f7fb;
  --panel: #ffffff;
  --ink: #1f2a44;
  --accent: #0f766e;
  --accent-soft: #d8f3ef;
  --muted: #6b7280;
  --border: #dbe3ef;
}

html, body, [data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 5% 5%, #eef8ff 0%, var(--bg) 45%, #eff5ff 100%);
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff 0%, #f2f7ff 100%);
  border-right: 1px solid var(--border);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.35rem 0.2rem 0.6rem 0.2rem;
  margin-bottom: 0.4rem;
  border-bottom: 1px solid #d9e5f6;
}

.sidebar-brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 18px;
  box-shadow: 0 6px 14px rgba(29, 78, 216, 0.25);
}

.sidebar-brand-text {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #12335f;
  letter-spacing: 0.4px;
}

.top-nav {
  background: linear-gradient(180deg, #163863 0%, #1b416f 100%);
  border: 1px solid #275381;
  border-radius: 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  color: #e9f2ff;
}

.top-nav-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #3f6496;
  border-radius: 999px;
  padding: 6px 12px;
  font-weight: 700;
  color: #f2f7ff;
  background: rgba(10, 28, 52, 0.6);
  white-space: nowrap;
}

/* Prevent material icon token text from showing near popovers */
[data-testid="stPopover"] button span.material-symbols-rounded,
[data-testid="stPopover"] button span.material-icons {
  display: none !important;
}

[data-testid="stSidebarNav"] {
  padding-top: 0.15rem;
}

[data-testid="stSidebarNav"]::before {
  content: "🤖  ASTRA";
  display: block;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #12335f;
  letter-spacing: 0.4px;
  padding: 0.2rem 0.3rem 0.65rem 0.3rem;
  margin-bottom: 0.35rem;
  border-bottom: 1px solid #d9e5f6;
}

[data-testid="stSidebarNav"] ul {
  gap: 0.2rem;
}

[data-testid="stSidebarNav"] ul li a {
  border-radius: 10px;
  padding: 0.5rem 0.6rem;
  border: 1px solid transparent;
  color: #2a3b5f;
  font-weight: 600;
  transition: all 0.2s ease;
}

[data-testid="stSidebarNav"] ul li a:hover {
  background: #eaf2ff;
  border-color: #d0def5;
}

[data-testid="stSidebarNav"] ul li a[aria-current="page"] {
  background: linear-gradient(90deg, #dff4ef 0%, #eef8ff 100%);
  border-color: #b8ddd3;
  color: #11483f;
  box-shadow: inset 3px 0 0 #0f766e;
}

/* Menu icons (based on page order) */
[data-testid="stSidebarNav"] ul li:nth-child(1) a::before {
  content: "🏠  ";
}
[data-testid="stSidebarNav"] ul li:nth-child(2) a::before {
  content: "📄  ";
}
[data-testid="stSidebarNav"] ul li:nth-child(3) a::before {
  content: "💬  ";
}
[data-testid="stSidebarNav"] ul li:nth-child(4) a::before {
  content: "🧾  ";
}
[data-testid="stSidebarNav"] ul li:nth-child(5) a::before {
  content: "📊  ";
}
[data-testid="stSidebarNav"] ul li:nth-child(6) a::before {
  content: "\\1F4C4  ";
}

h1, h2, h3 {
  font-family: 'Space Grotesk', sans-serif !important;
  color: var(--ink);
  letter-spacing: -0.3px;
}

p, label, input, textarea, button {
  font-family: 'Source Sans 3', sans-serif !important;
}

/* Keep Streamlit/Material icons rendered as icons, not text names */
.material-symbols-rounded,
.material-icons,
[class*="material-symbols"] {
  font-family: "Material Symbols Rounded", "Material Icons" !important;
}

.hero-card {
  background: linear-gradient(135deg, #083a55 0%, #0f766e 60%, #14b8a6 100%);
  border-radius: 18px;
  padding: 1.3rem;
  color: #f8fafc;
  border: 1px solid #0f6276;
  box-shadow: 0 14px 32px rgba(8, 58, 85, 0.2);
  animation: fadeInUp 0.5s ease;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.9rem 1rem;
  box-shadow: 0 8px 20px rgba(20, 32, 58, 0.05);
}

[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.4rem;
}

.stChatMessage {
  border-radius: 12px;
  border: 1px solid var(--border);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
"""


def apply_theme(page_title: str, icon: str = ":bar_chart:") -> None:
    st.set_page_config(page_title=page_title, page_icon=icon, layout="wide")
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <h2 style="margin-bottom:0.2rem; color:#f8fafc;">{title}</h2>
            <p style="margin:0; color:#dcfce7;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav(show_search: bool = False) -> None:
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)
    nav_left, nav_mid, nav_right = st.columns([4.6, 0.8, 0.8])
    with nav_left:
        if show_search:
            st.text_input(
                "Search",
                placeholder="Search cases, policies, brokers...",
                label_visibility="collapsed",
                key="global_top_nav_search",
            )
        else:
            st.markdown("&nbsp;", unsafe_allow_html=True)
    with nav_mid:
        st.markdown("<div class='top-nav-chip'>Alert 2</div>", unsafe_allow_html=True)
    with nav_right:
        with st.popover("User Profile", use_container_width=True):
            user_email = st.session_state.get("user_email") or st.session_state.get("email") or "Not logged in"
            st.markdown("### User Profile")
            st.write("Name: Divyanshu Underwriter")
            st.write("Role: Senior Underwriter")
            st.write("Team: Commercial Lines")
            st.write(f"Email: {user_email}")
            if st.button("Sign Out", type="primary", use_container_width=True, key="global_signout"):
                logout_user()
                st.switch_page("app.py")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


