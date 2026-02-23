from services.Common_Functions import prune_state
from services.Graph_state import GraphState
from services.llm_service import call_llm


import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from langchain_core.runnables import Runnable
from serpapi import GoogleSearch
from vanna.remote import VannaDefault
from docx import Document
import tempfile
import os
from dotenv import load_dotenv
import json
import re
from openai import OpenAI
import pandas as pd
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
from datetime import datetime
import json
from datetime import date, timedelta
from pptx import Presentation
from pptx.util import Inches, Pt
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
import tempfile
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.table import Table as DocxTable
import tempfile
import uuid
from docx.table import Table as DocxTable
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import numpy as np
from pathlib import Path
from io import BytesIO
import base64
from time import sleep
from urllib.parse import urlparse
import io
import re
from difflib import get_close_matches
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
import math
import logging

load_dotenv()

STATE_KEYS_SET_AT_ENTRY = []

#-----------------------------WEB SEARCH AGENT-----------------------------------
# --Enhance Google Search--
DOMAINS = {
    "core": [
        "swissre.com", "munichre.com", "amwins.com", "willistowerswatson.com",
        "insurancebusinessmag.com", "businessinsurance.com",
        "insuranceinsider.com", "iii.org",  # Insurance Information Institute
        "deloitte.com", "mckinsey.com", "bcg.com"
    ],
    "regulators": [
        "irdai.gov.in", "naic.org", "eba.europa.eu", "eiopa.europa.eu"
    ],
    "market_news": [
        "dowjones.com", "wsj.com", "reuters.com", "bloomberg.com",
        "financialtimes.com", "economist.com"
    ],
}

INSURANCE_SYNONYMS = {
    "loss ratio": ["combined ratio", "claims ratio"],
    "reserve": ["ibnr", "loss reserves", "case reserve", "ultimate loss"],
    "premium": ["written premium", "earned premium", "gross premium", "gwp"],
    "social inflation": ["nuclear verdicts", "litigation costs", "jury awards"],
}


def _domain_filter(for_news: bool) -> str:
    # Bias to relevant sources; include market_news when for_news = True
    domains = DOMAINS["core"] + DOMAINS["regulators"] + (DOMAINS["market_news"] if for_news else [])
    return " OR ".join([f"site:{d}" for d in domains])


def enhance_query(prompt: str) -> dict:
    """
    Builds query and mode.
    Returns: {"q": <string>, "for_news": bool}
    """
    p = prompt.strip()
    lower = p.lower()
#   for_news = any(w in lower for w in ["news", "today", "latest", "update", "trend", "q3", "q4", "fy", "quarter", "yoy", "benchmark"])
    for_news = "TRUE"

    insurance_tokens = ["insurance", "insurer", "claim", "premium", "underwriting", "actuarial", "reinsurance", "coverage", "reserving"]
    base_query = p if any(t in lower for t in insurance_tokens) else f"in insurance industry: {p}"
    sites = _domain_filter(for_news)

    q = f'{base_query} ({sites})'
    return {"q": q, "for_news": for_news}

# --- SerpAPI Node --- 
def serp_node(state: GraphState) -> GraphState:
    built = enhance_query(state["user_prompt"])
    query, for_news = built["q"], built["for_news"]

    search = GoogleSearch({
    "q": query,
    "api_key": os.getenv("SERPAPI_API_KEY"),
    "num": 5
    })
    results = search.get_dict()

    links = []
    summaries = []

    if "organic_results" in results:
        for r in results["organic_results"][:5]:
            link = r.get("link")
            title = r.get("title", "Untitled").strip('"')
            snippet = r.get("snippet", "No summary available.").strip('"')
            if link:
                links.append(f"[{title}]({link})")
                summaries.append(snippet)

    if not links:
        links = ["No high-quality results found (try broader query or remove filters)."]
        summaries = [""]

    # Build LLM prompt
    combined_text = "\n".join([f"[{i+1}] {s}" for i, s in enumerate(summaries)])

    sql_in_context = isinstance(state.get("sql_result"), pd.DataFrame) and not state["sql_result"].empty
    internal_sql_top5 = state["sql_result"].head(5).to_markdown(index=False) if sql_in_context else ""

    # 2) EXTERNAL: fetch market benchmark only from the web
    #    We override the user_prompt for the search node so it explicitly asks for market/industry averages externally.
    ext_prompt = f"""
    Market / industry average IBNR trend (P&C) for recent 1–5 years, external sources only.
    Prefer credible sources (Dow Jones/WSJ/Reuters/BusinessInsurance/InsuranceInsider/regulators/reinsurers).
    Use USD, %, ratios if available.
    Original user context: {state.get('user_prompt','')}
    """.strip()


    if sql_in_context:
        general_summary_prompt = f"""
        You are an insurance and actuarial analyst comparing internal company data with external web results.

        Use the following INTERNAL SQL DATA ONLY FOR CONTEXT. **Do not include internal tables or numbers in your output.**

        🧾 Internal SQL Query:
        {state['sql_query'] if 'sql_query' in state else ''}

        📊 Top 5 rows of SQL Output (reference only, do not display):
        SQL: {state.get('sql_query','')}
        Top rows:
        {internal_sql_top5}

        External snippets (numbered):
        {combined_text}
        
        User Prompt:
        "{ext_prompt}"

        🔽 Your Task:
        - Summarize **only what is found in the external data**
        - DO NOT display the internal SQL data or repeat it
        - Be concise, no more than **6-8 lines**
        - Include **percentages, currency, loss ratios, IBNR**, and other KPIs found in the web
        - Avoid repeating full articles or sentences
        - Mention key **KPIs** (e.g., IBNR, premiums, loss ratios, reserves)
        -Focus more on numerical insights

        Output format:
        1. 📌 Start with a summary of overall findings with around 5-6 lines.
        2. 🔢 Then list 6–7 **quantitative highlights**.
        3. 💬 End with any notable quote or number from a source if applicable.
        4. Can include a table with numerical insights as well, but not the internal data or tabular data. Only if you found it in external data.
        """
    else:
        general_summary_prompt = f"""
        Your task is to extract **concise and numerically rich insights** from the following web snippets, in response to this user query:

        "{state['user_prompt']}"

        External snippets (numbered):
        {combined_text}

       Your summary should:
        - Be structured and no more than **10–12 lines**
        - Include **percentages**, **currency values**, **ratios**, **dates**, and **growth trends**
        - Mention key **KPIs** (e.g., IBNR, premiums, loss ratios, reserves)
        - Avoid repeating the snippets. Instead, **synthesize them**
        - If no numbers are found, say so explicitly

        Output format:
        1. 📌 Start with a summary of overall findings with around 5-6 lines.
        2. 🔢 Then list 3–4 **quantitative highlights**.
        3. 💬 End with any notable quote or number from a source if applicable.
        4. Can include a table with numerical insights as well
        """

    general_summary = call_llm(general_summary_prompt).strip()

    return {
        **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
        "web_links": list(zip(links, summaries)),
        "general_summary": general_summary
    }