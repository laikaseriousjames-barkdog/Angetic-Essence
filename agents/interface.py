"""Interface Agent - pyautogui screen capture and automated input."""

from core.logger import setup_logger

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class InterfaceAgent:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logger("interface")

    def screenshot(self, path: str = "user_screen.png") -> str | None:
        if not PYAUTOGUI_AVAILABLE:
            self.logger.warning("pyautogui not installed. pip install pyautogui")
            return None
        try:
            img = pyautogui.screenshot(path)
            self.logger.info(f"Screenshot saved: {path} ({img.size})")
            return path
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def click(self, x: int, y: int) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            self.logger.warning("pyautogui not installed.")
            return False
        try:
            pyautogui.click(x, y)
            self.logger.info(f"Clicked at ({x}, {y})")
            return True
        except Exception as e:
            self.logger.error(f"Click failed: {e}")
            return False

    def type_text(self, text: str, interval: float = 0.05) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.write(text, interval=interval)
            self.logger.info(f"Typed {len(text)} characters")
            return True
        except Exception as e:
            self.logger.error(f"Type failed: {e}")
            return False

    def press_key(self, key: str) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pyautogui.press(key)
            self.logger.info(f"Pressed key: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Key press failed: {e}")
            return False

    def locate_and_click(self, image_path: str, confidence: float = 0.9) -> bool:
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            pos = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if pos:
                pyautogui.click(pos)
                self.logger.info(f"Clicked image: {image_path}")
                return True
            self.logger.warning(f"Image not found on screen: {image_path}")
            return False
        except Exception as e:
            self.logger.error(f"Image locate failed: {e}")
            return False
