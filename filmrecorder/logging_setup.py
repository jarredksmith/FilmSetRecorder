from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .utils import app_data_dir


def configure_logging() -> logging.Logger:
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("filmsetrecorder")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_dir / "filmsetrecorder.log",
            maxBytes=2_000_000,
            backupCount=4,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)
    return logger


def install_exception_hook(logger: logging.Logger) -> None:
    original = sys.excepthook

    def hook(exc_type, exc_value, exc_traceback):
        if exc_type is KeyboardInterrupt:
            return original(exc_type, exc_value, exc_traceback)
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        return original(exc_type, exc_value, exc_traceback)

    sys.excepthook = hook
