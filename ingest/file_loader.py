"""export txt 파일 로더."""

from __future__ import annotations

from pathlib import Path

from config.settings import IngestConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class ExportFileLoader:
    """txt 파일 검증 및 목록."""

    def __init__(self, config: IngestConfig) -> None:
        self._config = config

    def is_allowed(self, path: Path) -> bool:
        return path.suffix.lower() in {ext.lower() for ext in self._config.allowed_extensions}

    def list_txt_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return []
        files = [p for p in directory.rglob("*.txt") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        return files

    def read_bytes_hash(self, path: Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()
