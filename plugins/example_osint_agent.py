"""OSINT reconnaissance plugin — domain research, passive recon, data aggregation."""

import re
import json
import asyncio
from plugins import PluginAgent


class OSINTSpecialist(PluginAgent):
    def __init__(self, config: dict = None, llm=None, kali=None):
        super().__init__("OSINT_Specialist", config or {}, llm, kali)
        self.description = "Automated OSINT reconnaissance — domain research, WHOIS lookups, DNS enumeration, and public data aggregation."
        self.version = "1.1.0"
        self.author = "Angetic Essence"
        self._targets = []
        self._findings = []

    async def on_load(self):
        self.logger.info(f"{self.name} online — OSINT recon engine ready")

    async def _whois(self, domain: str) -> str:
        if not self.kali or not self.kali.is_running:
            return "KaliVM unavailable"
        try:
            proc = await asyncio.create_subprocess_exec(
                "wsl",
                "--",
                "whois",
                domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return stdout.decode("utf-8", errors="replace")[:2000]
        except Exception as e:
            return f"whois error: {e}"

    async def _dns_enum(self, domain: str) -> str:
        if not self.kali or not self.kali.is_running:
            return "KaliVM unavailable"
        lines = []
        for record in ["A", "MX", "NS", "TXT"]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "wsl",
                    "--",
                    "dig",
                    "+short",
                    domain,
                    record,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
                out = stdout.decode("utf-8", errors="replace").strip()
                if out:
                    lines.append(f"{record}: {out[:200]}")
            except Exception:
                pass
        return "\n".join(lines) if lines else "No DNS records found"

    async def _analyze_findings(self, domain: str, whois: str, dns: str) -> str:
        if not self.llm:
            return "LLM unavailable for analysis"
        prompt = (
            f"Analyze these OSINT findings for domain '{domain}' and summarize "
            f"security-relevant information:\n\nWHOIS:\n{whois[:1500]}\n\nDNS:\n{dns[:1000]}"
        )
        return await self.llm.complete_async(prompt, max_tokens=300, temperature=0.3)

    async def on_tick(self, cycle: int) -> str | None:
        if cycle % 8 == 0 and self._targets:
            domain = self._targets[cycle // 8 % len(self._targets)]
            self.logger.info(f"Recon on {domain} (cycle {cycle})")
            whois, dns = await asyncio.gather(
                self._whois(domain), self._dns_enum(domain)
            )
            analysis = await self._analyze_findings(domain, whois, dns)
            self._findings.append(
                {"domain": domain, "cycle": cycle, "summary": analysis}
            )
            return f"[{self.name}] Recon complete for {domain}: {analysis[:200]}"
        return None

    async def add_target(self, domain: str):
        self._targets.append(domain)
        self.logger.info(f"Added OSINT target: {domain}")

    def get_findings(self) -> list:
        return self._findings[-20:]
