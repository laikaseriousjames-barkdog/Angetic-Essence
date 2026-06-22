import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from core.system_tracing import get_trace_id

class AuditLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.log_path = Path(__file__).parent.parent / "logs" / "audit.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def log(self, agent: str, action: str, success: bool, details: Dict[str, Any] = None, error: Optional[str] = None):
        """Write a structured audit entry to the JSONL log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": get_trace_id(),
            "agent": agent,
            "action": action,
            "success": success,
            "details": details or {},
            "error": error
        }
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_event(self, agent: str, event: str, details: Dict[str, Any] = None, success: bool = True, error: Optional[str] = None):
        """Helper for standard lifecycle events (AGENT_START, TASK_COMPLETE, etc)."""
        self.log(agent, event, success, details, error)

audit = AuditLogger()