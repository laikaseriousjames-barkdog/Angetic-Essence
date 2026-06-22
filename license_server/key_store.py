"""SQLite-backed license key store for the validation server."""

import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "licenses.db"


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                customer_email TEXT NOT NULL,
                customer_name TEXT DEFAULT '',
                tier TEXT NOT NULL CHECK(tier IN ('perpetual','subscription_monthly','subscription_yearly')),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','revoked','expired')),
                created_at INTEGER NOT NULL,
                activated_at INTEGER,
                expires_at INTEGER,
                stripe_session_id TEXT,
                stripe_subscription_id TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                ip_address TEXT,
                timestamp INTEGER NOT NULL,
                result TEXT NOT NULL
            )
        """)


def store_license(
    license_key: str,
    customer_email: str,
    tier: str,
    expires_at: int = None,
    customer_name: str = "",
    stripe_session_id: str = "",
    stripe_subscription_id: str = "",
) -> bool:
    init_db()
    with _get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO licenses
                    (license_key, customer_email, customer_name, tier,
                     created_at, expires_at, stripe_session_id, stripe_subscription_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    license_key,
                    customer_email,
                    customer_name,
                    tier,
                    int(time.time()),
                    expires_at,
                    stripe_session_id,
                    stripe_subscription_id,
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def validate_key(license_key: str) -> dict:
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE license_key = ?", (license_key,)
        ).fetchone()

    if row is None:
        return {"valid": False, "reason": "not_found"}

    data = dict(row)

    if data["status"] == "revoked":
        return {"valid": False, "reason": "revoked"}

    if data["expires_at"] and data["expires_at"] < time.time():
        return {"valid": False, "reason": "expired"}

    return {
        "valid": True,
        "tier": data["tier"],
        "customer_email": data["customer_email"],
        "expires_at": data["expires_at"],
        "created_at": data["created_at"],
    }


def log_validation(license_key: str, ip_address: str, result: str):
    init_db()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO validation_log (license_key, ip_address, timestamp, result) VALUES (?, ?, ?, ?)",
            (license_key, ip_address, int(time.time()), result),
        )


def get_license_by_email(email: str) -> list[dict]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM licenses WHERE customer_email = ? ORDER BY created_at DESC",
            (email,),
        ).fetchall()
    return [dict(r) for r in rows]


def revoke_key(license_key: str) -> bool:
    init_db()
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE licenses SET status = 'revoked' WHERE license_key = ?",
            (license_key,),
        )
        return cur.rowcount > 0


def get_all_licenses(limit: int = 100, offset: int = 0) -> list[dict]:
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM licenses ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]
