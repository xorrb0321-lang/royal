"""애플리케이션 로깅."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import LoggingConfig

_CONFIGURED = False


def setup_logging(config: LoggingConfig, base_dir: Path) -> None:
    """파일 + 콘솔 로깅 초기화."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = base_dir / config.directory
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "collector.log"

    level = getattr(logging, config.level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 반환."""
    return logging.getLogger(name)


class AppLogger:
    """도메인 이벤트용 로깅 래퍼."""

    def __init__(self, name: str) -> None:
        self._logger = get_logger(name)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def debug(self, message: str) -> None:
        self._logger.debug(message)
