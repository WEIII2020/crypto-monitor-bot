import pytest
from pathlib import Path
from src.utils.logger import setup_logger


def test_logger_creates_log_directory(tmp_path, monkeypatch):
    """Test that logger creates logs directory if it doesn't exist"""
    log_dir = tmp_path / "logs"
    monkeypatch.setattr('src.utils.logger.LOGS_DIR', log_dir)

    logger = setup_logger()

    assert log_dir.exists()


def test_logger_writes_to_file(tmp_path, monkeypatch, caplog):
    """Test that logger writes messages to file"""
    log_dir = tmp_path / "logs"
    monkeypatch.setattr('src.utils.logger.LOGS_DIR', log_dir)

    logger = setup_logger()
    logger.info("Test log message")

    log_files = list(log_dir.glob("crypto_monitor_*.log"))
    assert len(log_files) > 0
