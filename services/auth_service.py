from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_DB_PATH = BASE_DIR / "Users.db"

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _db_conn() -> sqlite3.Connection:
    return sqlite3.connect(str(USERS_DB_PATH))


def init_users_db() -> None:
    conn = _db_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def derive_user_name(email: str) -> str:
    normalized = _normalize_email(email)
    if "@" in normalized:
        return normalized.split("@", 1)[0]
    return normalized or "Not logged in"


def _is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(_normalize_email(email)))


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)


def create_user(email: str, password: str) -> tuple[bool, str]:
    init_users_db()
    email = _normalize_email(email)
    if not _is_valid_email(email):
        return False, "Please enter a valid email address."
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters."

    salt = os.urandom(16)
    pw_hash = _hash_password(password, salt)

    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO users (email, password_hash, password_salt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, pw_hash.hex(), salt.hex(), datetime.now().isoformat()),
        )
        conn.commit()
        return True, "Account created successfully. Please login."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> tuple[bool, str]:
    init_users_db()
    email = _normalize_email(email)
    if not _is_valid_email(email):
        return False, "Please enter a valid email address."

    conn = _db_conn()
    try:
        row = conn.execute(
            "SELECT id, password_hash, password_salt FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return False, "No account found for this email."

        _user_id, password_hash_hex, password_salt_hex = row
        salt = bytes.fromhex(password_salt_hex)
        expected_hash = bytes.fromhex(password_hash_hex)
        provided_hash = _hash_password(password, salt)
        if not hmac.compare_digest(provided_hash, expected_hash):
            return False, "Invalid password."

        conn.execute(
            "UPDATE users SET last_login_at = ? WHERE email = ?",
            (datetime.now().isoformat(), email),
        )
        conn.commit()
        return True, email
    finally:
        conn.close()


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated")) and bool(st.session_state.get("user_email"))


def logout_user() -> None:
    st.session_state["authenticated"] = False
    st.session_state.pop("user_email", None)
    st.session_state.pop("email", None)
    st.session_state.pop("user_name", None)
    # Clear cached chat-session state so next login reloads correct user data.
    st.session_state.pop("chat_history", None)
    st.session_state.pop("active_chat_index", None)
    st.session_state.pop("current_session", None)
    st.session_state.pop("just_ran_agent", None)
    st.session_state.pop("_underwriter_chat_loaded_user", None)


def require_auth() -> None:
    if is_authenticated():
        return
    st.warning("Please login first to access this page.")
    st.switch_page("app.py")
    st.stop()
