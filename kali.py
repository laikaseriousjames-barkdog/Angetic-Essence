"""Kali Linux VM manager — Docker-based, streams console to dashboard."""

import os
import sys
import time
import json
import queue
import signal
import threading
import subprocess
from pathlib import Path
from core.logger import setup_logger


class KaliVM:
    def __init__(self):
        self.logger = setup_logger("kali_vm")
        self.container_name = "agent-zero-kali"
        self.process = None
        self.output_queue: queue.Queue = queue.Queue()
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            try:
                result = subprocess.run(
                    ["docker", "inspect", self.container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    subprocess.run(
                        ["docker", "rm", "-f", self.container_name],
                        capture_output=True,
                        timeout=10,
                    )

                pull = subprocess.run(
                    ["docker", "pull", "kalilinux/kali-rolling"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if pull.returncode != 0:
                    self.logger.error(f"Failed to pull Kali: {pull.stderr[:200]}")
                    return False

                self.process = subprocess.Popen(
                    [
                        "docker",
                        "run",
                        "-i",
                        "--name",
                        self.container_name,
                        "-t",
                        "kalilinux/kali-rolling",
                        "/bin/bash",
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                self._running = True
                threading.Thread(target=self._stream_output, daemon=True).start()
                self.logger.info("Kali VM started")
                self.output_queue.put("[KALI] Container booted. Ready for commands.")
                return True

            except Exception as e:
                self.logger.error(f"Kali start failed: {e}")
                return False

    def _stream_output(self):
        while self._running and self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(line.rstrip())
                else:
                    time.sleep(0.1)
            except Exception:
                break
        self._running = False

    def exec_command(self, command: str) -> bool:
        if not self._running:
            return False
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=300,
            )
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

    def stop(self):
        with self._lock:
            self._running = False
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except Exception:
                    self.process.kill()
                self.process = None
            subprocess.run(
                ["docker", "rm", "-f", self.container_name],
                capture_output=True,
                timeout=10,
            )
            self.logger.info("Kali VM stopped")

    def install_tools(self, packages: list[str]) -> bool:
        if not self._running:
            return False
        pkgs = " ".join(packages)
        self.output_queue.put(f"[KALI] Installing: {pkgs}")
        return self.exec_command(
            f"apt-get update -qq && apt-get install -y -qq {pkgs} 2>&1"
        )
