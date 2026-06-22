"""Turing — Critic Agent. Deep analysis, code review, web research, decision-making."""

import re
import json
from pathlib import Path
from core.base_agent import BaseAgent


class CriticAgent(BaseAgent):
    def __init__(self, config: dict, llm=None, kali=None):
        super().__init__("critic", config, llm, kali)
        self.iteration = 0

    def analyze_logs(self, log_dir: Path | None = None) -> list[dict]:
        if log_dir is None:
            log_dir = self.work_dir / "logs"
        findings = []
        for log_file in log_dir.glob("*.log"):
            content = log_file.read_text(encoding="utf-8", errors="replace")
            errors = re.findall(r"(ERROR|CRITICAL|FAILED|Traceback).*", content)
            warnings = re.findall(r"(WARNING|TIMEOUT|budget).*", content)
            if errors:
                findings.append(
                    {
                        "file": log_file.name,
                        "severity": "error",
                        "count": len(errors),
                        "samples": errors[:5],
                    }
                )
            if warnings:
                findings.append(
                    {
                        "file": log_file.name,
                        "severity": "warning",
                        "count": len(warnings),
                        "samples": warnings[:5],
                    }
                )
        return findings

    def evaluate_test_results(self, test_output: dict) -> list[str]:
        recommendations = []
        if not test_output.get("passed", True):
            recommendations.append("FIX_FAILING_TESTS")
            stderr = test_output.get("stderr", "")
            if "AssertionError" in stderr:
                recommendations.append("REVIEW_ASSERTIONS")
            if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
                recommendations.append("FIX_IMPORTS")
            if "TIMEOUT" in stderr:
                recommendations.append("OPTIMIZE_PERFORMANCE")
        else:
            recommendations.append("ALL_TESTS_PASS")
            self.iteration += 1
            if self.iteration > 3:
                recommendations.append("ADD_FEATURE")
                self.iteration = 0
        return recommendations

    def dictate_next_action(
        self, findings: list[dict], test_recommendations: list[str]
    ) -> dict:
        action = {"type": "maintain", "target": None, "priority": "low"}
        if any(f["severity"] == "error" for f in findings):
            action["type"] = "fix_bugs"
            action["priority"] = "high"
            action["target"] = [f["file"] for f in findings if f["severity"] == "error"]
        elif "FIX_FAILING_TESTS" in test_recommendations:
            action["type"] = "fix_tests"
            action["priority"] = "high"
        elif "ADD_FEATURE" in test_recommendations:
            if self.iteration % 3 == 0:
                action["type"] = "self_evolve"
                action["priority"] = "high"
                action["suggestion"] = "Improve the Developer agent's capabilities."
            elif self.iteration % 3 == 1:
                action["type"] = "gui_improve"
                action["priority"] = "medium"
                action["suggestion"] = "Add visual polish to the dashboard."
            else:
                action["type"] = "new_feature"
                action["priority"] = "medium"
                action["suggestion"] = (
                    "Add a performance optimization or new utility function."
                )
        elif "OPTIMIZE_PERFORMANCE" in test_recommendations:
            action["type"] = "optimize"
            action["priority"] = "medium"
        else:
            action["type"] = "explore_opportunity"
            action["priority"] = "low"
            action["suggestion"] = (
                "Check the Kali VM for penetration testing opportunities."
            )
        self.logger.info(f"Dictated action: {action}")
        return action

    def speak(self, text: str, wait: bool = True) -> str:
        return self.toolkit.speak(text) if wait else self.toolkit.speak_async(text)

    def code_review(self, filepath: str | Path) -> str:
        content = self.read_file(filepath)
        prompt = f"""Review this code for bugs, vulnerabilities, and improvements:

```python
{content[:4000]}
```

Provide: 1) Critical issues 2) Suggestions 3) Overall assessment."""
        return self.llm.complete(prompt, max_tokens=1024, temperature=0.3)

    def analyze_vm_health(self, healing_log: list) -> dict:
        if not healing_log:
            return {
                "action": "none",
                "reason": "No VM healing history found. VM appears stable.",
            }
        recent = healing_log[-10:]
        log_text = "\n".join(
            f"[{e.get('event', '?')}] {e.get('detail', '')}" for e in recent
        )
        prompt = f"""You are Turing, analyzing the Kali VM healing log. Recent events:

{log_text}

Determine: 1) What went wrong  2) What recovery step to attempt next
Possible actions: restart_wsl, install_distro, retry_boot, escalate
Output valid JSON with keys "action" (the action to take) and "reason" (one sentence explanation)."""
        raw = self.llm.complete(prompt, max_tokens=200, temperature=0.3)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "action": "restart_wsl",
                "reason": "Failed to parse LLM output, defaulting to restart_wsl",
            }

    def deep_research(self, topic: str) -> str:
        self.logger.info(f"Turing researching: {topic[:80]}")
        web_results = self.web_search(topic)
        prompt = f"""Research topic: {topic}

Web results:
{web_results[:3000]}

Synthesize findings and provide actionable recommendations."""
        return self.llm.complete(prompt, max_tokens=1024, temperature=0.5)
