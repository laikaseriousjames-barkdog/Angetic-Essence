"""Phase 2: The Developer Agent.

Full terminal access to write scripts, create tools, install packages,
and overwrite its own codebase based on performance logs.
"""

import subprocess
import sys
from pathlib import Path
from core.logger import setup_logger
from core.overwrite import SourceOverwriter


class DeveloperAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("developer")
        self.overwriter = SourceOverwriter()
        self.work_dir = Path(__file__).resolve().parent.parent

    def execute_shell(self, command: str, timeout: int = 120) -> dict:
        self.logger.info(f"Executing shell command: {command[:120]}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
            )
            output = {
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
                "returncode": result.returncode,
            }
            self.logger.info(
                f"Shell result: rc={result.returncode}, "
                f"stdout={len(result.stdout)}b, stderr={len(result.stderr)}b"
            )
            return output
        except subprocess.TimeoutExpired:
            self.logger.error(f"Shell command timed out after {timeout}s")
            return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1}
        except Exception as e:
            self.logger.error(f"Shell command failed: {e}")
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def write_file(self, filepath: str | Path, content: str) -> Path:
        path = self.overwriter.overwrite_file(filepath, content)
        self.logger.info(f"Wrote {len(content)}b to {path}")
        return path

    def read_file(self, filepath: str | Path) -> str:
        path = Path(filepath)
        if not path.exists():
            self.logger.warning(f"File not found: {path}")
            return ""
        content = path.read_text(encoding="utf-8")
        self.logger.info(f"Read {len(content)}b from {path}")
        return content

    def install_package(self, package: str) -> dict:
        self.logger.info(f"Installing package: {package}")
        return self.execute_shell(f"{sys.executable} -m pip install {package}")

    def generate_code(self, prompt: str) -> str:
        """Generate code based on a prompt (placeholder for LLM integration)."""
        self.logger.info(f"Code generation request: {prompt[:100]}")
        return f"# Auto-generated code for: {prompt}\n"
