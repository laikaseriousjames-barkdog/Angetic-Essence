"""Screen control — capture, mouse, keyboard for agent screen access."""

import os
import time
from pathlib import Path
from core.logger import setup_logger


class ScreenController:
    def __init__(self):
        self.logger = setup_logger("screen")
        self._pyautogui = None

    def _ensure_pyautogui(self):
        if self._pyautogui is None:
            try:
                import pyautogui

                pyautogui.FAILSAFE = False
                self._pyautogui = pyautogui
            except ImportError:
                self.logger.error("pyautogui not installed")
                return False
        return True

    def screenshot(self, path: str | Path = None) -> str:
        try:
            from PIL import ImageGrab

            img = ImageGrab.grab()
            if path is None:
                path = f"screen_{int(time.time())}.png"
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(p))
            self.logger.info(f"Screenshot saved: {p} ({img.size})")
            return str(p)
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return f"[ERROR] {e}"

    def screenshot_base64(self) -> str:
        try:
            from PIL import ImageGrab
            import base64, io

            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            self.logger.info(f"Screenshot captured ({len(b64) // 1024}KB base64)")
            return b64
        except Exception as e:
            return f"[ERROR] {e}"

    def mouse_position(self) -> dict:
        if not self._ensure_pyautogui():
            return {"error": "pyautogui not installed"}
        x, y = self._pyautogui.position()
        return {"x": x, "y": y}

    def mouse_move(self, x: int, y: int, duration: float = 0.2) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.moveTo(x, y, duration=duration)
        self.logger.info(f"Mouse moved to ({x}, {y})")
        return f"Moved to ({x}, {y})"

    def mouse_click(self, x: int = None, y: int = None, button: str = "left") -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        if x is not None and y is not None:
            self._pyautogui.click(x, y, button=button)
            loc = f"({x}, {y})"
        else:
            self._pyautogui.click(button=button)
            loc = "current position"
        self.logger.info(f"Mouse clicked {button} at {loc}")
        return f"Clicked {button} at {loc}"

    def mouse_drag(self, x: int, y: int, duration: float = 0.3) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.dragTo(x, y, duration=duration)
        return f"Dragged to ({x}, {y})"

    def scroll(self, clicks: int = -3) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.scroll(clicks)
        return f"Scrolled {clicks}"

    def type_text(self, text: str, interval: float = 0.05) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.write(text, interval=interval)
        self.logger.info(f"Typed {len(text)} characters")
        return f"Typed: {text[:80]}"

    def press_key(self, key: str) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.press(key)
        return f"Pressed key: {key}"

    def hotkey(self, *keys: str) -> str:
        if not self._ensure_pyautogui():
            return "[ERROR] pyautogui not installed"
        self._pyautogui.hotkey(*keys)
        return f"Hotkey: {'+'.join(keys)}"

    def screen_size(self) -> dict:
        if not self._ensure_pyautogui():
            return {"error": "pyautogui not installed"}
        w, h = self._pyautogui.size()
        return {"width": w, "height": h}
