import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

class AuditLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, log_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_path=None):
        if self._initialized:
            return
        self.log_path = Path(log_path) if log_path else Path(__file__).parent.parent / 'logs' / 'audit.jsonl'
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True
    
    def log(self, agent_name: str, action: str, details: Dict[str, Any] = None, success: bool = True, error: str = None):
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'agent': agent_name,
            'action': action,
            'success': success,
            'details': details or {},
            'error': error
        }
        with self._lock:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
    
    def log_agent_start(self, agent_name: str, task: str):
        self.log(agent_name, 'agent_start', {'task': task})
    
    def log_agent_complete(self, agent_name: str, result_summary: str):
        self.log(agent_name, 'agent_complete', {'result': result_summary[:200]})
    
    def log_agent_error(self, agent_name: str, error: str, context: Dict = None):
        self.log(agent_name, 'agent_error', context or {}, success=False, error=error)
    
    def log_permission_denied(self, agent_name: str, action: str, reason: str):
        self.log(agent_name, 'permission_denied', {'attempted_action': action, 'reason': reason}, success=False)
    
    def log_tool_execution(self, agent_name: str, tool_name: str, args: Dict, result: str):
        self.log(agent_name, 'tool_execute', {'tool': tool_name, 'args': args, 'result': result[:200]})
    
    def log_file_access(self, agent_name: str, path: str, operation: str, allowed: bool):
        self.log(agent_name, 'file_access', {'path': path, 'operation': operation, 'allowed': allowed})
    
    def log_network_request(self, agent_name: str, url: str, allowed: bool):
        self.log(agent_name, 'network_request', {'url': url, 'allowed': allowed})
    
    def get_recent_entries(self, count: int = 50) -> list:
        entries = []
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
                    if len(entries) >= count:
                        break
        except FileNotFoundError:
            pass
        return list(reversed(entries))

# Global instance
audit = AuditLogger()