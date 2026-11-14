"""Unit tests for FunnelForge standardized logging."""

import logging
from pathlib import Path
from unittest.mock import patch

from funnelforge.logging import get_logger, setup_logging


def test_setup_logging_console_and_file(tmp_path: Path):
    log_file = tmp_path / "test.log"
    setup_logging(log_level="DEBUG", log_file=log_file)

    logger = get_logger("test_module")
    logger.debug("Debug message test")
    logger.info("Info message test")

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "DEBUG" in content
    assert "Debug message test" in content
    assert "INFO" in content
    assert "Info message test" in content


def test_setup_logging_idempotence(tmp_path: Path):
    log_file = tmp_path / "idempotent.log"
    # Call multiple times
    setup_logging(log_level="INFO", log_file=log_file)
    setup_logging(log_level="INFO", log_file=log_file)

    root_logger = logging.getLogger("funnelforge")
    # Check that handlers are not duplicated indefinitely
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1


def test_get_logger_naming():
    logger1 = get_logger()
    assert logger1.name == "funnelforge"

    logger2 = get_logger("reporting")
    assert logger2.name == "funnelforge.reporting"
