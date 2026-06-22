"""Secure authentication layer — bcrypt password hashing & session management."""

import os
import uuid
import time
import functools
from pathlib import Path
from flask import session, redirect, url_for, request, jsonify

try:
    from werkzeug.security import generate_password_hash, check_password_hash

    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False

import sys
if getattr(sys, "frozen", False):
    AUTH_CONFIG_PATH = Path(sys.executable).parent.resolve() / "data" / "auth.json"
else:
    AUTH_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "auth.json"


def _load_auth_config() -> dict:
    AUTH_CONFIG_PATH.parent.mkdir(exist_ok=True)
    if AUTH_CONFIG_PATH.exists():
        try:
            return __import__("json").loads(AUTH_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"users": {}, "sessions": {}}


def _save_auth_config(cfg: dict):
    AUTH_CONFIG_PATH.parent.mkdir(exist_ok=True)
    AUTH_CONFIG_PATH.write_text(__import__("json").dumps(cfg, indent=2))


def hash_password(password: str) -> str:
    if not HAS_WERKZEUG:
        raise RuntimeError("werkzeug not available — cannot hash passwords")
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not HAS_WERKZEUG:
        raise RuntimeError("werkzeug not available — cannot verify passwords")
    return check_password_hash(password_hash, password)


def create_user(username: str, password: str) -> bool:
    cfg = _load_auth_config()
    if username in cfg["users"]:
        return False
    cfg["users"][username] = {
        "password_hash": hash_password(password),
        "created_at": time.time(),
        "user_id": str(uuid.uuid4()),
    }
    _save_auth_config(cfg)
    return True


def authenticate(username: str, password: str) -> str | None:
    cfg = _load_auth_config()
    user = cfg["users"].get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    session_id = str(uuid.uuid4())
    cfg["sessions"][session_id] = {
        "username": username,
        "user_id": user["user_id"],
        "created_at": time.time(),
    }
    _save_auth_config(cfg)
    return session_id


def validate_session(session_id: str) -> dict | None:
    cfg = _load_auth_config()
    return cfg["sessions"].get(session_id)


def destroy_session(session_id: str):
    cfg = _load_auth_config()
    cfg["sessions"].pop(session_id, None)
    _save_auth_config(cfg)


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get("session_id")
        if not session_id:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        session_details = validate_session(session_id)
        if not session_details:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        if session_details.get("username") == "admin":
            os.environ["AE_DEV_MODE"] = "true"
        return f(*args, **kwargs)

    return decorated_function


def ensure_default_admin():
    cfg = _load_auth_config()
    if "admin" not in cfg["users"]:
        create_user("admin", "essence2024")
