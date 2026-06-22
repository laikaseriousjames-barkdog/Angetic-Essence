"""Angetic Essence — PyInstaller build script with PyArmor obfuscation.
Produces a hardened standalone AngeticEssence.exe.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
SPEC_PATH = BASE_DIR / "AngeticEssence.spec"

PYINSTALLER_HIDDEN_IMPORTS = [
    "asyncio",
    "sqlite3",
    "yaml",
    "tenacity",
    "bs4",
    "flask",
    "jinja2",
    "werkzeug",
    "cryptography",
    "aiohttp",
    "queue",
    "threading",
    "uuid",
    "json",
    "re",
    "ast",
    "shutil",
    "subprocess",
    "concurrent",
    "concurrent.futures",
    "pkg_resources",
    "pkgutil",
    "importlib",
    "inspect",
    "ctypes",
    "pathlib",
    "http.client",
    "urllib.request",
    "urllib.error",
    "socket",
    "ssl",
    "email",
    "email.mime",
    "email.mime.text",
    "email.mime.multipart",
    "xml",
    "xml.etree",
    "xml.etree.ElementTree",
    "html.parser",
    "winsound",
    "win32com",
    "win32com.client",
    "pythoncom",
    "PIL",
    "PIL.ImageGrab",
    "pyautogui",
    "requests",
    "stripe",
    "docker",
    "flask_socketio",
    "eventlet",
    "engineio",
    "werkzeug.security",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat.primitives.serialization",
    "dashboard",
    "dashboard.app",
]


def ensure_pyinstaller():
    try:
        import PyInstaller

        return True
    except ImportError:
        print("[BUILD] PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True


def ensure_pyarmor():
    try:
        import pyarmor

        ver = getattr(pyarmor, "__version__", "")
        if not ver:
            try:
                r = subprocess.run(
                    ["pyarmor", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                ver = r.stdout.strip()[:20]
            except Exception:
                ver = "9.x"
        print(f"[BUILD] PyArmor {ver} found")
        return True
    except ImportError:
        print("[BUILD] PyArmor not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyarmor"])
            return True
        except Exception as e:
            print(f"[WARN] PyArmor install failed: {e}")
            print("[WARN] Falling back to unprotected PyInstaller build")
            return False


def clean_build():
    for d in [DIST_DIR, BUILD_DIR, OBF_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"[BUILD] Cleaned {d}")
    if SPEC_PATH.exists():
        SPEC_PATH.unlink()
        print(f"[BUILD] Removed {SPEC_PATH}")


def _find_exe(dist_dir: Path, name: str) -> Path | None:
    candidates = [
        dist_dir / f"{name}.exe",
        dist_dir / name / f"{name}.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


OBF_DIR = BASE_DIR / "obf_build"
PYARMOR_SOURCE = "pyarmor"


def _check_pyarmor_cli() -> bool:
    try:
        subprocess.run(
            [PYARMOR_SOURCE, "gen", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def build_with_pyarmor():
    ensure_pyinstaller()
    if not ensure_pyarmor():
        build_with_pyinstaller()
        return
    if not _check_pyarmor_cli():
        print("[WARN] pyarmor CLI not found on PATH — falling back")
        build_with_pyinstaller()
        return

    clean_build()
    if OBF_DIR.exists():
        shutil.rmtree(OBF_DIR)

    output_name = "AngeticEssence"
    entry_point = BASE_DIR / "main.py"
    if not entry_point.exists():
        print(f"[ERROR] Entry point not found: {entry_point}")
        sys.exit(1)

    print(f"\n[BUILD] PyArmor 9.x pipeline — Stage 1: Obfuscation")
    obf_cmd = [
        PYARMOR_SOURCE,
        "gen",
        "-O",
        str(OBF_DIR),
        "-r",
        str(entry_point),
        str(BASE_DIR / "core"),
        str(BASE_DIR / "agents"),
        str(BASE_DIR / "plugins"),
        str(BASE_DIR / "vm"),
        str(BASE_DIR / "android"),
    ]
    print(f"  {' '.join(obf_cmd)}")
    r1 = subprocess.run(obf_cmd, cwd=str(BASE_DIR))
    if r1.returncode != 0:
        print(
            f"[WARN] PyArmor obfuscation failed (code {r1.returncode}) — falling back"
        )
        if OBF_DIR.exists():
            shutil.rmtree(OBF_DIR)
        build_with_pyinstaller()
        return

    obf_entry = OBF_DIR / "main.py"
    if not obf_entry.exists():
        print("[WARN] obf_build/main.py not generated — falling back")
        build_with_pyinstaller()
        return
    print(f"[BUILD] Stage 1 complete — obfuscated bytecode in {OBF_DIR}")

    print(f"\n[BUILD] Stage 2: PyInstaller packaging (targeting obfuscated entry)")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--log-level=INFO",
        "--onefile",
        "--name",
        output_name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--add-data",
        f"{OBF_DIR / 'core'}{os.pathsep}core",
        "--add-data",
        f"{OBF_DIR / 'agents'}{os.pathsep}agents",
        "--add-data",
        f"{OBF_DIR / 'plugins'}{os.pathsep}plugins",
        "--add-data",
        f"{OBF_DIR / 'vm'}{os.pathsep}vm",
        "--add-data",
        f"{OBF_DIR / 'android'}{os.pathsep}android",
        "--add-data",
        f"{BASE_DIR / 'dashboard' / 'templates'}{os.pathsep}dashboard/templates",
        "--add-data",
        f"{BASE_DIR / 'dashboard' / 'static'}{os.pathsep}dashboard/static",
        "--add-data",
        f"{BASE_DIR / 'config.yaml'}{os.pathsep}.",
    ]
    if (BASE_DIR / "logs").exists():
        cmd.extend(["--add-data", f"{BASE_DIR / 'logs'}{os.pathsep}logs"])

    for mod in PYINSTALLER_HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")

    cmd.append(str(obf_entry))

    print(f"[BUILD] Executing PyInstaller...")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller failed with code {result.returncode}")
        sys.exit(result.returncode)

    if OBF_DIR.exists():
        shutil.rmtree(OBF_DIR)
        print(f"[BUILD] Cleaned up {OBF_DIR}")

    exe_path = _find_exe(DIST_DIR, output_name)
    if exe_path:
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Obfuscated executable: {exe_path} ({size_mb:.1f} MB)")
    print(f"[BUILD] Complete. Output: {DIST_DIR}")


def build_with_pyinstaller():
    ensure_pyinstaller()
    clean_build()

    entry_point = BASE_DIR / "main.py"
    if not entry_point.exists():
        print(f"[ERROR] Entry point not found: {entry_point}")
        sys.exit(1)

    output_name = "AngeticEssence"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--log-level=INFO",
        "--onefile",
        "--name",
        output_name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--add-data",
        f"{BASE_DIR / 'core'}{os.pathsep}core",
        "--add-data",
        f"{BASE_DIR / 'agents'}{os.pathsep}agents",
        "--add-data",
        f"{BASE_DIR / 'vm'}{os.pathsep}vm",
        "--add-data",
        f"{BASE_DIR / 'android'}{os.pathsep}android",
        "--add-data",
        f"{BASE_DIR / 'plugins'}{os.pathsep}plugins",
        "--add-data",
        f"{BASE_DIR / 'dashboard' / 'templates'}{os.pathsep}dashboard/templates",
        "--add-data",
        f"{BASE_DIR / 'dashboard' / 'static'}{os.pathsep}dashboard/static",
        "--add-data",
        f"{BASE_DIR / 'config.yaml'}{os.pathsep}.",
    ]

    if (BASE_DIR / "logs").exists():
        cmd.extend(["--add-data", f"{BASE_DIR / 'logs'}{os.pathsep}logs"])

    for mod in PYINSTALLER_HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")

    cmd.append(str(entry_point))

    print(f"\n[BUILD] Running PyInstaller...")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))

    if result.returncode != 0:
        print(f"\n[ERROR] PyInstaller failed with code {result.returncode}")
        sys.exit(result.returncode)

    exe_path = _find_exe(DIST_DIR, output_name)
    if exe_path:
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n[SUCCESS] Executable built: {exe_path} ({size_mb:.1f} MB)")
    print(f"\n[BUILD] Complete. Output: {DIST_DIR}")


def build():
    print("=" * 60)
    print("  ANGETIC ESSENCE — HARDENED BUILD SYSTEM")
    print("=" * 60)
    build_with_pyarmor()


if __name__ == "__main__":
    build()
