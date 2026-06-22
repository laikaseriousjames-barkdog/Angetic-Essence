"""Speaker — text-to-speech and audio playback for agents."""

import os
import time
import winsound
from pathlib import Path
from core.logger import setup_logger


class Speaker:
    def __init__(self):
        self.logger = setup_logger("speaker")
        self._voice = None

    def _ensure_voice(self):
        if self._voice is None:
            try:
                import win32com.client

                self._voice = win32com.client.Dispatch("SAPI.SpVoice")
                self._voice.Rate = 0
                self._voice.Volume = 100
                self.logger.info("SAPI voice initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize SAPI: {e}")
                return False
        return True

    def speak(
        self, text: str, rate: int = 0, volume: int = 100, wait: bool = True
    ) -> str:
        if not text:
            return "[ERROR] No text to speak"
        if not self._ensure_voice():
            return "[ERROR] Speech not available"

        try:
            self._voice.Rate = rate
            self._voice.Volume = volume
            self.logger.info(f"Speaking ({len(text)} chars): {text[:100]}...")
            if wait:
                self._voice.Speak(text, 1)
                while self._voice.WaitUntilDone(1000) == 0:
                    pass
            else:
                self._voice.Speak(text, 0)
            return f"Spoke: {text[:120]}"
        except Exception as e:
            self.logger.error(f"Speak failed: {e}")
            return f"[ERROR] {e}"

    def speak_async(self, text: str, rate: int = 0, volume: int = 100) -> str:
        return self.speak(text, rate, volume, wait=False)

    def beep(self, frequency: int = 440, duration_ms: int = 300) -> str:
        try:
            winsound.Beep(frequency, duration_ms)
            return f"Beeped at {frequency}Hz for {duration_ms}ms"
        except Exception as e:
            return f"[ERROR] {e}"

    def play_wav(self, path: str | Path) -> str:
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.logger.info(f"Playing audio: {path}")
            return f"Playing: {path}"
        except Exception as e:
            return f"[ERROR] {e}"

    def stop(self):
        if self._voice:
            try:
                self._voice.Speak("", 3)
                self.logger.info("Speech stopped")
            except Exception:
                pass

    def list_voices(self) -> list[dict]:
        if not self._ensure_voice():
            return []
        voices = []
        for v in self._voice.GetVoices():
            voices.append({"name": v.GetDescription(), "id": v.Id})
        return voices

    def set_voice(self, name_pattern: str) -> str:
        if not self._ensure_voice():
            return "[ERROR] Speech not available"
        for v in self._voice.GetVoices():
            if name_pattern.lower() in v.GetDescription().lower():
                self._voice.Voice = v
                return f"Voice set to: {v.GetDescription()}"
        return f"[ERROR] No voice matching '{name_pattern}'"
