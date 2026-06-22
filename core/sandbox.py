"""Sandbox management and secure validation of agent operations."""

import os
import shlex
import time
from pathlib import Path

# Import docker dynamically to avoid startup crashes if docker is not installed
try:
    import docker
    client = docker.from_env()
except Exception:
    client = None


def get_or_create_kali_container():
    if client is None:
        return None
    try:
        container = client.containers.get('kali_cyberdeck')
        if container.status != 'running':
            container.start()
        return container
    except Exception:
        try:
            container = client.containers.run(
                'kalilinux/kali-rolling',
                name='kali_cyberdeck',
                detach=True,
                tty=True,
                command='tail -f /dev/null'
            )
            time.sleep(2)
            return container
        except Exception:
            return None


class Sandbox:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.work_dir = Path(__file__).resolve().parent.parent
        self.sandbox_dir = self.work_dir / "sandbox"
        if self.enabled:
            self.sandbox_dir.mkdir(exist_ok=True)

    def resolve_read_path(self, path: str | Path) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.work_dir / p
        p = p.resolve()
        return p

    def resolve_write_path(self, path: str | Path) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.work_dir / p
        p = p.resolve()
        if self.enabled:
            try:
                rel = p.relative_to(self.work_dir)
                return self.sandbox_dir / rel
            except ValueError:
                return self.sandbox_dir / p.name
        return p

    def check_command(self, command: str) -> tuple[bool, str]:
        if not self.enabled:
            return True, ""
        
        WHITELIST = {"ls", "cat", "echo", "pwd", "whoami", "uname", "grep", "find", "head", "tail", "pytest"}
        
        try:
            tokens = shlex.split(command)
        except Exception as e:
            return False, f"Failed to parse command: {e}"
            
        if not tokens:
            return True, ""
            
        dangerous_chars = {"|", ">", ">>", "<", "<<", "&", ";", "`", "$", "(", ")", "{", "}"}
        for token in tokens:
            if any(char in token for char in dangerous_chars):
                return False, f"Dangerous shell character found in token: {token}"
            if token in {"-c", "-i", "-s", "--login", "-l"}:
                return False, f"Dangerous command flag: {token}"
                
        first_cmd = tokens[0].lower()
        if first_cmd not in WHITELIST:
            return False, f"Command '{first_cmd}' is not whitelisted in sandbox mode."
            
        return True, ""

    def check_python_code(self, code: str) -> tuple[bool, str]:
        if not self.enabled:
            return True, ""
            
        dangerous = {"os", "subprocess", "socket", "eval", "exec", "open", "sys"}
        for word in dangerous:
            if word in code:
                if f"import {word}" in code or f"from {word}" in code or f"{word}(" in code:
                    return False, f"Dangerous Python operation blocked: {word}"
        return True, ""