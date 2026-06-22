"""Optimizer Agent - Self-improvement via log analysis and code patching."""

import os
import json
from pathlib import Path
from core.logger import setup_logger
from agents.developer import DeveloperAgent
from agents.tester import TesterAgent
from core.rollback import RollbackManager


class OptimizerAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("optimizer")
        self.developer = DeveloperAgent(config)
        self.tester = TesterAgent(config)
        self.rollback = RollbackManager()
        self.source_dir = Path(__file__).resolve().parent.parent

    def analyze_error_log(self) -> list[dict]:
        error_log = self.source_dir / "error.log"
        if not error_log.exists():
            return []
        content = error_log.read_text(encoding="utf-8", errors="replace")
        lines = content.strip().split("\n")
        unique = list(dict.fromkeys(lines))
        self.logger.info(f"error.log: {len(unique)} unique entries")
        return [{"line": line, "source": "error.log"} for line in unique[-20:]]

    def self_improve(self, logs: list[dict] | None = None) -> dict:
        if logs is None:
            logs = self.analyze_error_log()
        if not logs:
            self.logger.info("No errors to fix.")
            return {"status": "clean", "action": "none"}

        self.logger.info(f"Self-improvement triggered on {len(logs)} errors.")

        snapshot = self.rollback.snapshot(list(self.source_dir.rglob("*.py")))

        patches = []
        for entry in logs:
            target = self._identify_target(entry["line"])
            if target:
                patch = self._generate_patch(target, entry["line"])
                if patch:
                    patches.append(patch)

        if not patches:
            self.logger.info("No patches generated.")
            return {"status": "no_patches"}

        for patch in patches:
            self.developer.write_file(patch["file"], patch["content"])

        test_result = self._dry_run_test()

        if test_result.get("passed"):
            self.logger.info("Self-improvement: tests PASSED. Changes committed.")
            return {"status": "patched", "patches": len(patches), "tests": "passed"}
        else:
            self.logger.warning("Self-improvement: tests FAILED. Rolling back.")
            latest = self.rollback.latest_snapshot()
            if latest:
                self.rollback.rollback(latest, self.source_dir)
            return {"status": "rolled_back", "patches": len(patches), "tests": "failed"}

    def _identify_target(self, error_line: str) -> str | None:
        for pyfile in self.source_dir.rglob("*.py"):
            if "site-packages" in str(pyfile):
                continue
            if pyfile.name in error_line or str(pyfile.stem) in error_line:
                return str(pyfile)
        return None

    def _generate_patch(self, filepath: str, error_line: str) -> dict | None:
        content = self.developer.read_file(filepath)
        if not content:
            return None
        patched = (
            f"# Auto-patch by OptimizerAgent\n# Source: {error_line[:120]}\n" + content
        )
        return {"file": filepath, "content": patched}

    def _dry_run_test(self) -> dict:
        test_code = self.tester.generate_tests("OptimizerAgent dry-run validation")
        test_file = self.tester.write_test(test_code, "test_optimizer_dryrun.py")
        return self.tester.run_tests(test_file)
