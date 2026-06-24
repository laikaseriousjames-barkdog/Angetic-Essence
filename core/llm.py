import os
import sys
import json
import time
import atexit
import asyncio
import subprocess
import threading
import urllib.request
import urllib.error
from pathlib import Path
from core.logger import setup_logger

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )

    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False


def _remote_retry(fn):
    if not HAS_TENACITY:
        return fn

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (urllib.error.HTTPError, urllib.error.URLError, OSError)
        ),
        reraise=True,
    )
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


def _sync_run(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, coro).result()


class LLMClient:
    def __init__(self, model_name: str = None, config: dict = None, memory=None):
        self.config = config or {}
        self.logger = setup_logger("llm")
        self._memory = memory
        self._model_name = model_name or self.config.get(
            "model", "openai"
        )
        self._provider = self.config.get("provider", "pollinations")
        self._process = None
        self._port = 8081
        self._base_url = f"http://127.0.0.1:{self._port}"
        self._lock = threading.Lock()
        self._loaded = False
        self._llama_dir = Path(__file__).resolve().parent.parent / "llama-bin"
        self._server_exe = self._llama_dir / "llama-server.exe"
        self.logger.info(f"LLM: {self._model_name} | provider: {self._provider}")

    @property
    def is_loaded(self):
        return self._loaded

    def load(self):
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self._provider != "local":
                self._loaded = True
                return
            model_path = self._model_name
            if not model_path.endswith(".gguf"):
                self.logger.info(f"Non-GGUF model configured ({model_path})")
                self._loaded = True
                return
            if not os.path.exists(model_path):
                self.logger.error(f"Model not found: {model_path}")
                return
            if not self._server_exe.exists():
                self.logger.error(f"llama-server.exe not found at {self._server_exe}")
                return
            self.logger.info(f"Starting llama-server with {model_path}...")
            try:
                self._process = subprocess.Popen(
                    [
                        str(self._server_exe),
                        "-m",
                        model_path,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(self._port),
                        "-c",
                        "4096",
                        "--mlock",
                        "-lv",
                        "0",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(self._llama_dir),
                )
                self._wait_for_server(60)
                self._loaded = True
                self.logger.info("llama-server ready")
                atexit.register(self._cleanup)
            except Exception as e:
                self.logger.error(f"Failed to start server: {e}")
                self._cleanup()

    def _wait_for_server(self, timeout_sec: int = 60):
        for i in range(timeout_sec):
            try:
                req = urllib.request.Request(f"{self._base_url}/health")
                with urllib.request.urlopen(req, timeout=2):
                    return True
            except Exception:
                time.sleep(1)
        self.logger.warning("Server health check timeout")

    def _cleanup(self):
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
            self._loaded = False

    def _call_local(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> str:
        self.load()
        if not self._loaded or not self._process:
            return self._fallback_chat(messages, max_tokens, temperature)
        payload = json.dumps(
            {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        ).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"{self._base_url}/v1/chat/completions",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                self.logger.warning(f"Local chat attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2)
        return self._fallback_chat(messages, max_tokens, temperature)

    async def _call_local_async(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> str:
        self.load()
        if not self._loaded or not self._process:
            return self._fallback_chat(messages, max_tokens, temperature)
        payload = json.dumps(
            {"messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        ).encode()
        loop = asyncio.get_event_loop()
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"{self._base_url}/v1/chat/completions",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                resp = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=120)
                )
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                self.logger.warning(f"Local chat attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        return self._fallback_chat(messages, max_tokens, temperature)

    def _http_open(self, req: urllib.request.Request) -> object:
        if HAS_TENACITY:
            return self._http_open_with_retry(req)
        return urllib.request.urlopen(req, timeout=60)

    @_remote_retry
    def _http_open_with_retry(self, req: urllib.request.Request) -> object:
        return urllib.request.urlopen(req, timeout=60)

    async def _http_open_async(self, req: urllib.request.Request) -> object:
        loop = asyncio.get_event_loop()
        if HAS_TENACITY:
            for attempt in range(3):
                try:
                    return await loop.run_in_executor(
                        None, lambda: urllib.request.urlopen(req, timeout=60)
                    )
                except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                    if isinstance(e, urllib.error.HTTPError) and e.code not in (
                        429,
                        500,
                        502,
                        503,
                        504,
                    ):
                        raise
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
        return await loop.run_in_executor(
            None, lambda: urllib.request.urlopen(req, timeout=60)
        )

    async def _call_remote_async(
        self, url: str, body: bytes, headers: dict, timeout: int = 60
    ) -> str:
        loop = asyncio.get_event_loop()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        resp = await self._http_open_async(req)
        data = json.loads(resp.read())
        return data

    def _record_spend(self, prompt_tokens: int, completion_tokens: int):
        if self._memory:
            try:
                self._memory.record_spend(
                    provider=self._provider,
                    model=self._model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            except Exception:
                pass

    async def chat_async(
        self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7
    ) -> str:
        provider = self._provider
        if provider == "local":
            return await self._call_local_async(messages, max_tokens, temperature)

        key_map = {
            "openai": (
                "OPENAI_API_KEY",
                "https://api.openai.com/v1/chat/completions",
                {"model": self._model_name or "gpt-4o-mini"},
            ),
            "openrouter": (
                "OPENROUTER_API_KEY",
                "https://openrouter.ai/api/v1/chat/completions",
                {"model": self._model_name or "openai/gpt-4o-mini"},
            ),
        }

        if provider == "pollinations":
            body = json.dumps({
                "model": self._model_name or "openai",
                "messages": messages,
                "temperature": temperature
            }).encode()
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            try:
                data = await self._call_remote_async("https://text.pollinations.ai/openai/chat/completions", body, headers)
                # No token usage provided by pollinations, so we just return the text
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[Pollinations error: {e}]"

        if provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                return "[ERROR: No ANTHROPIC_API_KEY set]"
            sys_msg = ""
            msgs = []
            for m in messages:
                if m["role"] == "system":
                    sys_msg = m["content"]
                else:
                    msgs.append({"role": m["role"], "content": m["content"]})
            body = json.dumps(
                {
                    "model": self._model_name or "claude-3-haiku-20240307",
                    "max_tokens": max_tokens,
                    "system": sys_msg or "You are a helpful assistant.",
                    "messages": msgs,
                    "temperature": temperature,
                }
            ).encode()
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            try:
                data = await self._call_remote_async(
                    "https://api.anthropic.com/v1/messages", body, headers
                )
                pt = data.get("usage", {}).get("input_tokens", 0)
                ct = data.get("usage", {}).get("output_tokens", 0)
                self._record_spend(pt, ct)
                return data["content"][0]["text"]
            except Exception as e:
                return f"[Anthropic error: {e}]"

        if provider == "google":
            key = os.environ.get("GOOGLE_API_KEY", "")
            if not key:
                return "[ERROR: No GOOGLE_API_KEY set]"
            model = self._model_name or "gemini-2.0-flash"
            contents = []
            system_text = ""
            for m in messages:
                if m["role"] == "system":
                    system_text = m["content"]
                else:
                    role = "model" if m["role"] == "assistant" else m["role"]
                    contents.append({"role": role, "parts": [{"text": m["content"]}]})
            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            }
            if system_text:
                payload["system_instruction"] = {"parts": [{"text": system_text}]}
            body = json.dumps(payload).encode()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            try:
                data = await self._call_remote_async(url, body, headers)
                usage = data.get("usageMetadata", {})
                pt = usage.get("promptTokenCount", 0)
                ct = usage.get("candidatesTokenCount", 0)
                self._record_spend(pt, ct)
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                return f"[Google error: {e}]"

        if provider in key_map:
            env_key, api_url, defaults = key_map[provider]
            key = os.environ.get(env_key, "")
            if not key:
                if provider == "openrouter":
                    return "[ERROR: No OpenRouter API key found. Please open the Dashboard Settings to configure your API key, choose a different provider, or connect a local model.]"
                return f"[ERROR: No {env_key} set]"
            body_dict = {
                **defaults,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            body = json.dumps(body_dict).encode()
            auth_header = f"Bearer {key}"
            headers = {"Authorization": auth_header, "Content-Type": "application/json"}
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/angetic-essence"
            try:
                data = await self._call_remote_async(api_url, body, headers)
                usage = data.get("usage", {})
                pt = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                ct = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                self._record_spend(pt, ct)
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[{provider.title()} error: {e}]"

        return self._fallback_chat(messages, max_tokens, temperature)

    def chat(
        self, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.7
    ) -> str:
        return _sync_run(self.chat_async(messages, max_tokens, temperature))

    def _fallback_chat(self, messages, max_tokens, temperature):
        self.logger.info("Using fallback chat")
        return f"[Model unavailable: {self._model_name}]"

    def complete(
        self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> str:
        return self.chat([{"role": "user", "content": prompt}], max_tokens, temperature)

    async def complete_async(
        self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> str:
        return await self.chat_async(
            [{"role": "user", "content": prompt}], max_tokens, temperature
        )

    def generate_code(self, prompt: str, language: str = "python") -> str:
        return self.chat(
            [
                {
                    "role": "system",
                    "content": f"You are an expert {language} developer. Output ONLY valid {language} code. No explanations.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
            temperature=0.3,
        )

    def generate_tests(self, source_code: str) -> str:
        return self.chat(
            [
                {
                    "role": "system",
                    "content": "You are a QA engineer. Generate pytest unit tests for the given code.",
                },
                {
                    "role": "user",
                    "content": f"Generate pytest tests for:\n\n{source_code[:2000]}",
                },
            ],
            max_tokens=2048,
            temperature=0.3,
        )

    def analyze_logs(self, log_content: str) -> str:
        return self.chat(
            [
                {
                    "role": "system",
                    "content": "Analyze these logs and identify bugs, errors, and optimization opportunities.",
                },
                {"role": "user", "content": f"Logs:\n{log_content[:3000]}"},
            ],
            max_tokens=1024,
            temperature=0.5,
        )

    def suggest_fix(self, error: str, code: str) -> str:
        return self.chat(
            [
                {
                    "role": "system",
                    "content": "You are a debugger. Identify the bug and output the fixed code.",
                },
                {"role": "user", "content": f"Error:\n{error}\n\nCode:\n{code[:2000]}"},
            ],
            max_tokens=2048,
            temperature=0.3,
        )
