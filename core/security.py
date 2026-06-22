"""
AngeticSecurity - Permission Gatekeeper

Controls access to dangerous system operations based on agent-specific policies.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

class SecurityPolicy:
    def __init__(self):
        self.permissions = self._load_permissions()
        self.sandbox_mode = False

    def _load_permissions(self) -> Dict[str, Any]:
        """Load permissions from config.yaml."""
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    self.sandbox_mode = cfg.get("sandbox", {}).get("enabled", False) or cfg.get("sandbox_mode", False)
                    return cfg.get("permissions", {})
        except Exception:
            pass
        return {}

    def reload(self) -> None:
        """Refresh permissions from disk."""
        self.permissions = self._load_permissions()

    def set_sandbox_mode(self, enabled: bool) -> None:
        """Global override to restrict all dangerous actions."""
        self.sandbox_mode = enabled

    def check_permission(self, agent_name: str, action: str) -> bool:
        """
        Returns True if the agent is allowed to perform the action.
        
        Actions: 'shell_execution', 'network_bridge', 'file_system_write'
        """
        from core.audit_logger import audit

        from core.system_tracing import get_trace_id

        trace_id = get_trace_id()
        if self.sandbox_mode:
            audit.log_permission_denied(agent_name, action, 'Sandbox mode enabled')
            audit.log(agent_name, 'PERMISSION_CHECK', {'action': action, 'trace_id': trace_id, 'allowed': False, 'reason': 'Sandbox mode enabled'}, success=False)
            return False

        # Default to False if agent or action is not explicitly allowed
        agent_policy = self.permissions.get(agent_name, {})
        allowed = agent_policy.get(action, False)

        if not allowed:
            audit.log_permission_denied(agent_name, action, 'Action not permitted in agent policy')
            audit.log(agent_name, 'PERMISSION_CHECK', {'action': action, 'trace_id': trace_id, 'allowed': False, 'reason': 'Action not permitted in agent policy'}, success=False)
        else:
            audit.log(agent_name, 'PERMISSION_CHECK', {'action': action, 'trace_id': trace_id, 'allowed': True}, success=True)

        return allowed

# Global singleton for the system
policy_engine = SecurityPolicy()
