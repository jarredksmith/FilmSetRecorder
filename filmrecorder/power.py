from __future__ import annotations

import ctypes
import logging
import subprocess
import sys

LOGGER = logging.getLogger("filmsetrecorder.power")


class PowerInhibitor:
    """Prevent normal idle sleep without forcing the display to stay on.

    This cannot override a laptop's hardware lid-close policy on every OS.
    In particular, macOS may still sleep when the lid closes unless the Mac is
    in a supported clamshell configuration.
    """

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def __init__(self):
        self.active = False
        self._process: subprocess.Popen | None = None

    def enable(self) -> bool:
        if self.active:
            return True
        try:
            if sys.platform.startswith("win"):
                result = ctypes.windll.kernel32.SetThreadExecutionState(
                    self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
                )
                self.active = bool(result)
            elif sys.platform == "darwin":
                self._process = subprocess.Popen(
                    ["caffeinate", "-i", "-m"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.active = True
            else:
                self.active = False
        except Exception:
            LOGGER.exception("Could not enable sleep inhibition")
            self.active = False
        return self.active

    def disable(self) -> None:
        if not self.active and self._process is None:
            return
        try:
            if sys.platform.startswith("win"):
                ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            elif self._process is not None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._process.kill()
        except Exception:
            LOGGER.exception("Could not disable sleep inhibition")
        finally:
            self._process = None
            self.active = False
