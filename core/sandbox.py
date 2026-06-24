"""Sandbox management and secure validation of agent operations."""

import os
import shlex
import time
from pathlib import Path

from core.logger import setup_logger

logger = setup_logger("sandbox")

# Import docker dynamically to avoid startup crashes if docker is not installed
try:
    import docker
    client = docker.from_env()
except Exception as e:
    logger.debug(f"Docker not available: {e}")
    client = None


def get_or_create_kali_container():
    if client is None:
        return None
    try:
        container = client.containers.get('kali_cyberdeck')
        if container.status != 'running':
            container.start()
        return container
    except Exception as e:
        logger.debug(f"Kali container not found, attempting to create: {e}")
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
        except Exception as run_err:
            logger.error(f"Failed to create Kali container: {run_err}")
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
            
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
            
        forbidden_modules = {"os", "subprocess", "sys", "socket", "pty", "shutil"}
        forbidden_funcs = {"eval", "exec", "open", "compile", "__import__"}
        
        class SecurityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.blocked = []
                
            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name.split('.')[0] in forbidden_modules:
                        self.blocked.append(f"import of forbidden module: {alias.name}")
                self.generic_visit(node)
                
            def visit_ImportFrom(self, node):
                if node.module and node.module.split('.')[0] in forbidden_modules:
                    self.blocked.append(f"import from forbidden module: {node.module}")
                self.generic_visit(node)
                
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_funcs:
                    self.blocked.append(f"call to forbidden function: {node.func.id}")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_funcs:
                    self.blocked.append(f"call to forbidden function attribute: {node.func.attr}")
                self.generic_visit(node)
                
        visitor = SecurityVisitor()
        visitor.visit(tree)
        if visitor.blocked:
            logger.warning(f"Python sandbox blocked execution: {visitor.blocked[0]}")
            return False, f"Dangerous Python operation blocked: {visitor.blocked[0]}"
            
        return True, ""