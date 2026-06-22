"""Lovelace — Tester Agent. Generates tests, runs coverage, validates code."""

import subprocess
import sys
from pathlib import Path
from core.base_agent import BaseAgent


class TesterAgent(BaseAgent):
    def __init__(self, config: dict, llm=None):
        super().__init__("tester", config, llm)
        self.test_dir = self.work_dir / "tests" / "generated"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def generate_tests(
        self, source_code: str, module_name: str = "generated_module"
    ) -> str:
        self.logger.info(f"Generating tests for: {module_name}")
        return self.llm.generate_tests(source_code)

    def write_test(self, test_content: str, test_name: str = "test_auto.py") -> Path:
        test_path = self.test_dir / test_name
        test_path.write_text(test_content, encoding="utf-8")
        self.logger.info(f"Wrote: {test_path}")
        return test_path

    def run_tests(self, test_path: Path | None = None, timeout: int = 60) -> dict:
        target = str(test_path) if test_path else str(self.test_dir)
        self.logger.info(f"Running tests in: {target}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", target, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.test_dir.parent,
            )
            output = {
                "stdout": result.stdout[-3000:],
                "stderr": result.stderr[-3000:],
                "returncode": result.returncode,
                "passed": result.returncode == 0,
            }
            self.logger.info(f"Tests {'PASSED' if output['passed'] else 'FAILED'}")
            return output
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "TIMEOUT",
                "returncode": -1,
                "passed": False,
            }
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1, "passed": False}

    def run_coverage(self, target: str = None) -> dict:
        tgt = target or str(self.test_dir)
        self.logger.info(f"Running coverage: {tgt}")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "coverage",
                    "run",
                    "-m",
                    "pytest",
                    tgt,
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.test_dir.parent,
            )
            report = subprocess.run(
                [sys.executable, "-m", "coverage", "report"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.test_dir.parent,
            )
            return {
                "test_output": result.stdout[-2000:],
                "coverage": report.stdout,
                "passed": result.returncode == 0,
            }
        except Exception as e:
            return {"error": str(e)}
