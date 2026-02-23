from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "Actuarial_Data.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))


def fetch_kpis() -> dict[str, Any]:
    query = """
    SELECT
      SUM([Ultimate Premium]) AS total_premium,
      SUM([Incurred Loss]) AS total_incurred,
      AVG([Loss Ratio]) AS avg_loss_ratio,
      AVG([IBNR]) AS avg_ibnr
    FROM PnC_Data
    """
    with _conn() as conn:
        row = pd.read_sql_query(query, conn).iloc[0]

    return {
        "total_premium": float(row["total_premium"] or 0.0),
        "total_incurred": float(row["total_incurred"] or 0.0),
        "avg_loss_ratio": float(row["avg_loss_ratio"] or 0.0),
        "avg_ibnr": float(row["avg_ibnr"] or 0.0),
    }


def fetch_lob_loss_ratio() -> pd.DataFrame:
    query = """
    SELECT [Reserve Class] AS reserve_class,
           AVG([Loss Ratio]) AS avg_loss_ratio,
           SUM([Ultimate Premium]) AS premium
    FROM PnC_Data
    GROUP BY [Reserve Class]
    ORDER BY avg_loss_ratio DESC
    """
    with _conn() as conn:
        return pd.read_sql_query(query, conn)


def fetch_recent_trend() -> pd.DataFrame:
    query = """
    SELECT [Exposure Year] AS exposure_year,
           SUM([Incurred Loss]) AS incurred_loss,
           SUM([Ultimate Premium]) AS ultimate_premium,
           AVG([Loss Ratio]) AS loss_ratio
    FROM PnC_Data
    GROUP BY [Exposure Year]
    ORDER BY [Exposure Year]
    """
    with _conn() as conn:
        return pd.read_sql_query(query, conn)

