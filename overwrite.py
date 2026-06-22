"""Self-overwrite system for recursive code improvement."""

import sys
from pathlib import Path


class SourceOverwriter:
    """Writes new content to agent source files."""

    def overwrite_file(self, filepath: str | Path, content: str):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def overwrite_own_source(self, content: str):
        current_file = Path(__file__)
        backup = current_file.read_text(encoding="utf-8")
        try:
            current_file.write_text(content, encoding="utf-8")
        except Exception:
            current_file.write_text(backup, encoding="utf-8")
            raise
