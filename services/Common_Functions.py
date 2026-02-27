
from services.Graph_state import GraphState
from services.llm_service import call_llm
from config.global_variables import SQL_PAIR_PATH

from typing import List
from dotenv import load_dotenv
import json
import re
import pandas as pd
import sqlite3
from typing import  List
from io import BytesIO
from datetime import datetime
import json
from datetime import date, timedelta
import numpy as np
from pathlib import Path
from io import BytesIO
import base64


money_keywords = ["loss", "premium", "amount", "cost", "ibnr", "ult", "total", "claim", "reserve", "payment"]


load_dotenv()

def get_schema_description(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema_str = ""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_name, in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        cols = cursor.fetchall()
        col_names = [col[1] for col in cols]
        schema_str += f"\n- {table_name}: columns = {', '.join(col_names)}"

    conn.close()
    return schema_str.strip()

def load_qs_pairs():
    with open(SQL_PAIR_PATH, "r") as f:
        text = f.read()
    pairs = re.findall(r'question="(.*?)",\s*sql="""(.*?)"""', text, re.DOTALL)
    return [{"question": q.strip(), "sql": s.strip()} for q, s in pairs]


def last(old, new):
    return new


def prune_state(state: GraphState, exclude: List[str]) -> dict:
    return {k: v for k, v in state.items() if k not in exclude}


def _get_entry_datetime(entry):
    """
    Return a datetime for a history `entry`:
    - checks keys in order: 'timestamp', 'created_at', 'archived_at'
    - if not found, tries first/last message timestamps in entry['messages']
    - if still not found, returns current datetime
    Accepts string timestamps in format "%d %b %Y, %I:%M %p" or ISO format.
    """
    # 1) top-level fields
    ts = entry.get("timestamp") or entry.get("created_at") or entry.get("archived_at")
    # 2) try messages list
    if not ts:
        msgs = entry.get("messages") or []
        if msgs:
            # prefer first message timestamp then last
            ts = msgs[0].get("timestamp") or msgs[-1].get("timestamp") or msgs[0].get("assistant_run", {}).get("timestamp")
    # 3) fallback to now
    if not ts:
        return datetime.now()

    # 4) parse
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return datetime.now()

    ts_str = str(ts)
    # try your expected format first
    try:
        return datetime.strptime(ts_str, "%d %b %Y, %I:%M %p")
    except Exception:
        pass
    # try ISO formats
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        pass
    # try common alternative formats (best-effort)
    alt_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]
    for fmt in alt_formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except Exception:
            continue
    # give up -> return now
    return datetime.now()


def _format_dataframe_for_display(result_obj):
    """Helper: convert serialized list/dict to DataFrame and format numeric columns."""
    df = result_obj
    if isinstance(result_obj, list):
        df = pd.DataFrame(result_obj)
    if isinstance(df, pd.DataFrame):
        formatted_df = df.copy()
        for col in formatted_df.select_dtypes(include='number').columns:
            col_lower = col.lower()
            if "percentile" in col_lower:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
            elif "ratio" in col_lower:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x * 100:.2f}%" if pd.notnull(x) else "")
            elif any(keyword in col_lower for keyword in money_keywords):
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
        return formatted_df
    return result_obj


def format_date_label(chat_date: date) -> str:
    today = date.today()
    if chat_date == today:
        return "Today"
    elif chat_date == today - timedelta(days=1):
        return "Yesterday"
    else:
        return chat_date.strftime("%d %b %Y")
    
def generate_title(prompt: str) -> str:
    try:
        title_prompt = f"Summarize the following user query into a short title:\n\n'{prompt}'\n\nKeep it under 7 words."
        return call_llm(title_prompt)
    except:
        return prompt[:40] + ("..." if len(prompt) > 40 else "")
    



def serialize_chat_history(history):
    """
    Given st.session_state.chat_history (list of dicts), produce a JSON string safely.
    Use this instead of plain json.dumps(history).
    """
    safe_history = []
    for entry in history:
        safe_entry = {}
        # iterate keys in original entry and serialize values
        for k, v in entry.items():
            safe_entry[str(k)] = safe_serialize_obj(v)
        # ensure messages list (if present) is serialized as well
        if "messages" in safe_entry and isinstance(safe_entry["messages"], list):
            safe_messages = []
            for m in safe_entry["messages"]:
                safe_messages.append(safe_serialize_obj(m))
            safe_entry["messages"] = safe_messages
        safe_history.append(safe_entry)

    return json.dumps(safe_history, indent=2, ensure_ascii=False)



def safe_serialize_obj(obj):
    """
    Convert obj to a JSON-serializable representation.
    Handles: pandas.DataFrame, list[dict], numpy types, datetime/date, Path, BytesIO.
    For unknown objects, falls back to str(obj).
    """
    # None / primitives
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj

    # datetime / date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Path
    if isinstance(obj, Path):
        return str(obj)

    # BytesIO -> base64 (optional; careful about size)
    if isinstance(obj, BytesIO):
        # convert to base64 string (avoid if large)
        obj.seek(0)
        b64 = base64.b64encode(obj.read()).decode("ascii")
        return {"__bytes_base64__": b64}

    # pandas DataFrame
    if isinstance(obj, pd.DataFrame):
        try:
            # prefer records orient (list of dicts)
            return obj.where(pd.notnull(obj), None).to_dict(orient="records")
        except Exception:
            # fallback to string
            return str(obj)

    # pandas Series
    if isinstance(obj, pd.Series):
        try:
            return obj.where(pd.notnull(obj), None).to_dict()
        except Exception:
            return list(obj)

    # numpy scalar types
    if isinstance(obj, (np.generic,)):
        return obj.item()

    # lists / tuples / sets
    if isinstance(obj, (list, tuple, set)):
        return [safe_serialize_obj(i) for i in obj]

    # dicts -> apply recursively
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            # ensure keys are strings
            key = str(k)
            out[key] = safe_serialize_obj(v)
        return out

    # dataclasses? try to convert to dict
    # fallback: try to use __dict__ if present
    if hasattr(obj, "__dict__"):
        try:
            return safe_serialize_obj(vars(obj))
        except Exception:
            pass

    # last resort: stringify
    try:
        return str(obj)
    except Exception:
        return None
    

def safe_serialize_preview_df(df_like):
    # If it's already a list-of-dicts, return as-is.
    # If it's a pandas DataFrame, convert to records.
    try:
        import pandas as pd
        if isinstance(df_like, pd.DataFrame):
            return df_like.to_dict(orient="records")
    except Exception:
        pass
    return df_like
