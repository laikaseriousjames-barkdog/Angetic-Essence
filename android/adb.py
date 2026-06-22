"""Android ADB Bridge — device control, rooting, and management via agents."""

import subprocess
import time
import re
from pathlib import Path
from core.logger import setup_logger


class ADBBridge:
    def __init__(self, adb_path: str = "adb"):
        self.logger = setup_logger("adb")
        self.adb = adb_path
        self._connected_devices = []

    def _run(self, args: list[str], timeout: int = 30) -> dict:
        try:
            result = subprocess.run(
                [self.adb] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": "ADB not found. Install Android SDK platform-tools.",
                "returncode": -1,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def devices(self) -> list[dict]:
        r = self._run(["devices"])
        devices = []
        for line in r["stdout"].split("\n"):
            if "\tdevice" in line:
                parts = line.split("\t")
                devices.append({"id": parts[0], "status": parts[1]})
        self._connected_devices = devices
        return devices

    def shell(self, command: str, device: str = "", timeout: int = 30) -> dict:
        args = ["-s", device, "shell", command] if device else ["shell", command]
        return self._run(args, timeout)

    def install(self, apk_path: str, device: str = "") -> dict:
        args = (
            ["-s", device, "install", "-r", apk_path]
            if device
            else ["install", "-r", apk_path]
        )
        return self._run(args, 120)

    def uninstall(self, package: str, device: str = "") -> dict:
        args = (
            ["-s", device, "uninstall", package] if device else ["uninstall", package]
        )
        return self._run(args, 60)

    def push(self, local: str, remote: str, device: str = "") -> dict:
        args = (
            ["-s", device, "push", local, remote] if device else ["push", local, remote]
        )
        return self._run(args, 60)

    def pull(self, remote: str, local: str, device: str = "") -> dict:
        args = (
            ["-s", device, "pull", remote, local] if device else ["pull", remote, local]
        )
        return self._run(args, 60)

    def screenshot(self, device: str = "") -> dict:
        remote = "/sdcard/screen.png"
        local = f"android_screen_{int(time.time())}.png"
        self.shell(f"screencap -p {remote}", device)
        return self.pull(remote, local, device)

    def is_rooted(self, device: str = "") -> bool:
        r = self.shell("su -c 'id'", device)
        return "uid=0(root)" in r.get("stdout", "")

    def attempt_root(self, device: str = "") -> dict:
        steps = []
        steps.append(self.shell("su -c 'echo root_ok'", device))
        if "root_ok" in steps[-1].get("stdout", ""):
            return {"status": "already_rooted", "steps": steps}
        steps.append(self.shell("which magisk", device))
        if magisk := steps[-1].get("stdout", ""):
            steps.append(self.shell(f"{magisk} --install", device))
            return {"status": "magisk_attempted", "steps": steps}
        steps.append(self.shell("which supolicy", device))
        if steps[-1].get("stdout"):
            return {"status": "superSU_found", "steps": steps}
        return {"status": "no_root_method_found", "steps": steps}

    def get_prop(self, key: str, device: str = "") -> str:
        r = self.shell(f"getprop {key}", device)
        return r.get("stdout", "")

    def device_info(self, device: str = "") -> dict:
        return {
            "model": self.get_prop("ro.product.model", device),
            "manufacturer": self.get_prop("ro.product.manufacturer", device),
            "android": self.get_prop("ro.build.version.release", device),
            "sdk": self.get_prop("ro.build.version.sdk", device),
            "rooted": self.is_rooted(device),
        }

    def install_apk_from_url(self, url: str, device: str = "") -> dict:
        try:
            import urllib.request
            temp_dir = Path(__file__).resolve().parent.parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            temp_apk = temp_dir / f"downloaded_{int(time.time())}.apk"
            
            self.logger.info(f"Downloading APK from {url} to {temp_apk}")
            urllib.request.urlretrieve(url, str(temp_apk))
            
            res = self.install(str(temp_apk), device)
            if temp_apk.exists():
                temp_apk.unlink()
            return res
        except Exception as e:
            self.logger.error(f"Failed to install APK from URL: {e}")
            return {"error": str(e), "returncode": -1}
