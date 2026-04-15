from __future__ import annotations

import string
import threading
import time
from collections.abc import Callable
from typing import Optional
import re

from pynput import keyboard


class BarcodeListener:
    def __init__(
        self,
        on_barcode: Callable[[str], None],
        timeout_seconds: float = 0.08,
        min_length: int = 6,
        max_length: int = 32,
    ) -> None:
        self.on_barcode = on_barcode
        self.timeout_seconds = timeout_seconds
        self.min_length = min_length
        self.max_length = max_length

        self._buffer: list[str] = []
        self._last_key_time: float = 0.0
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        now = time.time()

        with self._lock:
            if self._last_key_time and (now - self._last_key_time) > self.timeout_seconds:
                self._buffer.clear()

            self._last_key_time = now

            if key == keyboard.Key.enter:
                barcode = "".join(self._buffer).strip()
                self._buffer.clear()

                print(f"ENTER received, buffer={self._buffer}")
                if self._is_valid_barcode(barcode):
                    self.on_barcode(barcode)
                return

            char = getattr(key, "char", None)
            if char and char in string.printable and char not in {"\r", "\n", "\t"}:
                self._buffer.append(char)

    # def _is_valid_barcode(self, barcode: str) -> bool:
    #     if not barcode:
    #         return False
    #     if not (self.min_length <= len(barcode) <= self.max_length):
    #         return False
    #     return bool(re.match(r"^[A-Za-z0-9_-]+$", barcode))
    
    def _is_valid_barcode(self, barcode: str) -> bool:
        return self.min_length <= len(barcode) <= self.max_length