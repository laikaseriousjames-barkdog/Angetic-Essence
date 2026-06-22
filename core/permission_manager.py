import yaml
from pathlib import Path
from typing import Dict, Any, List
from core.audit_logger import audit

class PermissionManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        import sys
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent.resolve()
        else:
            base_dir = Path(__file__).parent.parent
        self.config_path = base_dir / "config.yaml"
        self.permissions: Dict[str, Any] = {}
        self.sandbox_mode = False
        self.load_config()
        self._initialized = True

    def load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                self.permissions = config.get("permissions", {})
                self.sandbox_mode = config.get("sandbox", {}).get("enabled", False) or config.get("sandbox_mode", False)
        except Exception as e:
            print(f"Error loading config.yaml: {e}")
            self.permissions = {}
            self.sandbox_mode = True  # Fail-safe: enable sandbox on error

    def get_agent_persona(self, role: str) -> str:
        """
        Maps a dashboard role to a persona name from config.yaml
        Mapping: 
        developer -> Knuth
        tester -> Turing
        critic -> Lovelace
        optimizer -> Knuth
        """
        mapping = {
            "developer": "Knuth",
            "tester": "Lovelace",
            "critic": "Turing",
            "optimizer": "Knuth"
        }
        return mapping.get(role, "Turing")

    def check_permission(self, role: str, action: str) -> bool:
        """
        Validates if a specific role can perform an action.
        """
        if self.sandbox_mode:
            audit.log_permission_denied(role, action, "Global sandbox mode active")
            return False

        persona = self.get_agent_persona(role)
        persona_perms = self.permissions.get(persona, {})
        allowed = persona_perms.get(action, False)

        if not allowed:
            audit.log_permission_denied(role, action, f"Persona {persona} not permitted to {action}")

        return allowed

# Global instance
permissions = PermissionManager()