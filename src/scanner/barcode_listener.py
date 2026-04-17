from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from typing import Optional

from pynput import keyboard


class BarcodeListener:
    """
    More tolerant keyboard-wedge barcode listener.

    Compared with the original:
    - still supports the current simple pynput approach
    - accepts Enter and Tab as terminators
    - can emit on timeout if scanner sends no suffix
    - does NOT use aggressive timing heuristics that can reject valid scans
    """

    def __init__(
        self,
        on_barcode: Callable[[str], None],
        timeout_seconds: float = 0.20,
        expected_length: int = 8,
        debug: bool = False,
    ) -> None:
        self.on_barcode = on_barcode
        self.timeout_seconds = timeout_seconds
        self.expected_length = expected_length
        self.debug = debug

        self._buffer: list[str] = []
        self._last_key_time: float = 0.0
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.debug:
            print("BarcodeListener.start()")

        self._stop_event.clear()
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._listener is not None:
            self._listener.stop()
            self._listener = None

        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=0.5)
            self._watchdog_thread = None

    def _watchdog_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(0.03)
            self._flush_if_timed_out()

    def _flush_if_timed_out(self) -> None:
        with self._lock:
            if not self._buffer or not self._last_key_time:
                return

            now = time.time()
            if (now - self._last_key_time) <= self.timeout_seconds:
                return

            barcode = "".join(self._buffer).strip()
            if self.debug:
                print(f"TIMEOUT flush, candidate barcode={barcode!r}")

            self._buffer.clear()
            self._last_key_time = 0.0

        if self._is_valid_barcode(barcode):
            if self.debug:
                print(f"VALID BARCODE (timeout): {barcode}")
            self.on_barcode(barcode)
        else:
            if self.debug:
                print(f"INVALID BARCODE (timeout): {barcode!r}")

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        barcode_to_emit: str | None = None
        now = time.time()

        with self._lock:
            if self._last_key_time and (now - self._last_key_time) > self.timeout_seconds:
                if self.debug and self._buffer:
                    print(f"Gap reset, dropping buffer={''.join(self._buffer)!r}")
                self._buffer.clear()

            self._last_key_time = now

            if key in (keyboard.Key.enter, keyboard.Key.tab):
                barcode = "".join(self._buffer).strip()
                if self.debug:
                    print(f"TERMINATOR pressed, candidate barcode={barcode!r}")
                self._buffer.clear()
                self._last_key_time = 0.0

                if self._is_valid_barcode(barcode):
                    barcode_to_emit = barcode
                else:
                    if self.debug:
                        print(f"INVALID BARCODE (terminator): {barcode!r}")
                # important: stop here for terminator
            else:
                char = getattr(key, "char", None)
                if char and char.isdigit():
                    self._buffer.append(char)
                    if self.debug:
                        print(f"KEY: {char!r} buffer={''.join(self._buffer)!r}")
                    # avoid runaway buffers
                    if len(self._buffer) > self.expected_length:
                        if self.debug:
                            print(f"Buffer overflow, clearing buffer={''.join(self._buffer)!r}")
                        self._buffer.clear()

        if barcode_to_emit is not None:
            if self.debug:
                print(f"VALID BARCODE: {barcode_to_emit}")
            self.on_barcode(barcode_to_emit)

    def _is_valid_barcode(self, barcode: str) -> bool:
        return bool(re.fullmatch(rf"\d{{{self.expected_length}}}", barcode))