"""Kali Linux VM manager — WSL2 based with Docker fallback and self-repair."""

import os
import sys
import uuid
import time
import json
import queue
import threading
import subprocess
from pathlib import Path
from core.logger import setup_logger


KALI_WSL_NAME = "kali-linux"
UBUNTU_WSL_NAME = "Ubuntu-24.04"
KALI_DOCKER_IMAGE = "kalilinux/kali-rolling"
HEALING_LOG = Path(__file__).resolve().parent.parent / "logs" / "vm_healing.json"


class KaliVM:
    def __init__(self):
        self.logger = setup_logger("kali_vm")
        self.output_queue: queue.Queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()
        self._wsl_name = None
        self._healing_attempts = 0
        self._tools_installed = False

    def _log_healing(self, event: str, detail: str):
        log_path = HEALING_LOG
        log_path.parent.mkdir(exist_ok=True)
        entry = {"time": time.time(), "event": event, "detail": detail}
        try:
            history = json.loads(log_path.read_text()) if log_path.exists() else []
        except Exception as e:
            self.logger.error(f"Failed to load healing log: {e}")
            history = []
        history.append(entry)
        log_path.write_text(json.dumps(history[-50:], indent=2))
        self.logger.info(f"[HEAL] {event}: {detail}")

    def _run_wsl(
        self, cmd: str, timeout: int = 60, shell: bool = False
    ) -> subprocess.CompletedProcess:
        if shell:
            return subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
        if self._wsl_name:
            return subprocess.run(
                ["wsl", "-d", self._wsl_name, "--", "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        return subprocess.run(
            ["wsl", "--", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _detect_wsl(self) -> bool:
        try:
            result = subprocess.run(
                ["wsl", "-l", "-v"], capture_output=True, text=True, timeout=15
            )
            raw = result.stdout
            if "\x00" in raw:
                raw = raw.encode("utf-8").decode("utf-16-le")
            lines = raw.strip().split("\n")
            if len(lines) <= 1:
                return False
            
            distros = []
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.replace("*", "").strip().split()
                if parts:
                    distros.append(parts[0])
            
            if not distros:
                return False
                
            # Find best match (Kali > Ubuntu > Debian > Other)
            for d in distros:
                if "kali" in d.lower():
                    self._wsl_name = d
                    return True
            for d in distros:
                if "ubuntu" in d.lower():
                    self._wsl_name = d
                    return True
            for d in distros:
                if "debian" in d.lower():
                    self._wsl_name = d
                    return True
            
            self._wsl_name = distros[0]
            return True
        except Exception as e:
            self.logger.error(f"WSL detection failed: {e}")
            return False

    def _heal_wsl(self) -> bool:
        self._healing_attempts += 1
        self.logger.info(f"Healing attempt #{self._healing_attempts}...")

        # Attempt 1: Try starting the detected distro
        if self._wsl_name:
            self._log_healing("starting_distro", f"Starting {self._wsl_name}")
            try:
                subprocess.run(
                    ["wsl", "-d", self._wsl_name, "--", "bash", "-c", "echo ready"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self._log_healing("distro_started", f"{self._wsl_name} responded")
                return True
            except Exception as e:
                self._log_healing("distro_start_failed", str(e))

        # Attempt 2: Try without specifying distro name
        self._log_healing("try_default_wsl", "Attempting default WSL")
        try:
            result = subprocess.run(
                ["wsl", "--", "bash", "-c", "echo default_wsl_ok"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if "default_wsl_ok" in result.stdout:
                self._wsl_name = None
                self._log_healing("default_wsl_working", "Default WSL works")
                return True
        except Exception as e:
            self._log_healing("default_wsl_failed", str(e))

        # Attempt 3: Try installing Kali WSL
        self._log_healing("install_kali_wsl", "Attempting to install Kali Linux WSL")
        try:
            subprocess.run(
                ["wsl", "--install", "-d", "kali-linux"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self._wsl_name = KALI_WSL_NAME
            self._log_healing("kali_installed", "Kali Linux WSL installed")
            return True
        except Exception as e:
            self._log_healing("kali_install_failed", str(e))

        return False

    def _detect_docker(self) -> bool:
        try:
            r = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                self.logger.info(f"Docker available: {r.stdout.strip()}")
                return True
            self.logger.warning(f"Docker not available: {r.stderr[:100]}")
            return False
        except FileNotFoundError:
            self.logger.warning("Docker not installed")
            return False
        except Exception as e:
            self.logger.warning(f"Docker detection failed: {e}")
            return False

    def _start_docker_kali(self) -> bool:
        self._log_healing("docker_pull", f"Pulling {KALI_DOCKER_IMAGE}")
        try:
            subprocess.run(
                ["docker", "pull", KALI_DOCKER_IMAGE],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except Exception as e:
            self._log_healing("docker_pull_failed", str(e))
            return False
        self._log_healing("docker_run", "Starting Kali Docker container")
        try:
            subprocess.run(
                ["docker", "rm", "-f", "kali-agent"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as e:
            self.logger.debug(f"Docker rm failed (likely didn't exist): {e}")
        self._container_uuid = uuid.uuid4().hex
        container_name = f"kali-agent-{self._container_uuid[:8]}"
        try:
            r = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    container_name,
                    "--network",
                    "host",
                    "-it",
                    KALI_DOCKER_IMAGE,
                    "bash",
                    "-c",
                    "apt-get update -qq && apt-get install -y -qq "
                    "nmap curl wget netcat-openbsd sqlmap hydra dirb "
                    "jq dnsutils whois 2>/dev/null; "
                    "echo KALI_DOCKER_READY; "
                    "while true; do sleep 30; done",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if r.returncode == 0:
                self._wsl_name = None
                self._running = True
                self._tools_installed = True
                self._log_healing("docker_kali_ready", "Kali Docker container running")
                self.output_queue.put("[KALI] Docker Kali container ready.")
                return True
            self._log_healing("docker_run_failed", r.stderr[:200])
            return False
        except Exception as e:
            self._log_healing("docker_run_failed", str(e))
            return False

    def _exec_docker(self, cmd: str, timeout: int = 60) -> subprocess.CompletedProcess:
        container_name = (
            f"kali-agent-{self._container_uuid[:8]}"
            if hasattr(self, "_container_uuid")
            else "kali-agent"
        )
        return subprocess.run(
            ["docker", "exec", container_name, "bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _install_tools(self):
        if self._tools_installed:
            return True
        self._log_healing("installing_tools", "Installing Kali security tools")
        try:
            cmd = (
                "apt-get update -qq 2>/dev/null && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nmap curl wget netcat-openbsd "
                "sqlmap hydra dirb jq dnsutils whois 2>/dev/null | tail -3"
            )
            # Use '-u root' to bypass sudo password prompt
            result = subprocess.run(
                ["wsl", "-d", self._wsl_name, "-u", "root", "--", "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Apt install failed: {result.stderr[:200]}")
            
            self._tools_installed = True
            self._log_healing("tools_installed", "Security tools installed")
            return True
        except Exception as e:
            self._log_healing("tools_install_failed", str(e))
            return False

    @property
    def is_running(self):
        return self._running

    @staticmethod
    def check_wsl_health() -> dict:
        try:
            result = subprocess.run(
                ["wsl", "-l", "-v"], capture_output=True, text=True, timeout=15
            )
            raw = result.stdout
            if "\x00" in raw:
                raw = raw.encode("utf-8").decode("utf-16-le")
            has_distro = KALI_WSL_NAME in raw or UBUNTU_WSL_NAME in raw
            return {"healthy": has_distro, "output": raw.strip()[:500]}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    @staticmethod
    def get_healing_log() -> list:
        try:
            if HEALING_LOG.exists():
                return json.loads(HEALING_LOG.read_text())
            return []
        except Exception as e:
            self.logger.error(f"Failed to read healing log: {e}")
            return []

    @property
    def healing_history(self) -> list:
        return self.get_healing_log()

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True

            # Phase 1: Detect WSL
            if not self._detect_wsl():
                self._log_healing("no_wsl", "No WSL distro detected, attempting heal")
                if not self._heal_wsl():
                    self.output_queue.put(
                        "[KALI] WSL healing failed — trying Docker fallback..."
                    )
                    if self._detect_docker() and self._start_docker_kali():
                        return True
                    self.output_queue.put("[KALI] ERROR: No WSL or Docker available.")
                    return False

            # Phase 2: Start WSL distro
            self._log_healing(
                "booting", f"Starting VM on {self._wsl_name or 'default'}"
            )
            try:
                test_cmd = "echo wsl_boot_ok && cat /etc/os-release 2>/dev/null | head -1 || echo 'no_os_release'"
                result = self._run_wsl(test_cmd, timeout=60)
                if "wsl_boot_ok" not in result.stdout:
                    raise RuntimeError(f"WSL boot test failed: {result.stderr[:200]}")
                self._log_healing("booted", "WSL instance is alive")
            except Exception as e:
                self._log_healing("boot_failed", str(e))
                if not self._heal_wsl():
                    self.output_queue.put(
                        "[KALI] WSL boot failed — trying Docker fallback..."
                    )
                    if self._detect_docker() and self._start_docker_kali():
                        return True
                    self.output_queue.put(
                        "[KALI] ERROR: VM boot failed after all attempts."
                    )
                    return False

            # Phase 3: Install tools
            self._install_tools()

            self._running = True
            self.output_queue.put("[KALI] VM ready — Kali tools loaded.")
            self.logger.info("Kali VM started successfully")
            return True

    def exec_command(self, command: str) -> bool:
        if not self._running:
            return False
        try:
            if self._wsl_name is None:
                result = self._exec_docker(command, timeout=300)
            else:
                result = self._run_wsl(command, timeout=300)
            output = result.stdout + result.stderr
            for line in output.split("\n"):
                if line.strip():
                    self.output_queue.put(line.strip())
            self.output_queue.put(f"[EXIT {result.returncode}]")
            return True
        except subprocess.TimeoutExpired:
            self.output_queue.put("[KALI] Command timed out (300s)")
            return False
        except Exception as e:
            self.output_queue.put(f"[KALI] Error: {e}")
            return False

    def install_tools(self, packages: list[str]) -> bool:
        if not self._running:
            return False
        pkgs = " ".join(packages)
        self.output_queue.put(f"[KALI] Installing: {pkgs}")
        if self._wsl_name is None:
            return self.exec_command(
                f"apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq {pkgs} 2>&1"
            )
        
        try:
            cmd = f"apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq {pkgs} 2>&1"
            result = subprocess.run(
                ["wsl", "-d", self._wsl_name, "-u", "root", "--", "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            for line in output.split("\n"):
                if line.strip():
                    self.output_queue.put(line.strip())
            self.output_queue.put(f"[EXIT {result.returncode}]")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.output_queue.put("[KALI] Command timed out (300s)")
            return False
        except Exception as e:
            self.output_queue.put(f"[KALI] Error: {e}")
            return False

    def stop(self):
        with self._lock:
            self._running = False
            self.logger.info("Kali VM stopped")
            self.output_queue.put("[KALI] VM halted.")
