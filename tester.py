"""Phase 2: The Tester Agent.

Generates and runs unit tests for Developer-written code.
Logs all failures for the Critic to analyze.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from core.logger import setup_logger


class TesterAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("tester")
        self.test_dir = Path(__file__).resolve().parent.parent / "tests" / "generated"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def generate_tests(
        self, source_code: str, module_name: str = "generated_module"
    ) -> str:
        """Auto-generate pytest-compatible tests from source code."""
        self.logger.info(f"Generating tests for module: {module_name}")
        test_content = [
            f"'''Auto-generated tests for {module_name}.'''",
            "import pytest",
            f"import sys, importlib",
            f"# Attempt to import the module being tested",
            f"try:",
            f"    mod = importlib.import_module('{module_name}')",
            f"except ImportError:",
            f"    mod = None",
            "",
            "",
            f"def test_module_importable():",
            f"    assert mod is not None, f'Module {module_name} could not be imported'",
            "",
            f"def test_module_has_attributes():",
            f"    if mod is None:",
            f"        pytest.skip('Module not importable')",
            f"    attrs = [a for a in dir(mod) if not a.startswith('_')]",
            f"    assert len(attrs) > 0, 'Module has no public attributes'",
            "",
        ]
        return "\n".join(test_content)

    def write_test(self, test_content: str, test_name: str = "test_auto.py") -> Path:
        test_path = self.test_dir / test_name
        test_path.write_text(test_content, encoding="utf-8")
        self.logger.info(f"Wrote test file: {test_path}")
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
            self.logger.info(
                f"Tests {'PASSED' if output['passed'] else 'FAILED'} "
                f"(rc={result.returncode})"
            )
            return output
        except subprocess.TimeoutExpired:
            self.logger.error("Tests timed out")
            return {
                "stdout": "",
                "stderr": "TIMEOUT",
                "returncode": -1,
                "passed": False,
            }
        except Exception as e:
            self.logger.error(f"Test run failed: {e}")
            return {"stdout": "", "stderr": str(e), "returncode": -1, "passed": False}
