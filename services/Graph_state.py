from __future__ import annotations

from typing import Any

import pandas as pd
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    user_prompt: str

    # Uploaded document
    uploaded_file1: Any
    uploaded_file1_name: str | None
    uploaded_file1_path: str | None
    uploaded_file1_is_excel: bool
    uploaded_file1_is_docx: bool
    uploaded_file2: Any
    uploaded_file2_name: str | None
    uploaded_file2_path: str | None
    uploaded_file2_is_excel: bool
    uploaded_file2_is_docx: bool

    # Routing
    route: str | None
    vanna_prompt: str | None
    fuzzy_prompt: str | None

    # SQL/search results
    sql_result: pd.DataFrame | None
    sql_query: str | None
    web_links: list | None

    # Summaries
    chart_info: dict | None
    comparison_summary: str | None
    general_summary: str | None
    document_compare_preview_1: pd.DataFrame | None
    document_compare_preview_2: pd.DataFrame | None
    document_compare_name_1: str | None
    document_compare_name_2: str | None

    # FAISS
    faiss_summary: str | None
    faiss_sources: list | None
    faiss_images: list | None

    # Intranet
    intranet_summary: str | None
    intranet_sources: list | None
    intranet_doc_links: list | None
    intranet_doc_count: int | None

