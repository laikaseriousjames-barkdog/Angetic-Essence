import sqlite3
import json
import time
import threading
from pathlib import Path


class RateLimiter:
    def __init__(self, rate: float = 10.0, burst: int = 20):
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False


class MemoryManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent / "essence_state.db"
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.rate_limiter = RateLimiter()
        self._init_db()

    def _init_db(self):
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    agent_name TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS active_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    task_description TEXT,
                    status TEXT,
                    assigned_to TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    user_id TEXT PRIMARY KEY,
                    key_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS spend_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    provider TEXT,
                    model TEXT,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    timestamp INTEGER NOT NULL
                )
            """)
            self._migrate_db()

    def _migrate_db(self):
        for table, column in [
            ("agent_conversations", "user_id"),
            ("active_tasks", "user_id"),
        ]:
            try:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} TEXT DEFAULT 'default'"
                )
            except sqlite3.OperationalError:
                pass

    def set_user_api_key(self, user_id: str, key_hash: str):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO api_keys (user_id, key_hash) VALUES (?, ?)",
                (user_id, key_hash),
            )

    def get_user_api_key(self, user_id: str) -> str | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT key_hash FROM api_keys WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def save_message(
        self, agent_name: str, role: str, content: str, user_id: str = "default"
    ):
        with self.conn:
            self.conn.execute(
                "INSERT INTO agent_conversations (user_id, agent_name, role, content) VALUES (?, ?, ?, ?)",
                (user_id, agent_name, role, content),
            )

    def load_context(
        self, agent_name: str, limit: int = 50, user_id: str = "default"
    ) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM agent_conversations WHERE agent_name = ? AND user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (agent_name, user_id, limit),
        )
        return [
            {"role": row[0], "content": row[1]} for row in reversed(cursor.fetchall())
        ]

    def save_task(
        self,
        task_description: str,
        status: str = "pending",
        assigned_to: str = "",
        user_id: str = "default",
    ):
        with self.conn:
            self.conn.execute(
                "INSERT INTO active_tasks (user_id, task_description, status, assigned_to) VALUES (?, ?, ?, ?)",
                (user_id, task_description, status, assigned_to),
            )

    def get_pending_tasks(self, user_id: str = "default") -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, task_description, status, assigned_to FROM active_tasks WHERE status = 'pending' AND user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return [
            {
                "id": row[0],
                "task_description": row[1],
                "status": row[2],
                "assigned_to": row[3],
            }
            for row in cursor.fetchall()
        ]

    def record_spend(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        user_id: str = "default",
    ):
        PRICING = {
            "openai": {"gpt-4o-mini": (0.15, 0.60)},
            "openrouter": {"*": (2.00, 6.00)},
            "anthropic": {"claude-3-haiku-20240307": (0.25, 1.25)},
            "google": {"*": (0.50, 1.50)},
        }
        rates = PRICING.get(provider, {}).get(
            model, PRICING.get(provider, {}).get("*", (0.0, 0.0))
        )
        cost = (prompt_tokens / 1_000_000 * rates[0]) + (
            completion_tokens / 1_000_000 * rates[1]
        )
        now = int(time.time())
        with self.conn:
            self.conn.execute(
                "INSERT INTO spend_log (user_id, provider, model, prompt_tokens, completion_tokens, cost, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, provider, model, prompt_tokens, completion_tokens, cost, now),
            )

    def get_daily_spend(self, user_id: str = "default") -> float:
        today_start = int(time.time()) - 86400
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(cost), 0.0) FROM spend_log WHERE user_id = ? AND timestamp >= ?",
            (user_id, today_start),
        )
        row = cursor.fetchone()
        return row[0] if row else 0.0

    def check_spend_limit(
        self, max_daily: float = 5.0, user_id: str = "default"
    ) -> bool:
        return self.get_daily_spend(user_id) < max_daily

    def close(self):
        self.conn.close()


Memory = MemoryManager
