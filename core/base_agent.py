import json
import asyncio
from pathlib import Path
from core.logger import setup_logger
from core.llm import LLMClient
from core.toolkit import ToolKit
from core.sandbox import Sandbox
from core.memory import MemoryManager


def _sync_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _get_spend_limit(config: dict) -> float:
    return float(config.get("max_daily_spend", 0.0)) or 5.0


class BaseAgent:
    def __init__(self, name: str, config: dict, llm: LLMClient = None, kali=None):
        self.name = name
        self.config = config
        self.logger = setup_logger(name)
        self.llm = llm or LLMClient(config=config.get("llm", {}), memory=self.memory)
        import sys
        if getattr(sys, "frozen", False):
            self.work_dir = Path(sys.executable).parent.resolve()
        else:
            self.work_dir = Path(__file__).resolve().parent.parent
        self.kali = kali
        sb_enabled = config.get("sandbox", {}).get("enabled", False)
        self.toolkit = ToolKit(self.work_dir, Sandbox(enabled=sb_enabled), kali=kali, config=config)
        self.memory = MemoryManager()
        self._max_spend = _get_spend_limit(config.get("cost", {}))
        context = self.memory.load_context(self.name)
        if context:
            self.logger.info(f"Restored {len(context)} context messages from memory")

    def _check_spend(self) -> bool:
        under = self.memory.check_spend_limit(self._max_spend)
        if not under:
            self.logger.warning(
                f"Daily spend ${self.memory.get_daily_spend():.2f} exceeds limit ${self._max_spend:.2f} — agent paused"
            )
        return under

    def kali_exec(self, command: str) -> dict | None:
        if not self.kali or not self.kali.is_running:
            return {"error": "Kali VM not running"}
        ok = self.kali.exec_command(command)
        return {"status": "sent" if ok else "failed"}

    def kali_install(self, packages: list[str]) -> dict | None:
        if not self.kali or not self.kali.is_running:
            return {"error": "Kali VM not running"}
        ok = self.kali.install_tools(packages)
        return {"status": "installing" if ok else "failed"}

    def execute_shell(self, command: str, timeout: int = 120) -> dict:
        """Execute shell command in the Kali Cyberdeck container and stream output via WebSocket."""
        from core.sandbox import get_or_create_kali_container
        from core.socket_manager import socketio

        container = get_or_create_kali_container()
        if not container:
            result = {"stdout": "", "stderr": "Error: Could not get Kali container", "returncode": 1}
            if socketio:
                socketio.emit('cyberdeck_stream', {'agent': self.name, 'command': command, 'output': result["stderr"]})
            return result
        try:
            exec_result = container.exec_run(f'bash -c "{command}"', timeout=timeout)
            stdout = exec_result.output.decode('utf-8') if exec_result.output else ""
            result = {"stdout": stdout, "stderr": "", "returncode": exec_result.exit_code}
            if socketio:
                socketio.emit('cyberdeck_stream', {'agent': self.name, 'command': command, 'output': stdout})
            return result
        except Exception as e:
            result = {"stdout": "", "stderr": str(e), "returncode": 1}
            if socketio:
                socketio.emit('cyberdeck_stream', {'agent': self.name, 'command': command, 'output': str(e)})
            return result

    def write_file(self, filepath: str | Path, content: str) -> str:
        return self.toolkit.write_file(filepath, content)

    def read_file(self, filepath: str | Path) -> str:
        return self.toolkit.read_file(filepath)

    def edit_file(self, filepath: str | Path, old_text: str, new_text: str) -> str:
        return self.toolkit.edit_file(filepath, old_text, new_text)

    def search_files(self, pattern: str) -> list[str]:
        return self.toolkit.search_files(pattern)

    def search_code(self, pattern: str, include: str = "*.py") -> list[dict]:
        return self.toolkit.search_code(pattern, include)

    def web_fetch(self, url: str) -> str:
        return self.toolkit.web_fetch(url)

    def web_search(self, query: str) -> str:
        return self.toolkit.web_search(query)

    def run_python(self, code: str) -> dict:
        return self.toolkit.run_python(code)

    def install_package(self, package: str) -> dict:
        return self.toolkit.install_package(package)

    def _execute_tool_plan(self, plan_text: str) -> tuple:
        return _sync_run(self._execute_tool_plan_async(plan_text))

    async def _execute_tool_plan_async(self, plan_text: str) -> tuple:
        import re
        plan_text = plan_text.strip()
        
        if plan_text.startswith("[Model unavailable:"):
            self.memory.save_message(self.name, "assistant", plan_text)
            return plan_text, plan_text
            
        # More robust extraction for smaller LLMs that don't obey strict JSON formatting
        match = re.search(r'(\{.*\})', plan_text, re.DOTALL)
        clean_text = match.group(1) if match else plan_text.strip()

        try:
            plan = json.loads(clean_text)
            tool_call = plan.get("tool_call", {})
            tool_name = tool_call.get("name")
            args = tool_call.get("arguments", {})
            thought = plan.get("thought", "")

            if thought:
                self.logger.info(f"{self.name} reasoning: {thought[:200]}")

            if not tool_name or tool_name.lower() == "none":
                result_text = plan.get("result", "No tool executed.")
                self.memory.save_message(
                    self.name,
                    "assistant",
                    f"{thought}\n{result_text}" if thought else result_text,
                )
                return result_text, thought

            # --- SECURITY POLICY CHECK ---
            TOOL_PERMISSIONS = {
                "run_bash": "shell_execution",
                "run_bash_async": "shell_execution",
                "kali_exec": "shell_execution",
                "adb_shell": "shell_execution",
                "web_fetch": "network_bridge",
                "web_fetch_async": "network_bridge",
                "web_search": "network_bridge",
                "web_search_async": "network_bridge",
                "write_file": "file_system_write",
                "edit_file": "file_system_write",
                "create_tool": "file_system_write",
                "modify_gui": "file_system_write",
                "modify_agent_source": "file_system_write",
                "install_package": "file_system_write"
            }
            category = TOOL_PERMISSIONS.get(tool_name)
            if category:
                from core.licensing import is_licensed
                if not is_licensed() and category == "shell_execution":
                    error_msg = f"License Violation: Tool '{tool_name}' requires a Pro License Key. Standard Freemium mode locks shell execution, Kali Linux, and ADB automation."
                    self.logger.warning(error_msg)
                    self.memory.save_message(self.name, "assistant", error_msg)
                    return error_msg, thought

                from core.security import policy_engine
                persona = {"developer": "Knuth", "tester": "Lovelace", "critic": "Turing"}.get(self.name, self.name)
                policy_engine.reload()
                if not policy_engine.check_permission(persona, category):
                    error_msg = f"Security Violation: Agent '{persona}' is not permitted to perform '{category}' action via tool '{tool_name}'."
                    self.logger.warning(error_msg)
                    self.memory.save_message(self.name, "assistant", error_msg)
                    return error_msg, thought

            tool_fn_async = getattr(self.toolkit, tool_name + "_async", None)
            tool_fn = getattr(self.toolkit, tool_name, None)

            if tool_fn_async:
                res = (
                    await tool_fn_async(**args)
                    if isinstance(args, dict)
                    else await tool_fn_async(args)
                )
            elif tool_fn:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(
                    None,
                    lambda: (
                        tool_fn(**args) if isinstance(args, dict) else tool_fn(args)
                    ),
                )
            else:
                error_msg = f"Error: Tool '{tool_name}' not found."
                self.memory.save_message(self.name, "assistant", error_msg)
                return error_msg, thought

            result_str = str(res)[:500]
            self.memory.save_message(
                self.name, "assistant", f"Tool [{tool_name}] -> {result_str}"
            )
            return result_str, thought

        except json.JSONDecodeError as e:
            error_msg = f"System Error: Failed to parse JSON tool schema. Ensure output is strictly JSON. Error: {str(e)}"
            self.memory.save_message(self.name, "assistant", error_msg)
            return error_msg, ""

        except Exception as e:
            error_msg = f"System Error during tool execution: {str(e)}"
            self.memory.save_message(self.name, "assistant", error_msg)
            return error_msg, ""

    def think(self, task: str) -> str:
        result, thought = _sync_run(self.athink(task))
        return result

    async def athink(self, task: str) -> tuple:
        if not self._check_spend():
            return "[PAUSED: Daily spend limit reached]", "Spend limit exceeded"

        self.logger.info(f"{self.name} reasoning about: {task[:120]}")
        tools_desc = self.toolkit.get_available_tools()

        messages = self.memory.load_context(self.name, limit=10)
        context_block = ""
        if messages:
            context_block = "\n".join(
                f"[{m['role']}]: {m['content'][:200]}" for m in messages
            )

        prompt = f"""You are {self.name}, an autonomous agent.
Available tools:
{tools_desc}

Recent context:
{context_block or "No prior context."}

Task: {task}

You MUST respond with a strictly valid JSON object matching this schema. Do not output markdown code blocks or any surrounding text.
{{
    "thought": "Your internal reasoning about the current state and next steps",
    "tool_call": {{
        "name": "name_of_tool_to_use",
        "arguments": {{
            "arg_name": "arg_value"
        }}
    }}
}}
If no tool is needed, set "name" to "none" and "arguments" to {{}}.
"""
        response = await asyncio.to_thread(
            self.llm.complete, prompt, max_tokens=2048, temperature=0.3
        )
        result, thought = await self._execute_tool_plan_async(response)
        self.memory.save_message(self.name, "user", task[:500])
        self.memory.save_message(self.name, "assistant", result[:500])
        return result, thought
