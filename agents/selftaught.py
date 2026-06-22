import os
import sys
import json
import ast
import time
import shutil
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from core.logger import setup_logger

try:
    from bs4 import BeautifulSoup as _BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class SelfEvolution:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("evolution")
        self.base_dir = Path(__file__).resolve().parent.parent
        self.tools_dir = self.base_dir / "tools"
        self.tools_dir.mkdir(exist_ok=True)
        self.evolution_log = self.base_dir / "logs" / "evolution.json"
        self._stats = self._load_stats()

    def _stage_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _staging_path(self) -> Path:
        return self.base_dir / f".staging_{self._stage_id()}"

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
            "staging_commits": 0,
            "failed_stages": 0,
        }

    def _save_stats(self):
        self.evolution_log.parent.mkdir(exist_ok=True)
        self.evolution_log.write_text(json.dumps(self._stats, indent=2))

    def _git_branch_isolation(self, branch_name: str) -> bool:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            if r.returncode != 0:
                return False
            subprocess.run(
                ["git", "stash"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            r = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            if r.returncode == 0:
                self.logger.info(f"Git branch created: {branch_name}")
                return True
            self.logger.warning(f"Git branch creation failed: {r.stderr[:200]}")
            return False
        except Exception as e:
            self.logger.warning(f"Git isolation unavailable: {e}")
            return False

    def _git_merge_back(self, branch_name: str) -> bool:
        try:
            r = subprocess.run(
                ["git", "checkout", "master"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            if r.returncode != 0:
                return False
            r = subprocess.run(
                ["git", "merge", branch_name],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            if r.returncode == 0:
                self.logger.info(f"Merged branch: {branch_name}")
                return True
            self.logger.error(f"Merge failed: {r.stderr[:200]}")
            return False
        except Exception as e:
            self.logger.error(f"Git merge error: {e}")
            return False

    def _git_abort_branch(self, branch_name: str):
        try:
            subprocess.run(
                ["git", "checkout", "master"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.base_dir,
            )
            self.logger.info(f"Aborted and deleted branch: {branch_name}")
        except Exception as e:
            self.logger.warning(f"Branch cleanup error: {e}")

    def _verify_with_pytest(self) -> dict:
        test_dir = self.base_dir / "tests"
        if not test_dir.exists():
            return {"passed": True, "output": "No tests directory — skipping pytest"}
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-x", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.base_dir,
            )
            passed = r.returncode == 0
            return {
                "passed": passed,
                "output": (r.stdout + r.stderr)[-2000:],
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "TIMEOUT", "returncode": -1}
        except Exception as e:
            return {"passed": False, "output": str(e), "returncode": -1}

    def _verify_py_compile(self, file_paths: list[Path]) -> dict:
        for fp in file_paths:
            if not fp.exists():
                continue
            try:
                ast.parse(fp.read_text(encoding="utf-8"))
            except SyntaxError as e:
                return {"passed": False, "output": f"Syntax error in {fp.name}: {e}"}
        return {"passed": True, "output": "All files compile OK"}

    def _stage_file(self, source: Path, staging_path: Path) -> Path | None:
        staging_path.mkdir(parents=True, exist_ok=True)
        rel = source.relative_to(self.base_dir)
        staged = staging_path / rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, staged)
        return staged

    def _cleanup_staging(self, staging_path: Path):
        if staging_path.exists():
            shutil.rmtree(staging_path)

    def _signal_reload(self):
        try:
            import requests

            requests.post("http://127.0.0.1:5000/api/reload", timeout=5)
        except Exception:
            pass

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

        sp = self._staging_path()
        staged = self._stage_file(template, sp)
        content = (
            staged.read_text(encoding="utf-8")
            if staged
            else template.read_text(encoding="utf-8")
        )

        if new_html:
            if not HAS_BS4:
                self.logger.warning(
                    "BeautifulSoup not installed, falling back to string replacement"
                )
                if element_id in content:
                    content = content.replace(element_id, new_html)
                else:
                    self.logger.warning(f"Element '{element_id}' not found")
                    self._cleanup_staging(sp)
                    return False
            else:
                soup = _BeautifulSoup(content, "html.parser")
                target = soup.find(id=element_id)
                if target:
                    new_soup = _BeautifulSoup(new_html, "html.parser")
                    target.replace_with(new_soup)
                    content = str(soup)
                else:
                    self.logger.warning(f"Element id='{element_id}' not found")
                    self._cleanup_staging(sp)
                    return False
            self.logger.info(f"GUI modified: replaced element '{element_id}'")

        if new_css:
            if not HAS_BS4:
                style_end = content.find("</style>")
                if style_end > 0:
                    content = content[:style_end] + new_css + "\n" + content[style_end:]
            else:
                soup = _BeautifulSoup(content, "html.parser")
                style_tag = soup.find("style")
                if style_tag:
                    style_tag.string = (
                        style_tag.string + "\n" + new_css
                        if style_tag.string
                        else new_css
                    )
                    content = str(soup)

        if not new_html and not new_css:
            self.logger.warning(f"No changes specified for {element_id}")
            self._cleanup_staging(sp)
            return False

        compile_check = self._verify_py_compile([template])
        if not compile_check["passed"]:
            self.logger.error(
                f"GUI modification failed compile check: {compile_check['output']}"
            )
            self._cleanup_staging(sp)
            return False

        test_result = self._verify_with_pytest()
        if not test_result["passed"]:
            self.logger.error(
                f"GUI modification failed tests: {test_result['output'][:300]}"
            )
            self._cleanup_staging(sp)
            return False

        template.write_text(content, encoding="utf-8")
        self._cleanup_staging(sp)
        self._stats["gui_changes"].append(
            {"element": element_id, "timestamp": datetime.utcnow().isoformat()}
        )
        self._stats["evolution_generation"] += 1
        self._save_stats()
        return True

    def modify_own_source(self, agent_name: str, new_code: str) -> bool:
        agent_file = self.base_dir / "agents" / f"{agent_name}.py"
        if not agent_file.exists():
            self.logger.error(f"Agent file not found: {agent_name}.py")
            return False

        try:
            ast.parse(new_code)
        except SyntaxError as e:
            self.logger.error(f"Syntax error in modification: {e}")
            return False

        branch_name = f"feature/evolution-patch-{uuid.uuid4().hex[:8]}"
        used_git = self._git_branch_isolation(branch_name)
        sp = self._staging_path()

        staged = self._stage_file(agent_file, sp)
        staged.write_text(new_code, encoding="utf-8")

        if used_git:
            target = agent_file
        else:
            target = staged

        target.write_text(new_code, encoding="utf-8")

        compile_result = self._verify_py_compile([agent_file])
        test_result = self._verify_with_pytest()

        all_passed = compile_result["passed"] and test_result["passed"]

        if all_passed:
            if used_git:
                subprocess.run(
                    ["git", "add", str(agent_file.relative_to(self.base_dir))],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.base_dir,
                )
                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"evolution: {agent_name} auto-modification",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.base_dir,
                )
                merged = self._git_merge_back(branch_name)
                if merged:
                    self._stats["staging_commits"] += 1
                    self._signal_reload()
            else:
                shutil.copy2(staged, agent_file)

            self._cleanup_staging(sp)
            self._stats["self_modifications"].append(
                {
                    "agent": agent_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "tests_passed": True,
                }
            )
            self._stats["evolution_generation"] += 1
            self._save_stats()
            self.logger.info(f"Agent {agent_name} self-modified ({len(new_code)}b)")
            return True
        else:
            self._stats["failed_stages"] += 1
            self._save_stats()
            failure_log = f"Compile: {compile_result['output'][:200]} | Tests: {test_result['output'][:200]}"
            self.logger.error(
                f"Staging verification FAILED for {agent_name}: {failure_log}"
            )
            if used_git:
                self._git_abort_branch(branch_name)
            self._cleanup_staging(sp)
            return False

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
