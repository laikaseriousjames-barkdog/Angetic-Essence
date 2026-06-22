"""Infrastructure Agent - Vagrant/Kali Linux VM provisioning."""

import subprocess
import os
import time
from pathlib import Path
from core.logger import setup_logger


class InfraAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("infra")
        self.work_dir = Path(__file__).resolve().parent.parent

    def provision_kali(self) -> dict:
        self.logger.info("Provisioning Kali Linux VM via Vagrant...")
        vagrantfile = self.work_dir / "Vagrantfile"
        if not vagrantfile.exists():
            self.logger.info("No Vagrantfile found. Initializing Kali Linux box...")
            result = subprocess.run(
                ["vagrant", "init", "kalilinux/kali-linux-2024.1"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.work_dir,
            )
            if result.returncode != 0:
                self.logger.error(f"vagrant init failed: {result.stderr}")
                return {"status": "failed", "detail": result.stderr}
            self.logger.info("Vagrantfile created.")

        self.logger.info("Running vagrant up...")
        result = subprocess.run(
            ["vagrant", "up"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=self.work_dir,
        )
        status = "running" if result.returncode == 0 else "failed"
        self.logger.info(f"VM status: {status}")
        return {"status": status, "detail": result.stdout[-1000:]}

    def ssh_command(self, cmd: str) -> dict:
        self.logger.info(f"SSH command: {cmd[:100]}")
        result = subprocess.run(
            ["vagrant", "ssh", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=self.work_dir,
        )
        return {
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "returncode": result.returncode,
        }

    def halt_vm(self):
        self.logger.info("Halting VM...")
        subprocess.run(
            ["vagrant", "halt"], capture_output=True, cwd=self.work_dir, timeout=60
        )
