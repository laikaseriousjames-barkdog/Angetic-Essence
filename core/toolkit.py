import os
import re
import sys
import json
import ast
import uuid
import asyncio
import subprocess
from pathlib import Path
from core.logger import setup_logger
from core.sandbox import Sandbox
from core.screen import ScreenController
from core.speaker import Speaker


def _sync_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()


class ToolKit:
    def __init__(self, work_dir: str | Path = None, sandbox: Sandbox = None, kali=None, config: dict = None):
        self.logger = setup_logger("toolkit")
        self.work_dir = Path(work_dir or Path(__file__).resolve().parent.parent)
        self.sandbox = sandbox or Sandbox(enabled=False)
        self.screen = ScreenController()
        self.speaker = Speaker()
        self.kali = kali
        self.config = config or {}
        
        adb_path = self.config.get("adb_path", "adb")
        try:
            from android.adb import ADBBridge
            self.adb = ADBBridge(adb_path)
        except Exception as e:
            self.logger.warning(f"Failed to initialize ADBBridge: {e}")
            self.adb = None

        try:
            from agents.selftaught import SelfEvolution
            self.evolution = SelfEvolution(self.config)
        except Exception as e:
            self.logger.warning(f"Failed to initialize SelfEvolution: {e}")
            self.evolution = None

    def read_file(self, path: str | Path) -> str:
        p = self.sandbox.resolve_read_path(path)
        if not p.exists():
            return f"[ERROR] File not found: {p}"
        content = p.read_text(encoding="utf-8", errors="replace")
        self.logger.info(f"read_file: {p} ({len(content)}b)")
        return content

    def write_file(self, path: str | Path, content: str) -> str:
        p = self.sandbox.resolve_write_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self.logger.info(f"write_file: {p} ({len(content)}b)")
        return f"Wrote {len(content)}b to {p}"

    def edit_file(self, path: str | Path, old_text: str, new_text: str) -> str:
        p = self.sandbox.resolve_write_path(path)
        content = self.read_file(str(p))
        if old_text not in content:
            return f"[ERROR] text not found in {p}"
        if content.count(old_text) > 1:
            return f"[ERROR] multiple matches for text in {p}"
        new_content = content.replace(old_text, new_text)
        return self.write_file(str(p), new_content)

    def search_files(self, pattern: str, path: str | Path = None) -> list[str]:
        base = Path(path) if path else self.work_dir
        matches = [str(p) for p in sorted(base.rglob(pattern))]
        self.logger.info(f"search_files: {pattern} -> {len(matches)} results")
        return matches

    def search_code(self, pattern: str, include: str = "*.py") -> list[dict]:
        results = []
        for p in self.work_dir.rglob(include):
            if "site-packages" in str(p) or "__pycache__" in str(p):
                continue
            try:
                for i, line in enumerate(
                    p.read_text(encoding="utf-8", errors="replace").split("\n"), 1
                ):
                    if re.search(pattern, line, re.IGNORECASE):
                        results.append(
                            {
                                "file": str(p.relative_to(self.work_dir)),
                                "line": i,
                                "text": line.strip()[:120],
                            }
                        )
            except Exception:
                pass
        self.logger.info(f"search_code: {pattern} -> {len(results)} results")
        return results

    async def web_fetch_async(self, url: str, timeout: int = 30) -> str:
        try:
            import urllib.request, urllib.error

            loop = asyncio.get_event_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            content = await loop.run_in_executor(
                None,
                lambda: (
                    urllib.request.urlopen(req, timeout=timeout)
                    .read()
                    .decode("utf-8", errors="replace")
                ),
            )
            self.logger.info(f"web_fetch: {url} ({len(content)}b)")
            return content[:10000]
        except Exception as e:
            return f"[ERROR] web_fetch: {e}"

    def web_fetch(self, url: str, timeout: int = 30) -> str:
        return _sync_run(self.web_fetch_async(url, timeout))

    async def web_search_async(self, query: str) -> str:
        try:
            import urllib.parse, urllib.request, urllib.error

            loop = asyncio.get_event_loop()
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html = await loop.run_in_executor(
                None,
                lambda: (
                    urllib.request.urlopen(req, timeout=15)
                    .read()
                    .decode("utf-8", errors="replace")
                ),
            )
            results = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html
            )[:5]
            formatted = (
                "\n".join(f"{r[1]} -> {r[0]}" for r in results)
                if results
                else "No results"
            )
            self.logger.info(f"web_search: {query} -> {len(results)} results")
            return formatted
        except Exception as e:
            return f"[ERROR] web_search: {e}"

    def web_search(self, query: str) -> str:
        return _sync_run(self.web_search_async(query))

    async def run_bash_async(self, command: str, timeout: int = 120) -> str:
        allowed, _ = self.sandbox.check_command(command)
        if not allowed:
            self.logger.warning(f"Sandbox blocked: {command[:80]}")
            return "Error: Command blocked by sandbox."

        self.logger.info(f"run_bash_async: {command[:120]}")
        
        env = os.environ.copy()
        if self.sandbox.enabled:
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"]:
                env.pop(key, None)
                
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.work_dir,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return (
                stdout.decode("utf-8", errors="replace")
                + "\n"
                + stderr.decode("utf-8", errors="replace")
            ).strip()
        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            return f"Error: Command timed out after {timeout}s"

    def run_bash(self, command: str, timeout: int = 120) -> dict:
        result_str = _sync_run(self.run_bash_async(command, timeout))
        if result_str.startswith("Error:"):
            return {"stdout": "", "stderr": result_str, "returncode": -1}
        return {"stdout": result_str, "stderr": "", "returncode": 0}

    def run_python(self, code: str, timeout: int = 30) -> str:
        return _sync_run(self._run_python_async(code, timeout))

    async def _run_python_async(self, code: str, timeout: int = 30) -> str:
        allowed, _ = self.sandbox.check_python_code(code)
        if not allowed:
            return "Error: Python code blocked by sandbox."

        self.logger.info(f"run_python: {len(code)}b")
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"Error: SyntaxError - {e}"

        script_name = f"temp_exec_{uuid.uuid4().hex[:8]}.py"
        sandbox_dir = str(self.sandbox.sandbox_dir)
        os.makedirs(sandbox_dir, exist_ok=True)
        script_path = os.path.join(sandbox_dir, script_name)

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            if (
                self.kali
                and self.kali.is_running
                and hasattr(self.kali, "_container_uuid")
            ):
                container_name = f"kali-agent-{self.kali._container_uuid[:8]}"
                cp_process = await asyncio.create_subprocess_exec(
                    "docker",
                    "cp",
                    script_path,
                    f"{container_name}:/tmp/{script_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await cp_process.communicate()

                process = await asyncio.create_subprocess_exec(
                    "docker",
                    "exec",
                    "-i",
                    container_name,
                    "python3",
                    f"/tmp/{script_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.DEVNULL,
                )
            else:
                env = os.environ.copy()
                if self.sandbox.enabled:
                    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"]:
                        env.pop(key, None)
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.DEVNULL,
                    env=env,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                output = (
                    stdout.decode("utf-8", errors="replace")
                    + "\n"
                    + stderr.decode("utf-8", errors="replace")
                ).strip()
                return output if output else "(no output)"
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                return f"Error: Python execution timed out after {timeout} seconds."

        except Exception as e:
            return f"Error executing python: {str(e)}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)

    def list_dir(self, path: str | Path = "") -> list[str]:
        p = self.sandbox.resolve_read_path(path) if path else self.work_dir
        if not p.exists():
            return [f"[ERROR] directory not found: {p}"]
        return sorted(os.listdir(p))

    def install_package(self, package: str) -> dict:
        return _sync_run(
            self.run_bash_async(
                f"{sys.executable} -m pip install {package}", timeout=120
            )
        )

    def set_sandbox(self, sandbox: Sandbox):
        self.sandbox = sandbox
        self.logger.info(
            f"ToolKit sandbox {'enabled' if sandbox.enabled else 'disabled'}"
        )

    def screenshot(self, path: str = None) -> str:
        return self.screen.screenshot(path)

    def screenshot_base64(self) -> str:
        return self.screen.screenshot_base64()

    def mouse_move(self, x: int, y: int) -> str:
        return self.screen.mouse_move(x, y)

    def mouse_click(self, x: int = None, y: int = None, button: str = "left") -> str:
        return self.screen.mouse_click(x, y, button)

    def mouse_drag(self, x: int, y: int) -> str:
        return self.screen.mouse_drag(x, y)

    def mouse_position(self) -> dict:
        return self.screen.mouse_position()

    def scroll(self, clicks: int = -3) -> str:
        return self.screen.scroll(clicks)

    def type_text(self, text: str) -> str:
        return self.screen.type_text(text)

    def press_key(self, key: str) -> str:
        return self.screen.press_key(key)

    def hotkey(self, *keys: str) -> str:
        return self.screen.hotkey(*keys)

    def screen_size(self) -> dict:
        return self.screen.screen_size()

    def speak(self, text: str, rate: int = 0, volume: int = 100) -> str:
        return self.speaker.speak(text, rate, volume)

    def speak_async(self, text: str) -> str:
        return self.speaker.speak_async(text)

    def beep(self, frequency: int = 440, duration_ms: int = 300) -> str:
        return self.speaker.beep(frequency, duration_ms)

    def play_wav(self, path: str) -> str:
        return self.speaker.play_wav(path)

    def kali_exec(self, command: str) -> str:
        if not self.kali or not self.kali.is_running:
            return "[ERROR] Kali VM not running"
        ok = self.kali.exec_command(command)
        return "Command sent to Kali VM" if ok else "[ERROR] Failed to send command to Kali VM"

    def kali_install(self, packages: list) -> str:
        if not self.kali or not self.kali.is_running:
            return "[ERROR] Kali VM not running"
        ok = self.kali.install_tools(packages)
        return "Installation started in Kali VM" if ok else "[ERROR] Failed to start installation in Kali VM"

    def adb_setup(self) -> str:
        try:
            import urllib.request
            import zipfile
            import yaml
            
            target_dir = self.work_dir / "android-tools"
            target_dir.mkdir(exist_ok=True)
            zip_path = target_dir / "platform-tools.zip"
            
            self.logger.info("Downloading Android SDK platform-tools...")
            url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
            urllib.request.urlretrieve(url, str(zip_path))
            
            self.logger.info("Extracting platform-tools...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            if zip_path.exists():
                zip_path.unlink()
                
            adb_exe = target_dir / "platform-tools" / "adb.exe"
            if not adb_exe.exists():
                return "[ERROR] ADB executable not found after extraction."
                
            config_path = self.work_dir / "config.yaml"
            cfg = {}
            if config_path.exists():
                cfg = yaml.safe_load(config_path.read_text()) or {}
            
            cfg["adb_path"] = str(adb_exe.resolve())
            config_path.write_text(yaml.dump(cfg))
            
            os.environ["ADB_PATH"] = str(adb_exe.resolve())
            
            from android.adb import ADBBridge
            self.adb = ADBBridge(str(adb_exe.resolve()))
            
            return f"ADB successfully downloaded and configured at {adb_exe}"
            
        except Exception as e:
            return f"[ERROR] ADB Setup Failed: {e}"

    def adb_devices(self) -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            devs = self.adb.devices()
            return json.dumps(devs)
        except Exception as e:
            return f"[ERROR] ADB Devices: {e}"

    def adb_shell(self, command: str, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.shell(command, device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Shell: {e}"

    def adb_root_check(self, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            rooted = self.adb.is_rooted(device)
            return "rooted" if rooted else "not rooted"
        except Exception as e:
            return f"[ERROR] ADB Root Check: {e}"

    def adb_root_attempt(self, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.attempt_root(device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Root Attempt: {e}"

    def adb_screenshot(self, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.screenshot(device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Screenshot: {e}"

    def adb_install(self, apk_path: str, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.install(apk_path, device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Install: {e}"

    def adb_uninstall(self, package: str, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.uninstall(package, device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Uninstall: {e}"

    def adb_device_info(self, device: str = "") -> str:
        if not self.adb:
            return "[ERROR] ADB bridge not initialized"
        try:
            res = self.adb.device_info(device)
            return json.dumps(res)
        except Exception as e:
            return f"[ERROR] ADB Device Info: {e}"

    def create_tool(self, name: str, description: str, code: str) -> str:
        if not self.evolution:
            return "[ERROR] SelfEvolution not initialized"
        try:
            res = self.evolution.create_tool(name, description, code)
            return f"Tool created at: {res}" if res else "[ERROR] Failed to create tool (syntax error or validation failed)"
        except Exception as e:
            return f"[ERROR] Create Tool: {e}"

    def modify_gui(self, element_id: str, html: str = None, css: str = None) -> str:
        if not self.evolution:
            return "[ERROR] SelfEvolution not initialized"
        try:
            ok = self.evolution.modify_gui(element_id, new_html=html, new_css=css)
            return "GUI modified successfully" if ok else "[ERROR] GUI modification failed (validation or tests failed)"
        except Exception as e:
            return f"[ERROR] Modify GUI: {e}"

    def modify_agent_source(self, agent: str, code: str) -> str:
        if not self.evolution:
            return "[ERROR] SelfEvolution not initialized"
        try:
            ok = self.evolution.modify_own_source(agent, code)
            return f"Agent {agent} source modified successfully" if ok else f"[ERROR] Modification of agent {agent} failed (syntax or test check failed)"
        except Exception as e:
            return f"[ERROR] Modify Agent Source: {e}"

    def get_available_tools(self) -> str:
        sb_status = (
            "ENABLED (read-only commands, sandboxed writes)"
            if self.sandbox.enabled
            else "DISABLED (full access)"
        )
        return f"""Available tools (sandbox: {sb_status}):
- read_file(path) — read any file
- write_file(path, content) — write any file (sandbox redirects writes to sandbox/ in sandbox mode)
- edit_file(path, old_text, new_text) — edit a file
- search_files(pattern) — glob for files (*.py, *.txt, etc)
- search_code(pattern, include) — grep for text in code files
- web_fetch(url) — fetch a web page
- web_search(query) — search the web
- run_bash(command) — run a shell command (read-only in sandbox mode)
- run_python(code) — run Python code (no os/subprocess/socket in sandbox mode)
- list_dir(path) — list directory contents
- install_package(package) — pip install
- screenshot(path) — capture screen to file
- screenshot_base64() — capture screen as base64
- mouse_move(x, y) — move mouse cursor
- mouse_click(x, y, button) — click mouse at position
- mouse_drag(x, y) — drag mouse
- mouse_position() — get cursor position
- scroll(clicks) — scroll mouse wheel
- type_text(text) — type text at cursor
- press_key(key) — press a keyboard key
- hotkey(key1, key2) — press keyboard combination
- screen_size() — get screen dimensions
- speak(text) — speak text aloud via TTS
- speak_async(text) — speak without waiting
- beep(freq, ms) — play a beep sound
- play_wav(path) — play a WAV audio file
- kali_exec(command) — execute a shell command in the Kali Linux VM
- kali_install(packages) — install packages in the Kali Linux VM (expects a list of package strings)
- adb_setup() — download and install ADB. YOU MUST ASK THE USER FOR PERMISSION IN PLAIN TEXT AND WAIT FOR THEIR APPROVAL BEFORE CALLING THIS TOOL.
- adb_devices() — list connected Android devices
- adb_shell(command, device) — run a shell command on an Android device via ADB
- adb_root_check(device) — check if an Android device has root access
- adb_root_attempt(device) — attempt to root a compatible Android device
- adb_screenshot(device) — capture a screenshot of the Android device
- adb_install(apk_path, device) — install an APK on the Android device
- adb_uninstall(package, device) — uninstall a package from the Android device
- adb_device_info(device) — get Android device hardware/OS metadata
- create_tool(name, description, code) — write a new tool script to the tools/ directory
- modify_gui(element_id, html, css) — modify the dashboard HTML/CSS
- modify_agent_source(agent, code) — edit the source code of an agent in agents/ directory
"""
