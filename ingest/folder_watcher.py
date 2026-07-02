"""exports 폴더 감시."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

from config.settings import IngestConfig
from ingest.file_loader import ExportFileLoader
from utils.logger import get_logger

logger = get_logger(__name__)


class FolderWatcher:
    """주기적으로 exports 폴더 스캔 (watchdog 없이 단순 폴링)."""

    def __init__(
        self,
        watch_dir: Path,
        config: IngestConfig,
        on_files: Callable[[list[Path]], None],
        interval_sec: float = 5.0,
    ) -> None:
        self._watch_dir = watch_dir
        self._config = config
        self._on_files = on_files
        self._interval_sec = interval_sec
        self._loader = ExportFileLoader(config)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._known: set[str] = set()

    @property
    def watch_dir(self) -> Path:
        return self._watch_dir

    def ensure_watch_dir(self) -> None:
        self._watch_dir.mkdir(parents=True, exist_ok=True)

    def scan_once(self) -> list[Path]:
        """신규 txt 파일 반환."""
        self.ensure_watch_dir()
        all_files = self._loader.list_txt_files(self._watch_dir)
        new_files: list[Path] = []
        for path in all_files:
            key = f"{path.resolve()}:{path.stat().st_mtime_ns}"
            if key not in self._known:
                self._known.add(key)
                new_files.append(path)
        return new_files

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="folder-watcher", daemon=True)
        self._thread.start()
        logger.info("폴더 감시 시작: %s", self._watch_dir)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("폴더 감시 중지")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                new_files = self.scan_once()
                if new_files:
                    self._on_files(new_files)
            except Exception as exc:
                logger.error("폴더 감시 오류: %s", exc)
            time.sleep(self._interval_sec)
