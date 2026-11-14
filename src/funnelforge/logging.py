"""Centralized logging configuration for FunnelForge."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from funnelforge.config import PROJECT_ROOT

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console: bool = True,
) -> logging.Logger:
    """Configure root logger with console and optional file handlers.

    Idempotently sets up handlers without duplicating them across multiple invocations.
    """
    level_name = (log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger("funnelforge")
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DATE_FORMAT)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    target_log_file = log_file or (PROJECT_ROOT / "logs" / "funnelforge.log")
    try:
        target_log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(target_log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as err:
        sys.stderr.write(f"Warning: Could not configure file logger at {target_log_file}: {err}\n")

    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger child of the funnelforge root logger."""
    if not name or name == "funnelforge":
        return logging.getLogger("funnelforge")
    if name.startswith("funnelforge."):
        return logging.getLogger(name)
    return logging.getLogger(f"funnelforge.{name}")
