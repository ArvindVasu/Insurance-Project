from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader

from services.Common_Functions import prune_state
from services.Graph_state import GraphState
from services.llm_service import call_llm

STATE_KEYS_SET_AT_ENTRY = []


def _extract_docx_text(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n".join(pages)


def _load_document(path: str, is_excel: bool, is_docx: bool):
    ext = Path(path).suffix.lower()

    if is_excel or ext in {".xlsx", ".xls", ".csv"}:
        if ext == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        preview = df.head(25)
        table_context = preview.to_markdown(index=False)
        summary = (
            f"Document type: tabular\n"
            f"Rows: {len(df)}\n"
            f"Columns: {', '.join(df.columns.astype(str).tolist())}\n"
            f"Preview:\n{table_context}"
        )
        return summary, preview

    if is_docx or ext == ".docx":
        return _extract_docx_text(path), None

    if ext == ".pdf":
        return _extract_pdf_text(path), None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(), None


def document_node(state: GraphState) -> GraphState:
    file_path = state.get("uploaded_file1_path")
    if not file_path or not os.path.exists(file_path):
        return {
            **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
            "route": "document",
            "general_summary": "No document uploaded. Please attach a file to analyze.",
            "sql_result": None,
        }

    try:
        document_text, preview_df = _load_document(
            file_path,
            bool(state.get("uploaded_file1_is_excel")),
            bool(state.get("uploaded_file1_is_docx")),
        )
    except Exception as exc:
        return {
            **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
            "route": "document",
            "general_summary": f"Failed to read document: {exc}",
            "sql_result": None,
        }

    context = document_text[:12000]
    insight_prompt = f"""
You are an underwriting document analyst.

User question:
{state.get('user_prompt', '')}

Document content (possibly truncated):
{context}

Provide:
1) A concise answer to the user question.
2) Risk considerations and underwriting implications.
3) Missing information the underwriter should ask for next.
"""

    analysis = call_llm(insight_prompt)

    return {
        **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
        "route": "document",
        "general_summary": analysis,
        "sql_result": preview_df,
    }

