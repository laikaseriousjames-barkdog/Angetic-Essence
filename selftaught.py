"""Self-Evolution Engine — agents build tools, improve GUI, upgrade themselves."""

import os
import sys
import json
import ast
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from core.logger import setup_logger


class SelfEvolution:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("evolution")
        self.base_dir = Path(__file__).resolve().parent.parent
        self.tools_dir = self.base_dir / "tools"
        self.tools_dir.mkdir(exist_ok=True)
        self.evolution_log = self.base_dir / "logs" / "evolution.json"
        self._stats = self._load_stats()

    def _load_stats(self) -> dict:
        if self.evolution_log.exists():
            try:
                return json.loads(self.evolution_log.read_text())
            except Exception:
                pass
        return {
            "tools_created": [],
            "gui_changes": [],
            "self_modifications": [],
            "total_code_written": 0,
            "evolution_generation": 0,
        }

    def _save_stats(self):
        self.evolution_log.parent.mkdir(exist_ok=True)
        self.evolution_log.write_text(json.dumps(self._stats, indent=2))

    def create_tool(self, name: str, description: str, code: str) -> Path | None:
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        if not safe_name.endswith(".py"):
            safe_name += ".py"
        tool_path = self.tools_dir / safe_name

        header = f'"""Auto-generated tool: {name}\n{description}\nCreated: {datetime.utcnow().isoformat()}\n"""\n\n'
        full_code = header + code

        try:
            ast.parse(full_code)
        except SyntaxError as e:
            self.logger.error(f"Tool {name} has syntax error: {e}")
            return None

        tool_path.write_text(full_code, encoding="utf-8")
        self._stats["tools_created"].append(
            {
                "name": name,
                "file": str(tool_path),
                "size": len(full_code),
                "created": datetime.utcnow().isoformat(),
            }
        )
        self._stats["total_code_written"] += len(full_code)
        self._stats["evolution_generation"] += 1
        self._save_stats()
        self.logger.info(f"Tool created: {name} ({len(full_code)}b)")
        return tool_path

    def modify_gui(
        self, element_id: str, new_html: str = None, new_css: str = None
    ) -> bool:
        template = self.base_dir / "dashboard" / "templates" / "dashboard.html"
        if not template.exists():
            self.logger.error("Dashboard template not found")
            return False

        content = template.read_text(encoding="utf-8")

        if new_html and element_id in content:
            content = content.replace(element_id, new_html)
            self.logger.info(f"GUI modified: replaced '{element_id}'")
        elif new_css:
            style_end = content.find("</style>")
            if style_end > 0:
                content = content[:style_end] + new_css + "\n" + content[style_end:]
        else:
            self.logger.warning(f"No changes specified for {element_id}")
            return False

        template.write_text(content, encoding="utf-8")
        self._stats["gui_changes"].append(
            {
                "element": element_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self._stats["evolution_generation"] += 1
        self._save_stats()
        return True

    def modify_own_source(self, agent_name: str, new_code: str) -> bool:
        agent_file = self.base_dir / "agents" / f"{agent_name}.py"
        if not agent_file.exists():
            self.logger.error(f"Agent file not found: {agent_name}.py")
            return False

        backup = agent_file.with_suffix(agent_file.suffix + ".bak")
        shutil.copy2(agent_file, backup)

        try:
            ast.parse(new_code)
        except SyntaxError as e:
            self.logger.error(f"Syntax error in modification: {e}")
            return False

        agent_file.write_text(new_code, encoding="utf-8")
        self._stats["self_modifications"].append(
            {
                "agent": agent_name,
                "timestamp": datetime.utcnow().isoformat(),
                "backup": str(backup),
            }
        )
        self._stats["evolution_generation"] += 1
        self._save_stats()
        self.logger.info(f"Agent {agent_name} self-modified ({len(new_code)}b)")
        return True

    def install_package(self, package: str) -> bool:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                self.logger.info(f"Package installed: {package}")
                return True
            self.logger.error(f"Package install failed: {result.stderr[:200]}")
            return False
        except Exception as e:
            self.logger.error(f"Package install error: {e}")
            return False

    def execute_code(self, code: str, timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    @property
    def stats(self) -> dict:
        return self._stats
