import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR.parent / "Actuarial_Data.db")
SQL_PAIR_PATH= str(BASE_DIR.parent / "vanna_advanced_sql_pairs.txt")

    