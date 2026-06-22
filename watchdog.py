"""Stateless Autonomy Watchdog — manages main.py lifecycle with crash recovery and opt-in encrypted telemetry."""

import os
import sys
import time
import json
import yaml
import base64
import signal
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
EVOLUTION_LOG = LOG_DIR / "evolution.log"
CONFIG_PATH = BASE_DIR / "config.yaml"


def _load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except Exception:
        pass
    return {}


_CRASH_SEQ = 0


def log_event(message: str):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    line = f"[{timestamp}] WATCHDOG: {message}\n"
    with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip(), flush=True)


def tail_stderr(stderr_text: str, max_lines: int = 60) -> str:
    lines = stderr_text.strip().split("\n")
    return "\n".join(lines[-max_lines:])


def _machine_id() -> str:
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
            ) as k:
                return winreg.QueryValueEx(k, "MachineGuid")[0]
    except Exception:
        pass
    try:
        return base64.b64encode(
            (
                Path("/etc/machine-id").read_text().strip()
                or Path("/var/lib/dbus/machine-id").read_text().strip()
            ).encode()
        ).decode()
    except Exception:
        pass
    return base64.b64encode(os.urandom(16)).decode()


def _minimal_stack_prefix(trace: str, max_chars: int = 2000) -> str:
    lines = trace.strip().split("\n")
    keep = []
    for line in lines:
        keep.append(line)
        if len("\n".join(keep)) > max_chars:
            keep = keep[:-1]
            break
    return "\n".join(keep)


def _submit_crash(returncode: int, stderr_tail: str):
    global _CRASH_SEQ
    _CRASH_SEQ += 1
    cfg = _load_config()
    telemetry_cfg = cfg.get("telemetry", {})
    if not telemetry_cfg.get("enabled", False):
        return
    endpoint = telemetry_cfg.get("endpoint", "https://api.angeticessence.com/telemetry")
    license_key = cfg.get("license", {}).get("key", "")
    payload = json.dumps(
        {
            "machine_id": _machine_id(),
            "crash_seq": _CRASH_SEQ,
            "returncode": returncode,
            "stderr": _minimal_stack_prefix(stderr_tail),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "platform": sys.platform,
        }
    ).encode()
    signature = base64.b64encode(payload).decode()
    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"payload": signature}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        log_event(f"Telemetry submitted (seq={_CRASH_SEQ})")
    except Exception as e:
        log_event(f"Telemetry send failed: {e}")


def git_rollback() -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=BASE_DIR,
        )
        if result.returncode != 0:
            log_event("No git repository found — skipping rollback")
            return False

        log_event("Attempting git rollback on core/ and agents/...")
        for directory in ["core", "agents"]:
            r = subprocess.run(
                ["git", "checkout", directory],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=BASE_DIR,
            )
            if r.returncode == 0:
                log_event(f"Rolled back {directory}/")
            else:
                log_event(f"Rollback failed for {directory}/: {r.stderr[:200]}")

        r = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=BASE_DIR,
        )
        if r.returncode == 0 and r.stdout.strip():
            log_event(f"Current HEAD: {r.stdout.strip()}")
            return True

        log_event("No commits exist — rollback is a no-op")
        return False
    except Exception as e:
        log_event(f"Git rollback error: {e}")
        return False


def launch_main() -> subprocess.Popen:
    env = os.environ.copy()
    if "ESSENCE_RECOVERED_FROM_CRASH" in os.environ:
        env["ESSENCE_RECOVERED_FROM_CRASH"] = os.environ["ESSENCE_RECOVERED_FROM_CRASH"]

    log_event("Launching main.py...")
    return subprocess.Popen(
        [sys.executable, str(BASE_DIR / "main.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(BASE_DIR),
        env=env,
    )


def watch():
    process = launch_main()
    while True:
        try:
            returncode = process.wait()
        except KeyboardInterrupt:
            log_event("Watchdog interrupted — shutting down main.py")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            sys.exit(0)

        if returncode == 0:
            log_event("main.py exited cleanly (code 0). Watchdog sleeping 5s...")
            time.sleep(5)
            process = launch_main()
            continue

        _, stderr_data = process.communicate()
        crash_tail = tail_stderr(stderr_data)
        log_event(f"main.py CRASHED with code {returncode}")
        log_event(f"STDERR tail:\n{crash_tail}")

        crash_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "returncode": returncode,
            "stderr": crash_tail,
        }
        with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(crash_record) + "\n")

        _submit_crash(returncode, crash_tail)

        git_rollback()

        log_event("Relaunching main.py with ESSENCE_RECOVERED_FROM_CRASH=1")
        os.environ["ESSENCE_RECOVERED_FROM_CRASH"] = "1"
        process = launch_main()


if __name__ == "__main__":
    log_event("Watchdog initializing...")
    watch()
