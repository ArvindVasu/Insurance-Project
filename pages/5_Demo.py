from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from services.auth_service import require_auth
from services.ui_theme import apply_theme, render_hero, render_top_nav

require_auth()
apply_theme("Demo", icon=":clapper:")
render_top_nav(show_search=False)
render_hero(
    "Product Demo Library",
    "Watch workflow demos for each product capability and expand this library by dropping more videos into the Demo folder.",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "Demo"
METADATA_PATH = DEMO_DIR / "videos.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mpeg", ".mpg"}
DEFAULT_DEMO_FILE = "Product_Demo.mp4"


def _humanize_name(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def _default_demo_description(title: str) -> str:
    normalized = " ".join(str(title or "").lower().split())

    if "product demo" in normalized:
        return (
            "Overview of the ASTRA platform and how the main underwriting workflows connect across the product. "
            "Use this demo to understand the end-to-end user journey."
        )
    if "dashboard" in normalized:
        return (
            "Shows how the Dashboard surfaces portfolio KPIs, line-of-business trends, and loss-ratio signals for underwriters. "
            "Use it to monitor book performance and spot movement quickly."
        )
    if "document insight" in normalized:
        return (
            "Demonstrates how Document Insights analyzes uploaded files and extracts underwriting-relevant summaries, gaps, and changes. "
            "Use it for submission review and document comparison workflows."
        )
    if "underwriter chat" in normalized:
        return (
            "The Underwriter Chat is an AI-powered assistant that answers underwriting queries by intelligently routing them to internal data, external sources, or company guidelines. "
            "It delivers transparent, auditable insights—combining analytics, market intelligence, and compliance in one place."
        )
    if "eoi" in normalized or "expression of interest" in normalized:
        return (
            "Shows how the EOI workflow combines broker submission analysis, internal benchmarking, and external signals to create a decision-ready output. "
            "Use it to generate a scored underwriting recommendation and final EOI document."
        )
    if "portfolio" in normalized:
        return (
            "Highlights portfolio-level analytics used to compare performance across classes, brokers, and underwriting segments. "
            "Use it to review concentration and trend behavior."
        )

    return (
        f"Demonstrates the {title} workflow within ASTRA and highlights the main user actions available on that page. "
        "Use it as a quick walkthrough of the feature."
    )


def _load_metadata() -> dict[str, dict]:
    if not METADATA_PATH.exists():
        return {}
    try:
        raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if isinstance(raw, list):
        items = {}
        for entry in raw:
            if isinstance(entry, dict) and entry.get("file"):
                items[str(entry["file"])] = entry
        return items
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items() if isinstance(v, dict)}
    return {}


def _discover_videos() -> list[dict]:
    metadata = _load_metadata()
    videos: list[dict] = []
    if not DEMO_DIR.exists():
        return videos

    for path in sorted(DEMO_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        meta = metadata.get(path.name, {})
        title = str(meta.get("title") or _humanize_name(path.stem))
        description = str(
            meta.get("description")
            or _default_demo_description(title)
        )
        tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
        videos.append(
            {
                "path": path,
                "file": path.name,
                "title": title,
                "description": description,
                "tags": [str(tag) for tag in tags],
                "size": _format_size(path.stat().st_size),
            }
        )
    return videos


def _preferred_demo_file(videos: list[dict]) -> str | None:
    if not videos:
        return None
    preferred = next((video["file"] for video in videos if video["file"].lower() == DEFAULT_DEMO_FILE.lower()), None)
    return preferred or videos[0]["file"]


def _render_thumbnail_card(video: dict, selected: bool) -> str:
    selected_class = " demo-info-card-selected" if selected else ""
    chips = "".join(f'<span class="demo-chip">{tag}</span>' for tag in video["tags"][:3])
    return f"""
<div class="demo-info-card demo-thumb-card{selected_class}">
  <div class="demo-thumb-visual">
    <div class="demo-thumb-kicker">ASTRA DEMO</div>
    <div class="demo-thumb-title">{video["title"]}</div>
  </div>
  <div class="demo-meta">File: {video["file"]} | Size: {video["size"]}</div>
  <p style="margin:0 0 10px 0;">{video["description"]}</p>
  {chips}
</div>
"""


st.markdown(
    """
    <style>
    .demo-info-card {
      background: linear-gradient(180deg, #ffffff 0%, #f5f9ff 100%);
      border: 1px solid #d7e4f5;
      border-radius: 16px;
      padding: 16px 18px;
      box-shadow: 0 10px 22px rgba(18, 42, 76, 0.08);
      margin-bottom: 12px;
    }
    .demo-info-card-selected {
      border: 2px solid #0f766e;
      box-shadow: 0 12px 28px rgba(15, 118, 110, 0.16);
    }
    .demo-meta {
      color: #5f7493;
      font-size: 14px;
      margin-bottom: 8px;
    }
    .demo-chip {
      display: inline-block;
      background: #e7f2ff;
      color: #0f3d75;
      border: 1px solid #cfe0f5;
      border-radius: 999px;
      padding: 4px 10px;
      margin: 0 6px 6px 0;
      font-size: 12px;
      font-weight: 700;
    }
    .demo-thumb-card {
      min-height: 236px;
    }
    .demo-thumb-visual {
      background: linear-gradient(135deg, #103b67 0%, #0f766e 55%, #14b8a6 100%);
      border-radius: 14px;
      min-height: 128px;
      padding: 14px;
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
    }
    .demo-thumb-kicker {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 1.2px;
      color: #d9f7ff;
    }
    .demo-thumb-title {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 24px;
      line-height: 1.1;
      font-weight: 700;
      color: #ffffff;
      max-width: 85%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

videos = _discover_videos()

if not videos:
    st.warning("No demo videos found in `Insurance-Project/Demo`.")
    st.info(
        "Add `.mp4`, `.mov`, `.webm`, `.m4v`, or similar video files to the `Demo` folder. "
        "Optional metadata can be added later through `Demo/videos.json`."
    )
    st.stop()

preferred_demo_file = _preferred_demo_file(videos)

if "demo_selected_file" not in st.session_state:
    st.session_state.demo_selected_file = preferred_demo_file

available_files = {video["file"] for video in videos}
if st.session_state.demo_selected_file not in available_files:
    st.session_state.demo_selected_file = preferred_demo_file

st.markdown("### Choose A Demo")
thumb_cols = st.columns(2)
for idx, video in enumerate(videos):
    is_selected = st.session_state.demo_selected_file == video["file"]
    with thumb_cols[idx % 2]:
        st.markdown(_render_thumbnail_card(video, is_selected), unsafe_allow_html=True)
        button_label = "Now Playing" if is_selected else "Watch Demo"
        if st.button(button_label, key=f"demo_select_{video['file']}", use_container_width=True):
            st.session_state.demo_selected_file = video["file"]
            st.rerun()

selected_video = next(video for video in videos if video["file"] == st.session_state.demo_selected_file)

left_col, right_col = st.columns([2.1, 1])
with left_col:
    st.markdown("### Now Playing")
    st.video(selected_video["path"].read_bytes())

with right_col:
    chips = "".join(f'<span class="demo-chip">{tag}</span>' for tag in selected_video["tags"])
    st.markdown(
        f"""
<div class="demo-info-card">
  <h3 style="margin:0 0 6px 0;">{selected_video["title"]}</h3>
  <div class="demo-meta">File: {selected_video["file"]}<br>Size: {selected_video["size"]}</div>
  <p style="margin:0 0 10px 0;">{selected_video["description"]}</p>
  {chips}
</div>
""",
        unsafe_allow_html=True,
    )
    # st.info(
    #     "To add more demo entries later, drop additional video files into `Insurance-Project/Demo`. "
    #     "If you want custom titles, descriptions, or tags, create `Insurance-Project/Demo/videos.json`."
    # )
