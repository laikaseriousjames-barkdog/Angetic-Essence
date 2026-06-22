"""Phase 2: The Critic Agent.

Evaluates execution logs, identifies bugs and bottlenecks,
and dictates what the Developer should build next.
"""

import re
from pathlib import Path
from core.logger import setup_logger


class CriticAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("critic")
        self.iteration = 0

    def analyze_logs(self, log_dir: Path | None = None) -> list[dict]:
        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent / "logs"
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
        action = {
            "type": "maintain",
            "target": None,
            "priority": "low",
        }
        if any(f["severity"] == "error" for f in findings):
            action["type"] = "fix_bugs"
            action["priority"] = "high"
            error_files = [f["file"] for f in findings if f["severity"] == "error"]
            action["target"] = error_files
        elif "FIX_FAILING_TESTS" in test_recommendations:
            action["type"] = "fix_tests"
            action["priority"] = "high"
        elif "ADD_FEATURE" in test_recommendations:
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
            action["suggestion"] = "Scrape marketplaces for monetization opportunities."

        self.logger.info(f"Dictated action: {action}")
        return action
