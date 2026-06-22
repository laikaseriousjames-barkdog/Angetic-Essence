"""Phase 1: Environment & Guardrail Setup - Docker/container verification."""

import os
import sys
import subprocess
import socket


def check_docker() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_container() -> bool:
    hints = [
        os.path.exists("/.dockerenv"),
        os.path.exists("/run/.containerenv"),
        os.environ.get("CONTAINER") == "docker",
    ]
    try:
        with open("/proc/1/cgroup") as f:
            hints.extend(["docker" in line or "kubepods" in line for line in f])
    except FileNotFoundError:
        pass
    return any(hints)


def check_isolated_environment() -> dict:
    checks = {
        "docker_installed": check_docker(),
        "in_container": check_container(),
        "hostname": socket.gethostname(),
        "platform": sys.platform,
    }
    return checks


def assert_safe_environment():
    checks = check_isolated_environment()
    if not checks["in_container"] and os.name != "nt":
        print("WARNING: Not running inside a container. Isolation not guaranteed.")
        print("Proceeding anyway. Set CONTAINER=1 env var to suppress.")
    return checks
