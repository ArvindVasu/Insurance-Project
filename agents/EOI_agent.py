# Summarize the attached broker submission document and fetch the internal loss history, web insights for international casualty lines

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from pypdf import PdfReader

from agents.document_agent import document_node
from agents.intranet_agent import intranet_node
from agents.vanna_agent import vanna_node
from config.global_variables import DB_PATH
from services.Common_Functions import get_schema_description
from services.Graph_state import GraphState
from services.llm_service import call_llm
from services.vanna_service import vanna_configure

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EOI_TEMPLATE_PATH = PROJECT_ROOT / "Doc" / "Insurance_EOI_Form.docx"
CHECKED_BOX = "\u2611"
UNCHECKED_BOX = "\u2610"

FIELD_LABELS = {
    "registered_address": "Registered Address",
    "city": "City",
    "state": "State",
    "country": "Country",
    "postal_code": "Postal Code",
    "phone_number": "Phone Number",
    "email_address": "Email Address",
    "website": "Website (if applicable)",
    "expected_sum_insured": "Expected Sum Insured / Coverage Amount",
    "pan_tax_id": "PAN / Tax ID / Business ID",
    "gst_number": "GST Number (if applicable)",
    "regulatory_licenses": "Regulatory Licenses / Certifications",
    "claims_history": "Claims History (last 3–5 years)",
}

FIELD_MAX_LEN = {
    "registered_address": 240,
    "city": 80,
    "state": 80,
    "country": 80,
    "postal_code": 24,
    "phone_number": 40,
    "email_address": 120,
    "website": 180,
    "expected_sum_insured": 80,
    "pan_tax_id": 80,
    "gst_number": 40,
    "regulatory_licenses": 120,
    "claims_history": 260,
}

NOISE_TOKENS = [
    "submission date",
    "client overview",
    "program objective",
    "loss history",
    "coverage requested",
    "value proposition",
    "required deliverables",
    "disclaimer",
    "this submission",
]

DECLARATION_TEXT = (
    "I/We hereby declare that the information provided in this Expression of Interest is true and "
    "accurate to the best of my/our knowledge. Submission of this form does not guarantee acceptance "
    "or issuance of any insurance policy or partnership."
)


def _extract_doc_text(path: str) -> str:
    ext = Path(path).suffix.lower()

    if ext == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _clean_value(value: str | None) -> str:
    if not value:
        return ""
    v = re.sub(r"\s+", " ", value).strip()
    v = v.strip("-_:. ")
    return "" if v.lower() in {"na", "n/a", "not available", "nil", "none"} else v


def _sanitize_field_value(key: str, value: str | None) -> str:
    v = _clean_value(value)
    if not v:
        return ""

    if len(v) > FIELD_MAX_LEN.get(key, 120):
        return ""

    low = v.lower()
    if any(token in low for token in NOISE_TOKENS):
        return ""

    if key == "email_address":
        return v if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", v) else ""

    if key == "phone_number":
        digits = re.sub(r"\D", "", v)
        return v if len(digits) >= 7 else ""

    if key == "website":
        has_domain = re.search(r"(https?://|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,})", v)
        return v if has_domain else ""

    if key in {"city", "state", "country"}:
        if ":" in v or len(v.split()) > 6:
            return ""
        return v

    if key == "postal_code":
        return v if re.search(r"[A-Za-z0-9]", v) else ""

    if key == "expected_sum_insured":
        # Should usually contain currency/number-like content.
        return v if re.search(r"\d", v) else ""

    if key in {"pan_tax_id", "gst_number"}:
        if re.search(r"[.!?].+[.!?]", v):
            return ""
        return v

    return v


def _extract_single_field(text: str, label_pattern: str, stop_labels: list[str]) -> str:
    stop = "|".join(stop_labels)
    pattern = rf"{label_pattern}\s*[:\-]?\s*(.+?)(?=\n\s*(?:{stop})\s*[:\-]|$)"
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        # Inline single-line fallback
        m2 = re.search(rf"{label_pattern}\s*[:\-]?\s*([^\n]+)", text, flags=re.IGNORECASE)
        return _clean_value(m2.group(1)) if m2 else ""
    return _clean_value(m.group(1))


def extract_broker_fields(doc_text: str) -> dict[str, str]:
    stop_labels = [
        r"Registered Address", r"City", r"State", r"Country", r"Postal Code",
        r"Phone Number", r"Email Address", r"Website(?:\s*\(if applicable\))?",
        r"Expected Sum Insured(?:\s*/\s*Coverage Amount)?", r"PAN(?:\s*/\s*Tax ID\s*/\s*Business ID)?",
        r"GST Number(?:\s*\(if applicable\))?", r"Regulatory Licenses(?:\s*/\s*Certifications)?",
    ]

    fields = {
        "registered_address": _extract_single_field(doc_text, r"Registered Address", stop_labels),
        "city": _extract_single_field(doc_text, r"City", stop_labels),
        "state": _extract_single_field(doc_text, r"State", stop_labels),
        "country": _extract_single_field(doc_text, r"Country", stop_labels),
        "postal_code": _extract_single_field(doc_text, r"Postal Code", stop_labels),
        "phone_number": _extract_single_field(doc_text, r"Phone Number", stop_labels),
        "email_address": _extract_single_field(doc_text, r"Email Address", stop_labels),
        "website": _extract_single_field(doc_text, r"Website(?:\s*\(if applicable\))?", stop_labels),
        "expected_sum_insured": _extract_single_field(doc_text, r"Expected Sum Insured(?:\s*/\s*Coverage Amount)?", stop_labels),
        "pan_tax_id": _extract_single_field(doc_text, r"PAN(?:\s*/\s*Tax ID\s*/\s*Business ID)?", stop_labels),
        "gst_number": _extract_single_field(doc_text, r"GST Number(?:\s*\(if applicable\))?", stop_labels),
        "regulatory_licenses": _extract_single_field(doc_text, r"Regulatory Licenses(?:\s*/\s*Certifications)?", stop_labels),
        "claims_history": _extract_single_field(doc_text, r"Claims History(?:\s*\(last\s*3[–-]5\s*years\))?", stop_labels),
    }
    fields = {k: _sanitize_field_value(k, v) for k, v in fields.items()}

    # LLM fallback only for missing fields
    missing = [k for k, v in fields.items() if not v]
    if missing:
        prompt = f"""
Extract the following fields from this broker submission text and return ONLY JSON.
Missing fields to extract: {missing}
Keys allowed: {list(FIELD_LABELS.keys())}
Use empty string if not found.

TEXT:
{doc_text[:12000]}
"""
        llm_raw = call_llm(prompt)
        m = re.search(r"\{.*\}", llm_raw, flags=re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                for k in missing:
                    fields[k] = _sanitize_field_value(k, str(parsed.get(k, "")))
            except Exception:
                pass

    return fields


def summarize_doc_with_instruction(doc_path: str, instruction: str) -> str:
    if not doc_path or not os.path.exists(doc_path):
        return "No document uploaded."

    try:
        content = _extract_doc_text(doc_path)
    except Exception as exc:
        return f"Failed to read document: {exc}"

    prompt = f"""
You are an underwriting analyst.

Instruction:
{instruction}

Submission document:
{content[:12000]}

Provide:
1) A concise summary of the submission.
2) Key underwriting pros and cons.
3) A clear recommendation on whether to proceed, and why.
"""
    return call_llm(prompt).strip()


def build_vanna_prompt(user_prompt: str) -> str:
    reserve_classes = [
        "aviation",
        "property",
        "casualty",
        "marine",
        "motor",
        "energy",
        "financial lines",
    ]

    prompt = user_prompt.lower()
    matched = next((rc for rc in reserve_classes if rc in prompt), None)

    if not matched:
        return "Show ultimate loss for the last 10 years"

    return f"Show ultimate loss for {matched} for the last 10 years"


def build_serp_prompt(user_prompt: str) -> str:
    """
    Build a focused external-search prompt instead of passing the full user text.
    Keeps SERP intent narrow: market/industry insights, not document summarization noise.
    """
    prompt = (user_prompt or "").lower()

    reserve_classes = [
        "aviation",
        "property",
        "casualty",
        "marine",
        "motor",
        "energy",
        "financial lines",
        "construction",
    ]
    matched = next((rc for rc in reserve_classes if rc in prompt), "casualty")

    geography = "global"
    if "international" in prompt:
        geography = "international"
    elif "us" in prompt or "united states" in prompt or "north america" in prompt:
        geography = "north america"
    elif "europe" in prompt:
        geography = "europe"
    elif "asia" in prompt:
        geography = "asia"

    metric = "ultimate losses"
    if "loss ratio" in prompt:
        metric = "loss ratios"
    elif "incurred" in prompt:
        metric = "incurred and ultimate losses"

    return (
        f"Fetch latest {geography} market web insights for {matched} lines, "
        f"with focus on {metric}, pricing trend, claims trend, and underwriting appetite."
    )


def _run_internal_sql(vanna_prompt: str) -> tuple[str | None, pd.DataFrame | None]:
    try:
        vanna_out = vanna_node({"user_prompt": vanna_prompt})
        sql_query = vanna_out.get("sql_query")
        result = vanna_out.get("sql_result")
        if isinstance(result, pd.DataFrame):
            return sql_query, result
        if isinstance(result, list):
            return sql_query, pd.DataFrame(result)
        if result is None:
            return sql_query, pd.DataFrame()
        return sql_query, pd.DataFrame([{"Result": str(result)}])
    except Exception as exc:
        return None, pd.DataFrame([{"Error": f"SQL Execution failed: {exc}"}])


def _run_external_search(prompt: str) -> dict[str, Any]:
    try:
        from agents.serp_agent import serp_node

        out = serp_node({"user_prompt": prompt})
        return {
            "web_links": out.get("web_links") or [],
            "general_summary": out.get("general_summary") or "",
        }
    except Exception as exc:
        return {
            "web_links": [("SERP API request failed (no links available)", str(exc))],
            "general_summary": f"External search failed: {exc}",
        }


def _infer_lob_hint(text: str) -> str | None:
    text_low = (text or "").lower()

    lob_keywords = {
        "Marine": ["marine", "cargo", "vessel", "shipping", "maritime", "hull"],
        "Casualty": ["casualty", "liability", "public liability", "general liability", "third party"],
        "Property": ["property", "fire", "building", "business interruption", "industrial all risk"],
        "Motor": ["motor", "auto", "vehicle", "fleet", "commercial vehicle"],
        "Energy": ["energy", "oil", "gas", "power", "offshore", "onshore", "renewable"],
        "Aviation": ["aviation", "aircraft", "aero", "aerospace", "airline", "airport"],
        "Financial Lines": ["financial lines", "d&o", "directors and officers", "professional indemnity", "cyber"],
        "Construction": ["construction", "contractor", "builders risk", "construction all risk", "erection all risk"],
    }

    best_lob = None
    best_score = 0
    for lob, kws in lob_keywords.items():
        score = sum(1 for kw in kws if kw in text_low)
        if score > best_score:
            best_score = score
            best_lob = lob

    return best_lob if best_score > 0 else None


def _run_intranet_insights(user_prompt: str, doc_insights: str, broker_text: str) -> dict[str, Any]:
    combined = f"{user_prompt}\n{doc_insights}\n{broker_text[:4000]}"
    lob_hint = _infer_lob_hint(combined)
    if not lob_hint:
        return {
            "intranet_summary": "",
            "intranet_sources": [],
            "intranet_doc_links": [],
            "intranet_doc_count": None,
            "intranet_lob": None,
        }

    intranet_prompt = (
        f"{user_prompt}\n"
        f"Line of business: {lob_hint}.\n"
        "Provide relevant underwriting guidelines, business written, and business not written."
    )

    try:
        out = intranet_node({"user_prompt": intranet_prompt})
        return {
            "intranet_summary": out.get("intranet_summary") or "",
            "intranet_sources": out.get("intranet_sources") or [],
            "intranet_doc_links": out.get("intranet_doc_links") or [],
            "intranet_doc_count": out.get("intranet_doc_count"),
            "intranet_lob": out.get("intranet_lob") or lob_hint,
        }
    except BaseException as exc:
        # intranet_node may raise streamlit stop-style exceptions when LOB is missing.
        return {
            "intranet_summary": f"Intranet lookup failed: {exc}",
            "intranet_sources": [],
            "intranet_doc_links": [],
            "intranet_doc_count": None,
            "intranet_lob": lob_hint,
        }


def _fallback_recommendation(
    document_summary: str,
    vanna_summary: str,
    web_summary: str,
    intranet_summary: str,
) -> str:
    combined = "\n".join([document_summary or "", vanna_summary or "", web_summary or "", intranet_summary or ""])
    low = combined.lower()
    negative_markers = [
        "do not write",
        "do not underwrite",
        "not underwrite",
        "decline",
        "excluded",
        "prohibited",
        "unacceptable risk",
    ]
    positive_markers = [
        "acceptable risk",
        "within appetite",
        "can underwrite",
        "write",
        "eligible",
    ]

    neg = sum(1 for m in negative_markers if m in low)
    pos = sum(1 for m in positive_markers if m in low)

    decision = "DO NOT WRITE" if neg >= max(1, pos) else "WRITE"
    if decision == "DO NOT WRITE":
        rationale = "material risk or exclusion indicators are stronger than supportive signals."
    else:
        rationale = "risk appears acceptable subject to normal underwriting controls."

    return (
        f"{decision}: {rationale}\n"
        f"- Internal claim history (Vanna): {_to_short_blurb(vanna_summary or 'No strong internal claim signal available.')}\n"
        f"- External insight (SERP): {_to_short_blurb(web_summary or 'No strong external signal available.')}\n"
        f"- Rules & Guidelines (Intranet): {_to_short_blurb(intranet_summary or 'No clear intranet guideline signal available.')}\n"
        f"- Broker submission (Document): {_to_short_blurb(document_summary or 'No clear broker submission signal available.')}"
    )


def _to_short_blurb(text: str, max_sentences: int = 2, max_chars: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    blurb = " ".join(sentences[:max_sentences]).strip()
    if not blurb:
        blurb = cleaned
    return blurb[:max_chars].rstrip()


def _build_executive_snapshot(
    user_prompt: str,
    doc_insights: str,
    sql_query: str | None,
    sql_result: pd.DataFrame | None,
    web_summary: str,
    web_links: list,
    intranet_summary: str,
) -> dict[str, str]:
    if isinstance(sql_result, pd.DataFrame) and not sql_result.empty:
        sql_context = sql_result.head(6).to_markdown(index=False)
    else:
        sql_context = "No SQL rows returned."

    links_context = "\n".join(
        [f"- {item[0]} | {item[1]}" for item in (web_links or [])[:5] if isinstance(item, (list, tuple)) and len(item) >= 2]
    ) or "No web links."
    web_link_summaries = " ".join(
        [str(item[1]) for item in (web_links or [])[:5] if isinstance(item, (list, tuple)) and len(item) >= 2 and item[1]]
    )
    web_summary_short = _to_short_blurb(web_summary or web_link_summaries or "No external web summary available.")

    prompt = f"""
You are preparing an underwriting executive snapshot.

Return ONLY valid JSON with these keys:
- document_agent_summary
- vanna_agent_summary
- intranet_agent_summary
- final_recommendation

Rules:
- Each *_summary must be 1-2 lines max.
- final_recommendation must:
  1) Start with exactly one decision: "WRITE" or "DO NOT WRITE".
  2) Include concise reasoning from all four sources:
     - Internal claim history (Vanna)
     - External insight (SERP)
     - Rules & Guidelines (Intranet)
     - Broker submission (Document)
  3) Be concise but specific (4-6 short lines).
- Use only evidence provided below.
- Do not use markdown.

USER PROMPT:
{user_prompt}

DOCUMENT AGENT:
{doc_insights}

VANNA AGENT:
SQL Query: {sql_query or "Not available"}
Top rows:
{sql_context}

WEB AGENT:
Summary:
{web_summary}
Top links:
{links_context}

INTRANET AGENT:
{intranet_summary or "No intranet insights available."}
"""

    vanna_short = f"SQL used: {sql_query or 'Not available'}."
    fallback = {
        "document_agent_summary": _to_short_blurb(doc_insights or "No document insight available."),
        "vanna_agent_summary": _to_short_blurb(vanna_short),
        "web_agent_summary": web_summary_short,
        "intranet_agent_summary": _to_short_blurb(intranet_summary or "No intranet policy insight available."),
        "final_recommendation": _fallback_recommendation(
            document_summary=doc_insights,
            vanna_summary=vanna_short,
            web_summary=web_summary_short,
            intranet_summary=intranet_summary,
        ),
    }

    try:
        raw = call_llm(prompt)
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return fallback
        parsed = json.loads(match.group(0))
        for k, v in fallback.items():
            if not parsed.get(k):
                parsed[k] = v
        out = {k: str(parsed.get(k, fallback[k])).strip() for k in fallback}
        # Force web-agent summary to come strictly from SERP output only.
        out["web_agent_summary"] = web_summary_short
        return out
    except Exception:
        return fallback


def _load_template_text(template_path: str) -> str:
    doc = Document(template_path)
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _resolve_template_path(template_path: str | None) -> Path:
    candidates: list[Path] = []
    if template_path:
        candidates.append(Path(template_path))

    env_template = os.getenv("EOI_TEMPLATE_PATH")
    if env_template:
        candidates.append(Path(env_template))

    candidates.append(Path(DEFAULT_EOI_TEMPLATE_PATH))

    resolved_candidates: list[Path] = []
    for candidate in candidates:
        p = candidate.expanduser()
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p = p.resolve()
        resolved_candidates.append(p)
        if p.exists():
            return p

    attempted = resolved_candidates[0] if resolved_candidates else Path(DEFAULT_EOI_TEMPLATE_PATH)
    raise FileNotFoundError(f"EOI template not found: {attempted}")


def _build_filled_form_text(user_prompt: str, eoi_state: dict[str, Any], template_text: str) -> str:
    sql_result = eoi_state.get("sql_result")
    if isinstance(sql_result, pd.DataFrame) and not sql_result.empty:
        sql_context = sql_result.head(12).to_markdown(index=False)
    else:
        sql_context = "No structured internal output available."

    web_links = eoi_state.get("web_links") or []
    web_context = "\n".join([f"- {link} | {summary}" for link, summary in web_links[:5]]) or "No web links."

    doc_insights = eoi_state.get("eoi_doc_insights") or "No document insights available."
    web_summary = eoi_state.get("general_summary") or "No web summary available."
    intranet_summary = eoi_state.get("intranet_summary") or "No intranet policy insights available."
    broker_fields = eoi_state.get("eoi_broker_fields") or {}

    prompt = f"""
You are filling an insurance EOI form.

Use ONLY the evidence below:
1) Broker submission insights
2) Internal SQL insights
3) External web insights
4) Intranet policy and underwriting guideline insights
5) Extracted broker fields (highest priority for matching labels)

If any field is missing, fill it with "Not Provided".
Preserve the exact form structure and section order from TEMPLATE below.

Formatting rules:
- Keep labels exactly as-is.
- Replace blank lines/underscores with values.
- For checkboxes, mark selected options with "\\u2611" and unselected with "\\u2610".
- In "Type of Entity", select exactly one option.
- Return plain text only. No markdown, no explanations.

EXTRACTED BROKER FIELDS (PRIORITY):
{json.dumps(broker_fields, indent=2)}

USER PROMPT:
{user_prompt}

BROKER SUBMISSION INSIGHTS:
{doc_insights}

INTERNAL SQL SUMMARY:
Query: {eoi_state.get('sql_query') or 'Not Provided'}
Top rows:
{sql_context}

EXTERNAL WEB SUMMARY:
{web_summary}

INTRANET POLICY INSIGHTS:
{intranet_summary}

EXTERNAL LINKS:
{web_context}

TEMPLATE:
{template_text}
"""

    return call_llm(prompt).strip()


def _override_field_line(line: str, label: str, value: str) -> str:
    if not value:
        return line
    pattern = rf"^\s*{re.escape(label)}\s*:"
    if re.match(pattern, line, flags=re.IGNORECASE):
        return f"{label}: {value}"
    return line


def _enforce_extracted_fields(filled_text: str, broker_fields: dict[str, str]) -> str:
    lines = filled_text.splitlines()
    for i, line in enumerate(lines):
        updated = line
        for key, label in FIELD_LABELS.items():
            updated = _override_field_line(updated, label, broker_fields.get(key, ""))
        lines[i] = updated
    return "\n".join(lines)


def _format_vanna_claims_history(eoi_state: dict[str, Any]) -> str:
    sql_result = eoi_state.get("sql_result")
    if not isinstance(sql_result, pd.DataFrame) or sql_result.empty:
        return ""
    if "Error" in sql_result.columns:
        return ""

    # Build compact row summaries from Vanna output for claim history section.
    top_rows = sql_result.head(3).fillna("")
    row_summaries: list[str] = []
    for _, row in top_rows.iterrows():
        pairs = []
        for col in top_rows.columns[:4]:
            val = str(row[col]).strip()
            if not val:
                continue
            pairs.append(f"{col}: {val}")
        if pairs:
            row_summaries.append(", ".join(pairs))

    return " | ".join(row_summaries)


def _enforce_declaration_and_claims(filled_text: str) -> str:
    lines = filled_text.splitlines()
    out: list[str] = []
    declaration_seen = False

    i = 0
    while i < len(lines):
        line = lines[i]
        low = line.strip().lower()

        if low.startswith("i/we hereby declare that"):
            out.append(DECLARATION_TEXT)
            declaration_seen = True
            i += 1
            continue

        if low.startswith("claims history (last 3") and i + 1 < len(lines):
            next_line = lines[i + 1].strip().lower()
            out.append(line)
            if next_line == "not provided":
                i += 2
                continue
            i += 1
            continue

        out.append(line)
        i += 1

    if not declaration_seen:
        for idx, line in enumerate(out):
            if line.strip().lower().startswith("6. declaration"):
                out.insert(idx + 1, "")
                out.insert(idx + 2, DECLARATION_TEXT)
                break

    return "\n".join(out)


def _infer_entity_type(user_prompt: str, eoi_state: dict[str, Any]) -> str:
    text = f"{user_prompt}\n{eoi_state.get('eoi_doc_insights','')}".lower()

    if any(k in text for k in ["broker", "broking", "brokerage", "intermediary"]):
        return "Broker"
    if any(k in text for k in ["vendor", "partner", "supplier"]):
        return "Vendor / Partner"
    if any(k in text for k in ["corporate", "company", "corporation", "inc", "llc", "ltd", "private limited"]):
        return "Corporate"
    if any(k in text for k in ["individual", "person", "sole proprietor", "sole-proprietor"]):
        return "Individual"
    return "Other"


def _set_checkbox_mark(line: str, checked: bool) -> str:
    mark = CHECKED_BOX if checked else UNCHECKED_BOX
    normalized = line.replace("\\u2611", CHECKED_BOX).replace("\\u2610", UNCHECKED_BOX)
    cleaned = re.sub(rf"[{CHECKED_BOX}{UNCHECKED_BOX}]", "", normalized).strip()
    return f"{mark} {cleaned}" if cleaned else mark


def _enforce_type_entity_checkboxes(filled_text: str, selected_entity: str) -> str:
    lines = filled_text.splitlines()
    in_entity_block = False

    for i, line in enumerate(lines):
        lower = line.lower().strip()

        if "type of entity" in lower:
            in_entity_block = True
            continue

        if in_entity_block and lower.startswith("registration / license number"):
            in_entity_block = False

        if not in_entity_block:
            continue

        if "individual" in lower:
            lines[i] = _set_checkbox_mark(line, selected_entity == "Individual")
        elif "corporate" in lower:
            lines[i] = _set_checkbox_mark(line, selected_entity == "Corporate")
        elif "broker" in lower:
            lines[i] = _set_checkbox_mark(line, selected_entity == "Broker")
        elif "vendor" in lower and "partner" in lower:
            lines[i] = _set_checkbox_mark(line, selected_entity == "Vendor / Partner")
        elif "other" in lower:
            lines[i] = _set_checkbox_mark(line, selected_entity == "Other")

    return "\n".join(lines)


def _normalize_checkbox_lines(filled_text: str) -> str:
    out = []
    for raw in filled_text.splitlines():
        line = raw.replace("\\u2611", CHECKED_BOX).replace("\\u2610", UNCHECKED_BOX).strip()

        if CHECKED_BOX in line or UNCHECKED_BOX in line:
            checked = CHECKED_BOX in line
            cleaned = re.sub(rf"[{CHECKED_BOX}{UNCHECKED_BOX}]", "", line).strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            line = f"{CHECKED_BOX if checked else UNCHECKED_BOX} {cleaned}" if cleaned else (CHECKED_BOX if checked else UNCHECKED_BOX)

        out.append(line)
    return "\n".join(out)


def _apply_doc_theme(doc: Document) -> None:
    section = doc.sections[0]
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)


def _add_line_with_style(doc: Document, line: str) -> None:
    stripped = line.strip()
    if not stripped:
        doc.add_paragraph("")
        return

    if stripped.lower().startswith("insurance expression of interest"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(stripped)
        run.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(13, 52, 103)
        return

    if re.match(r"^\d+\.\s", stripped):
        p = doc.add_paragraph()
        run = p.add_run(stripped)
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(25, 66, 124)
        return

    if stripped.startswith(CHECKED_BOX) or stripped.startswith(UNCHECKED_BOX):
        p = doc.add_paragraph()
        run = p.add_run(stripped)
        if stripped.startswith(CHECKED_BOX):
            run.bold = True
            run.font.color.rgb = RGBColor(15, 118, 110)
        else:
            run.font.color.rgb = RGBColor(100, 116, 139)
        return

    if ":" in stripped:
        label, value = stripped.split(":", 1)
        p = doc.add_paragraph()
        k = p.add_run(f"{label.strip()}: ")
        k.bold = True
        k.font.color.rgb = RGBColor(31, 41, 55)

        value_text = value.strip() or "Not Provided"
        v = p.add_run(value_text)
        v.font.color.rgb = RGBColor(16, 87, 156)
        return

    p = doc.add_paragraph()
    run = p.add_run(stripped)
    run.font.color.rgb = RGBColor(55, 65, 81)


def _claims_history_df_from_state(eoi_state: dict[str, Any] | None) -> pd.DataFrame | None:
    if not eoi_state:
        return None
    sql_result = eoi_state.get("sql_result")
    if not isinstance(sql_result, pd.DataFrame) or sql_result.empty:
        return None
    if "Error" in sql_result.columns:
        return None
    return sql_result.head(8).copy()


def _add_claims_history_table(doc: Document, df: pd.DataFrame) -> None:
    if df.empty:
        return

    view = df.iloc[:, : min(len(df.columns), 6)].fillna("")
    table = doc.add_table(rows=1, cols=len(view.columns))
    table.style = "Table Grid"

    hdr_cells = table.rows[0].cells
    for i, col in enumerate(view.columns):
        hdr_cells[i].text = str(col)

    for _, row in view.iterrows():
        cells = table.add_row().cells
        for i, val in enumerate(row.tolist()):
            cells[i].text = str(val)


def _build_styled_eoi_doc(filled_text: str, eoi_state: dict[str, Any] | None = None) -> bytes:
    doc = Document()
    _apply_doc_theme(doc)
    claims_df = _claims_history_df_from_state(eoi_state)

    for line in filled_text.splitlines():
        if line.strip().lower().startswith("claims history (last 3"):
            label = "Claims History (last 3–5 years)"
            value = "See Vanna claims table below." if claims_df is not None else line.split(":", 1)[-1].strip()
            _add_line_with_style(doc, f"{label}: {value}")
            if claims_df is not None:
                _add_claims_history_table(doc, claims_df)
            continue
        _add_line_with_style(doc, line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_eoi_document(user_prompt: str, eoi_state: dict[str, Any], template_path: str | None = None) -> tuple[bytes, str]:
    path = _resolve_template_path(template_path)

    template_text = _load_template_text(str(path))
    filled_text = _build_filled_form_text(user_prompt, eoi_state, template_text)

    broker_fields = dict(eoi_state.get("eoi_broker_fields") or {})
    vanna_claims = _format_vanna_claims_history(eoi_state)
    if vanna_claims:
        broker_fields["claims_history"] = vanna_claims

    filled_text = _enforce_extracted_fields(filled_text, broker_fields)
    filled_text = _enforce_declaration_and_claims(filled_text)

    selected_entity = _infer_entity_type(user_prompt, eoi_state)
    filled_text = _enforce_type_entity_checkboxes(filled_text, selected_entity)
    filled_text = _normalize_checkbox_lines(filled_text)

    doc_bytes = _build_styled_eoi_doc(filled_text, eoi_state=eoi_state)

    return doc_bytes, "Generated_Insurance_EOI.docx"


def EOI_node(state: GraphState) -> GraphState:
    user_prompt = (state.get("user_prompt") or "").strip()
    if not user_prompt:
        return {
            "eoi_doc_insights": "Please enter a prompt.",
            "sql_result": None,
            "sql_query": None,
            "web_links": [],
            "general_summary": "",
            "eoi_broker_fields": {},
        }

    uploaded_file_path = state.get("uploaded_file1_path") or state.get("uploaded_file_path")

    broker_text = ""
    if uploaded_file_path and os.path.exists(uploaded_file_path):
        try:
            broker_text = _extract_doc_text(uploaded_file_path)
        except Exception:
            broker_text = ""

    eoi_broker_fields = extract_broker_fields(broker_text) if broker_text else {}

    doc_insights = "No document uploaded."
    try:
        if uploaded_file_path and os.path.exists(uploaded_file_path):
            ext = Path(uploaded_file_path).suffix.lower()
            doc_out = document_node(
                {
                    "user_prompt": user_prompt,
                    "uploaded_file1_path": uploaded_file_path,
                    "uploaded_file1_is_excel": ext in {".xlsx", ".xls", ".csv"},
                    "uploaded_file1_is_docx": ext == ".docx",
                }
            )
            doc_insights = doc_out.get("general_summary") or summarize_doc_with_instruction(uploaded_file_path, user_prompt)
    except Exception:
        doc_insights = summarize_doc_with_instruction(uploaded_file_path, user_prompt)

    vanna_prompt = build_vanna_prompt(user_prompt)
    serp_prompt = build_serp_prompt(user_prompt)
    sql_query, sql_result = _run_internal_sql(vanna_prompt)
    search_result = _run_external_search(serp_prompt)
    intranet_result = _run_intranet_insights(user_prompt, doc_insights, broker_text)
    executive_snapshot = _build_executive_snapshot(
        user_prompt=user_prompt,
        doc_insights=doc_insights,
        sql_query=sql_query,
        sql_result=sql_result,
        web_summary=search_result["general_summary"],
        web_links=search_result["web_links"],
        intranet_summary=intranet_result["intranet_summary"],
    )

    return {
        "route": "eoi",
        "vanna_prompt": vanna_prompt,
        "serp_prompt": serp_prompt,
        "eoi_doc_insights": doc_insights,
        "eoi_broker_fields": eoi_broker_fields,
        "sql_result": sql_result,
        "sql_query": sql_query,
        "web_links": search_result["web_links"],
        "general_summary": search_result["general_summary"],
        "intranet_summary": intranet_result["intranet_summary"],
        "intranet_sources": intranet_result["intranet_sources"],
        "intranet_doc_links": intranet_result["intranet_doc_links"],
        "intranet_doc_count": intranet_result["intranet_doc_count"],
        "intranet_lob": intranet_result["intranet_lob"],
        "eoi_executive_snapshot": executive_snapshot,
    }
