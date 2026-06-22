import re
import json
import time
from pathlib import Path
from datetime import datetime
from core.logger import setup_logger


PRIORITY_KEYWORDS = {
    "high": [
        "urgent",
        "asap",
        "critical",
        "immediately",
        "high priority",
        "now",
        "emergency",
    ],
    "low": ["someday", "eventually", "not important", "low priority", "whenever"],
}


class Commander:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("commander")
        self.task_log = self._load_tasks()
        self._task_id = len(self.task_log)

    def _load_tasks(self) -> list:
        path = Path(__file__).resolve().parent.parent / "logs" / "tasks.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return []

    def _save_tasks(self):
        path = Path(__file__).resolve().parent.parent / "logs" / "tasks.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(self.task_log, indent=2))

    def _word_in_text(self, word: str, text: str) -> bool:
        return bool(re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE))

    def _words_in_text(self, words: list[str], text: str) -> bool:
        return any(self._word_in_text(w, text) for w in words)

    def parse_command(self, user_input: str) -> dict:
        priority = "medium"
        input_lower = user_input.lower()
        for level, keywords in PRIORITY_KEYWORDS.items():
            if any(self._word_in_text(kw, input_lower) for kw in keywords):
                priority = level
                break

        target_agents = self._detect_target(user_input)
        action_type = self._detect_action(user_input)

        return {
            "id": self._task_id,
            "original": user_input,
            "priority": priority,
            "target_agents": target_agents,
            "action_type": action_type,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
        }

    def _detect_target(self, text: str) -> list[str]:
        all_agents = ["developer", "tester", "critic"]
        mentioned = []
        mapping = {
            "dev": "developer",
            "developer": "developer",
            "code": "developer",
            "test": "tester",
            "tester": "tester",
            "qa": "tester",
            "critic": "critic",
            "review": "critic",
            "analyze": "critic",
        }
        for kw, agent in mapping.items():
            if self._word_in_text(kw, text) and agent not in mentioned:
                mentioned.append(agent)
        if not mentioned:
            return all_agents
        return mentioned

    def _detect_action(self, text: str) -> str:
        if self._words_in_text(
            ["scan", "nmap", "penetrat", "exploit", "hack", "vulnerab"], text
        ):
            return "pentest"
        if self._words_in_text(["install", "tool", "package", "setup"], text):
            return "install"
        if self._words_in_text(
            ["create", "write", "build", "make", "develop", "code"], text
        ):
            return "create"
        if self._words_in_text(["test", "check", "verify", "validate", "qa"], text):
            return "test"
        if self._words_in_text(["improve", "optimize", "refactor", "upgrade"], text):
            return "optimize"
        if self._words_in_text(["root", "android", "device", "phone", "adb"], text):
            return "android"
        if self._words_in_text(["analyze", "review", "critique", "audit"], text):
            return "analyze"
        if self._words_in_text(["gui", "ui", "dashboard", "interface", "theme"], text):
            return "gui"
        return "execute"

    def dispatch(self, user_input: str) -> dict:
        task = self.parse_command(user_input)
        self._task_id += 1
        task["id"] = self._task_id
        self.task_log.append(task)
        self._save_tasks()
        self.logger.info(
            f"Task #{task['id']}: [{task['priority']}] -> {task['target_agents']}: {user_input[:60]}"
        )
        return task

    def complete_task(self, task_id: int, result: str = ""):
        for task in self.task_log:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["completed_at"] = datetime.utcnow().isoformat()
                self._save_tasks()
                return task
        return None

    def update_task_status(self, task_id: int, status: str, result: str = None):
        for task in self.task_log:
            if task.get("id") == task_id:
                task["status"] = status
                if result is not None:
                    task["result"] = result
                if status == "completed":
                    task["completed_at"] = datetime.utcnow().isoformat()
                self._save_tasks()
                return task
        return None

    @property
    def pending_tasks(self) -> list:
        return [t for t in self.task_log if t.get("status") == "pending"]

    @property
    def all_tasks(self) -> list:
        return sorted(
            self.task_log,
            key=lambda t: ["high", "medium", "low"].index(t.get("priority", "medium")),
        )
