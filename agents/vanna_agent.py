
from services.Common_Functions import get_schema_description,prune_state
from services.Graph_state import GraphState
from services.llm_service import call_llm
from services.vanna_service import vanna_configure
from config.global_variables import DB_PATH


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

STATE_KEYS_SET_AT_ENTRY = []

load_dotenv()

vn_model = None


def _get_vn_model():
    global vn_model
    if vn_model is not None:
        return vn_model

    vn_model = vanna_configure()
    return vn_model

# ---- Vanna SQL Node ----

def get_user_chart_type(prompt: str) -> Optional[str]:
    prompt = prompt.lower()
    if "bar chart" in prompt or "bar graph" in prompt:
        return "bar"
    elif "line chart" in prompt or "line graph" in prompt:
        return "line"
    elif "pie chart" in prompt or "pie graph" in prompt:
        return "pie"
    return None


def suggest_chart(df: pd.DataFrame) -> Optional[dict]:
    sample_data = df.head(5).to_dict(orient="list")
    prompt = f"""
    You are a data visualization assistant.

    Here is the top of a pandas DataFrame:
    {json.dumps(sample_data, indent=2)}

    Your task:
    - Identify a good chart (bar, line, or pie) that best represents this data.
    - Choose 1 column for the x-axis (categorical or time-based), and 1 or more numeric columns for the y-axis.
    - If multiple y columns are appropriate (e.g. IBNR, IncurredLoss), return them as a list.

    Return your answer in JSON like:
    {{ "type": "bar", "x": "ExposureYear", "y": ["IncurredLoss", "IBNR"] }}

    If no chart is suitable, return: "none"
    """

    reply = call_llm(prompt)
    match = re.search(r'{.*}', reply, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            return None
    return None


def plot_chart(df: pd.DataFrame, chart_info: dict):
    chart_type = chart_info.get("type", "bar")
    x = chart_info.get("x")
    y = chart_info.get("y")

    if isinstance(y, str):
        y = [y]  # Make it a list

    df_columns = list(df.columns)
    def match_col(col_name):
        for c in df_columns:
            if col_name.lower().replace(" ", "") in c.lower().replace(" ", ""):
                return c
        return None

    x_col = match_col(x)
    y_cols = [match_col(col) for col in y if match_col(col)]

    if not x_col or not y_cols:
        st.warning(f"Invalid chart columns: {x}, {y}")
        return

    st.subheader(f"{chart_type.capitalize()} Chart: {', '.join(y)} vs {x}")

    if chart_type == "bar":
        st.bar_chart(df.set_index(x_col)[y_cols])
    elif chart_type == "line":
        st.line_chart(df.set_index(x_col)[y_cols])
    elif chart_type == "pie" and len(y_cols) == 1:
        fig, ax = plt.subplots()
        df.groupby(x_col)[y_cols[0]].sum().plot.pie(ax=ax, autopct='%1.1f%%')
        ax.set_ylabel('')
        st.pyplot(fig)
    else:
        st.warning("Pie chart supports only one y column.")

def vanna_node(state: GraphState) -> GraphState:
    # Use user_prompt if vanna_prompt is not available

    schema_desc = get_schema_description(DB_PATH)
    raw_prompt = state["user_prompt"]

    # Build a strict instruction block to prevent introspection
    instruction_block = (
        "IMPORTANT: You are only allowed to use the schema below — you must NOT inspect or read any rows from the database. "
        "Do NOT request sample rows. Do NOT attempt to access the database for schema discovery. "
        "Using only the schema below, produce a single valid SQL query (ANSI SQL or dialect I specify if needed) that returns "
        "Return only the SQL; do not include explanation text."
    )

    combined_prompt = f"{schema_desc}\n\n{instruction_block}\n\nUser intent: {raw_prompt}\n\n"

    try:
        vn = _get_vn_model()
        sql_query = vn.generate_sql(combined_prompt)
    except Exception as e:
        return {
            **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
            "sql_result": pd.DataFrame([{"Error": f"Vanna initialization/query generation failed: {e}"}]),
            "sql_query": None
        }
    #prompt = state["vanna_prompt"]

    #sql_query = vn_model.generate_sql(combined_prompt)

    try:
        result = vn.run_sql(sql_query)
        if isinstance(result, pd.DataFrame):
            parsed_result = result
        elif isinstance(result, list):
            parsed_result = pd.DataFrame(result)
        else:
            parsed_result = pd.DataFrame([{"Result": str(result)}])
    except Exception as e:
        parsed_result = pd.DataFrame([{"Error": f"SQL Execution failed: {e}"}])

    return {
        **prune_state(state, STATE_KEYS_SET_AT_ENTRY),
        "sql_result": parsed_result,
        "sql_query": sql_query
    }
