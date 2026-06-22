"""Rollback & snapshot system for source code recovery."""

import shutil
import hashlib
from pathlib import Path
from datetime import datetime

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "snapshots"


class RollbackManager:
    def __init__(self):
        SNAPSHOT_DIR.mkdir(exist_ok=True)

    def _file_hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""

    def snapshot(self, source_paths: list[Path]):
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        snap_dir = SNAPSHOT_DIR / ts
        snap_dir.mkdir(parents=True)
        for src in source_paths:
            if src.exists():
                dst = snap_dir / src.name
                shutil.copy2(src, dst)
        return snap_dir

    def rollback(self, snapshot_dir: Path, target_dir: Path):
        for src in snapshot_dir.iterdir():
            if src.is_file():
                dst = target_dir / src.name
                shutil.copy2(src, dst)
        return target_dir

    def latest_snapshot(self) -> Path | None:
        snaps = sorted(SNAPSHOT_DIR.iterdir()) if SNAPSHOT_DIR.exists() else []
        return snaps[-1] if snaps else None
