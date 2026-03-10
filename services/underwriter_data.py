from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from config.global_variables import DB_PATH as CONFIG_DB_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "Underwriter_Data.db"


def _resolve_db_path() -> Path:
    candidates = [
        os.getenv("UNDERWRITER_DB_PATH"),
        os.getenv("EOI_DB_PATH"),
        str(DEFAULT_DB_PATH),
        str(Path(CONFIG_DB_PATH)),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        p = Path(candidate).expanduser()
        if not p.is_absolute():
            p = BASE_DIR / p
        p = p.resolve()
        if p.exists():
            return p
    return DEFAULT_DB_PATH


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(_resolve_db_path()))


def _resolve_underwriting_table(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    names = [str(r[0]) for r in rows if r and r[0]]
    if not names:
        raise RuntimeError("No tables found in underwriting database.")

    preferred = [
        "underwriting_dataset",
        "underwriter_data",
        "underwriting_data",
        "portfolio",
    ]
    lowered = {n.lower(): n for n in names}
    for key in preferred:
        if key in lowered:
            return lowered[key]
    return names[0]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return {str(r[1]).lower() for r in rows if len(r) > 1}


def _pick_first(columns: set[str], *candidates: str) -> str | None:
    for name in candidates:
        if name.lower() in columns:
            return name
    return None


def _sql_expr_or_null(col_name: str | None, expr: str, alias: str) -> str:
    if not col_name:
        return f"NULL AS {alias}"
    return expr.format(col=col_name) + f" AS {alias}"


def fetch_kpis() -> dict[str, Any]:
    with _conn() as conn:
        table = _resolve_underwriting_table(conn)
        cols = _table_columns(conn, table)
        premium_col = _pick_first(cols, "ultimate_premium")
        incurred_col = _pick_first(cols, "incurred_loss")
        loss_ratio_col = _pick_first(cols, "loss_ratio")
        claims_freq_col = _pick_first(cols, "claims_frequency")
        query = f"""
        SELECT
          {_sql_expr_or_null(premium_col, "SUM({col})", "total_premium")},
          {_sql_expr_or_null(incurred_col, "SUM({col})", "total_incurred")},
          {_sql_expr_or_null(loss_ratio_col, "AVG({col})", "avg_loss_ratio")},
          {_sql_expr_or_null(claims_freq_col, "AVG({col})", "avg_claims_frequency")}
        FROM {table}
        """
        row = pd.read_sql_query(query, conn).iloc[0]

    return {
        "total_premium": float(row["total_premium"] or 0.0),
        "total_incurred": float(row["total_incurred"] or 0.0),
        "avg_loss_ratio": float(row["avg_loss_ratio"] or 0.0),
        "avg_claims_frequency": float(row["avg_claims_frequency"] or 0.0),
    }


def fetch_lob_loss_ratio() -> pd.DataFrame:
    with _conn() as conn:
        table = _resolve_underwriting_table(conn)
        cols = _table_columns(conn, table)
        lob_col = _pick_first(cols, "class_of_business", "risk_type")
        loss_ratio_col = _pick_first(cols, "loss_ratio")
        premium_col = _pick_first(cols, "ultimate_premium")
        if not lob_col:
            return pd.DataFrame(columns=["reserve_class", "avg_loss_ratio", "premium"])
        query = f"""
        SELECT {lob_col} AS reserve_class,
               {_sql_expr_or_null(loss_ratio_col, "AVG({col})", "avg_loss_ratio")},
               {_sql_expr_or_null(premium_col, "SUM({col})", "premium")}
        FROM {table}
        GROUP BY {lob_col}
        ORDER BY avg_loss_ratio DESC
        """
        return pd.read_sql_query(query, conn)


def fetch_recent_trend() -> pd.DataFrame:
    with _conn() as conn:
        table = _resolve_underwriting_table(conn)
        cols = _table_columns(conn, table)
        lob_col = _pick_first(cols, "class_of_business", "risk_type")
        incurred_col = _pick_first(cols, "incurred_loss")
        premium_col = _pick_first(cols, "ultimate_premium")
        if not lob_col:
            return pd.DataFrame(columns=["line_of_business", "incurred_loss", "ultimate_premium"])
        query = f"""
        SELECT {lob_col} AS line_of_business,
               {_sql_expr_or_null(incurred_col, "SUM({col})", "incurred_loss")},
               {_sql_expr_or_null(premium_col, "SUM({col})", "ultimate_premium")}
        FROM {table}
        WHERE {lob_col} IS NOT NULL AND TRIM({lob_col}) <> ''
        GROUP BY {lob_col}
        ORDER BY line_of_business
        """
        return pd.read_sql_query(query, conn)

