from services.Common_Functions import get_schema_description,prune_state

from agents.serp_agent import serp_node

from services.Graph_state import GraphState
from services.llm_service import call_llm
from services.vanna_service import vanna_configure


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

import tempfile
import tempfile
from config.global_variables import DB_PATH



load_dotenv()


vn_model=vanna_configure()

STATE_KEYS_SET_AT_ENTRY = []

# ------------------ COMP Node  -----------------
# COMPARISON_TERMS = [
#     "market average", "industry average", "industry", "benchmark", "benchmarks",
#     "peer", "peers", "peer set", "vs", "versus", "against", "relative to",
#     "compare", "comparison", "compared to", "market trend", "external"
# ]

def comp_node(state: GraphState) -> GraphState:
    # 1) INTERNAL: build a safe Vanna prompt (internal-only)

    schema_desc = get_schema_description(DB_PATH)
    raw_prompt = state.get("vanna_prompt") or state["user_prompt"]

    # Build a strict instruction block to prevent introspection
    instruction_block = (
        "IMPORTANT: You are only allowed to use the schema below — you must NOT inspect or read any rows from the database. "
        "Do NOT request sample rows. Do NOT attempt to access the database for schema discovery. "
        "Using only the schema below, produce a single valid SQL query (ANSI SQL or dialect I specify if needed) that returns "
        "Return only the SQL; do not include explanation text."
    )

    combined_prompt = f"{schema_desc}\n\n{instruction_block}\n\nUser intent: {raw_prompt}\n\n"

    sql_query = vn_model.generate_sql(combined_prompt)

    try:
        result = vn_model.run_sql(sql_query)
        if isinstance(result, pd.DataFrame):
            sql_df = result
        elif isinstance(result, list):
            sql_df = pd.DataFrame(result)
        else:
            sql_df = pd.DataFrame([{"Result": str(result)}])
    except Exception as e:
        sql_df = pd.DataFrame([{"Error": f"SQL Execution failed: {e}"}])

    serp_result = serp_node({**state, "sql_query": sql_query, "sql_result": sql_df})

    web_links = serp_result.get("web_links", [])
    external_summary = serp_result.get("general_summary", "")

    # 3) COMPARISON: clear separation + citations
    comparison_prompt = f"""
    You are an Benchmarking actuarial analyst. Compare OUR internal IBNR trend to EXTERNAL market/industry benchmarks.
    Rules:
    - Use INTERNAL SQL only for our numbers; do NOT infer market values from internal data.
    - Use EXTERNAL WEB snippets only for market/industry values; if no numeric market average is found, say so explicitly.
    - Put all money in **USD**, include **%/ratios/dates** where present.
    - Append [i] citations for any external metric where i refers to the snippet index (shown below).
    - If sources disagree, note the discrepancy briefly.

    Your job is to:
    1. Analyze differences, similarities, and gaps between internal company data and external web sources.
    2. Focus heavily on **numerical metrics** such as:
    - IBNR, Incurred Loss, Ultimate Loss
    - Premiums, Loss Ratios
    - Exposure Years, Percent changes

    3. Focus more on:
    - Trends (increases/decreases)
    - Matching vs. diverging figures
    - Numerical differences or % differences

    Our internal (context only; do not reveal raw table):
    SQL: {sql_query}
    Top rows (context only):
    {sql_df.head(5).to_markdown(index=False) if isinstance(sql_df, pd.DataFrame) else str(sql_df)}

    External snippets (numbered):
    {chr(10).join([f"[{i+1}] {s}" for i, (_, s) in enumerate(web_links)])}

    Task:
    1) 5–7 lines overview (internal vs market).
    2) 3–5 bullets with side-by-side contrasts (Our vs Market) using USD/%/ratios and [citation] only for external numbers.
    3) 1 “watch item” (e.g., social inflation, rate adequacy, reserving pressure) if relevant.

    General external synthesis to leverage (do not copy verbatim; keep citations): 
    {external_summary}
    """
    comparison_summary = call_llm(comparison_prompt).strip()

    return {
        **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
        "sql_result": sql_df,
        "sql_query": sql_query,
        "web_links": web_links,
        "general_summary": external_summary,
        "comparison_summary": comparison_summary
    }

