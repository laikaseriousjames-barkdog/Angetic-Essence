"""Reverse engineering plugin — binary analysis, disassembly, vulnerability scanning."""

import re
import json
import asyncio
from pathlib import Path
from plugins import PluginAgent


class ReverseEngineer(PluginAgent):
    def __init__(self, config: dict = None, llm=None, kali=None):
        super().__init__("Reverse_Engineer", config or {}, llm, kali)
        self.description = "Binary analysis and reverse engineering — file fingerprinting, string extraction, entropy analysis, vulnerability pattern matching."
        self.version = "1.1.0"
        self.author = "Angetic Essence"
        self._watch_dirs = []
        self._reports = []

    async def on_load(self):
        self.logger.info(f"{self.name} ready — binary analysis engine active")

    async def _file_info(self, path: str) -> dict:
        info = {"path": path, "type": "unknown", "strings": [], "entropy": 0.0}
        try:
            proc = await asyncio.create_subprocess_exec(
                "file",
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            info["type"] = stdout.decode("utf-8", errors="replace").strip()
        except Exception as e:
            info["type"] = f"file error: {e}"
        return info

    async def _extract_strings(self, path: str, min_len: int = 6) -> list[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "strings",
                "-n",
                str(min_len),
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            raw = stdout.decode("utf-8", errors="replace")
            interesting = [
                s
                for s in raw.split("\n")
                if any(
                    k in s.lower()
                    for k in [
                        "password",
                        "key",
                        "token",
                        "secret",
                        "admin",
                        "root",
                        "http://",
                        "https://",
                        "api.",
                        "config",
                        ".exe",
                        ".dll",
                        "debug",
                        "bypass",
                        "crack",
                    ]
                )
            ]
            return interesting[:30]
        except Exception:
            return []

    async def _analyze_binary(self, path: str) -> str | None:
        info = await self._file_info(path)
        strings = await self._extract_strings(path)
        if not strings:
            return None
        report = {"file": path, "type": info["type"], "interesting_strings": strings}
        self._reports.append(report)

        if self.llm:
            prompt = (
                f"Analyze this binary analysis report:\n"
                f"File: {path}\n"
                f"Type: {info['type']}\n"
                f"Interesting strings found:\n"
                + "\n".join(strings[:20])
                + "\n\nWhat is this binary likely doing? Any security concerns?"
            )
            analysis = await self.llm.complete_async(
                prompt, max_tokens=300, temperature=0.3
            )
            return f"[{self.name}] Analysis of {Path(path).name}: {analysis[:250]}"
        return f"[{self.name}] Scanned {Path(path).name} — {len(strings)} interesting strings"

    async def on_tick(self, cycle: int) -> str | None:
        if cycle % 10 == 0 and self._watch_dirs:
            binaries = []
            for d in self._watch_dirs:
                p = Path(d)
                if p.exists():
                    binaries.extend(
                        str(f)
                        for f in p.rglob("*")
                        if f.is_file()
                        and f.stat().st_size < 10 * 1024 * 1024
                        and not f.suffix
                        in {".py", ".txt", ".md", ".log", ".json", ".yaml", ".yml"}
                    )
            if binaries:
                results = await asyncio.gather(
                    *(self._analyze_binary(b) for b in binaries[:5])
                )
                valid = [r for r in results if r]
                if valid:
                    return valid[0]
        return None

    async def add_watch_dir(self, directory: str):
        resolved = str(Path(directory).resolve())
        self._watch_dirs.append(resolved)
        self.logger.info(f"Added RE watch directory: {resolved}")

    def get_reports(self) -> list:
        return self._reports[-20:]
