# Agent Marketplace — Plugin Development Guide

## Overview

The Agent Marketplace allows third-party developers to create and sell plugin agents that extend Angetic Essence's capabilities. Plugins hot-discover via subclass scanning of `PluginAgent` in the `plugins/` directory.

## Creating a Plugin

### 1. File placement

Create a `.py` file in the `plugins/` directory (or a subdirectory). Your file must contain a class that subclasses `PluginAgent`.

### 2. Base class

```python
# plugins/my_agent.py
from plugins import PluginAgent

class MySpecialist(PluginAgent):
    def __init__(self, config: dict = None, llm=None, kali=None):
        super().__init__("My_Specialist", config or {}, llm, kali)
        self.description = "What your agent does"
        self.version = "1.0.0"
        self.author = "Your Name"
```

### 3. Hooks

| Hook | Purpose |
|------|---------|
| `async on_load()` | Called once at startup. Initialize resources. |
| `async on_tick(cycle: int) -> str \| None` | Called every main loop cycle. Return a string to log output. |

### 4. Available services

- `self.llm` — `LLMClient` instance for AI completions
- `self.kali` — `KaliVM` instance for running Kali Linux tools
- `self.logger` — Pre-configured logger for your plugin
- `self.work_dir` — Project root `Path`

### 5. Example

```python
from plugins import PluginAgent

class SentinelAgent(PluginAgent):
    def __init__(self, config=None, llm=None, kali=None):
        super().__init__("Sentinel", config or {}, llm, kali)
        self.description = "Monitors system health and alerts on anomalies"
        self.version = "1.0.0"
        self.author = "Your Name"

    async def on_load(self):
        self.logger.info("Sentinel online")

    async def on_tick(self, cycle: int) -> str | None:
        if cycle % 10 == 0:
            return f"[Sentinel] Health check passed (cycle {cycle})"
        return None
```

## Selling Plugins

### Distribution

1. Package your plugin as a single `.py` file or a directory with `__init__.py`
2. Each plugin must expose exactly one `PluginAgent` subclass
3. Version your plugin using `self.version` (semver recommended)

### Listing

- Submit your plugin via the Angetic Essence developer portal
- Include: name, description, version, author, price (USD)
- All plugins undergo automated sandbox review for malicious patterns

### Pricing tiers

| Tier | Commission | Notes |
|------|-----------|-------|
| Free | 0% | Open-source, no monetization |
| Paid ($1–$50) | 30% | One-time purchase |
| Subscription ($1–$10/mo) | 25% | Recurring via license server |

### Licensing

Each purchased plugin receives an RSA-signed license key validated at load time. See `core/licensing.py` and `license_server/` for the validation infrastructure.

## Technical constraints

- Plugins run in the same process as the agent loop — no sandbox isolation yet
- Do NOT use blocking I/O in `on_tick`; use `asyncio` patterns
- Maximum `on_tick` execution time: 30 seconds (enforced by main loop)
- Plugin `__init__` must accept `config=None, llm=None, kali=None` as keyword args
- Do NOT import from `core.base_agent` or `core.toolkit` — use `self.llm` and `self.kali`

## Marketplace API

Dashboard endpoint `/api/plugins` returns metadata for all loaded plugins:

```json
{"plugins": [{"name": "...", "description": "...", "version": "...", "author": "..."}], "count": 2}
```
