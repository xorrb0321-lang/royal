"""애플리케이션 서비스."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.pipeline import ExportPipeline, PipelineResult, PipelineStats
from config.settings import Settings, load_settings
from ingest.folder_watcher import FolderWatcher
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


@dataclass
class ApplicationState:
    """UI 표시용 상태."""

    running: bool = False
    files_processed: int = 0
    total_accounts: int = 0
    new_accounts: int = 0
    duplicates_skipped: int = 0
    watch_dir: str = ""
    csv_path: str = ""


class ApplicationService:
    """폴더 감시 + 파이프라인 조율."""

    def __init__(self, settings: Settings | None = None, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._settings = settings or load_settings(base_dir=self._base_dir)
        setup_logging(self._settings.logging, self._base_dir)

        self._pipeline = ExportPipeline(self._settings)
        self._state = ApplicationState(
            watch_dir=str(self._pipeline.watch_dir),
            csv_path=str(self._pipeline.csv_path),
            total_accounts=self._pipeline.store.count_accounts(),
        )
        self._callbacks: list[Callable[[ApplicationState], None]] = []
        self._lock = threading.Lock()
        self._watcher = FolderWatcher(
            watch_dir=self._pipeline.watch_dir,
            config=self._settings.ingest,
            on_files=self._on_new_files,
        )

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def pipeline(self) -> ExportPipeline:
        return self._pipeline

    def on_state_change(self, callback: Callable[[ApplicationState], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        if self._state.running:
            return
        self._state.running = True
        self._watcher.ensure_watch_dir()
        self._watcher.start()
        threading.Thread(target=self._initial_scan, daemon=True).start()
        logger.info("수집기 시작")
        self._notify()

    def stop(self) -> None:
        if not self._state.running:
            return
        self._watcher.stop()
        self._state.running = False
        logger.info("수집기 중지")
        self._notify()

    def process_file(self, path: Path) -> PipelineResult:
        """단일/수동 파일 처리."""
        with self._lock:
            result = self._pipeline.process_paths([path])
            self._apply_result(result)
            return result

    def process_drop_paths(self, paths: list[Path]) -> PipelineResult:
        with self._lock:
            result = self._pipeline.process_paths(paths)
            self._apply_result(result)
            return result

    def reexport_csv(self) -> Path:
        from exporter.csv_exporter import CsvExporter

        exporter = CsvExporter(self._pipeline.csv_path)
        return exporter.export_from_store(self._pipeline.store)

    def _initial_scan(self) -> None:
        try:
            with self._lock:
                result = self._pipeline.process_watch_dir()
                self._apply_result(result)
        except Exception as exc:
            logger.error("초기 스캔 오류: %s", exc)

    def _on_new_files(self, paths: list[Path]) -> None:
        try:
            with self._lock:
                result = self._pipeline.process_paths(paths)
                self._apply_result(result)
        except Exception as exc:
            logger.error("파일 처리 오류: %s", exc)

    def _apply_result(self, result: PipelineResult) -> None:
        self._state.files_processed += result.stats.files_processed
        self._state.new_accounts += result.stats.new_accounts
        self._state.duplicates_skipped += result.stats.duplicates_skipped
        self._state.total_accounts = self._pipeline.store.count_accounts()
        if result.csv_path:
            self._state.csv_path = str(result.csv_path)
        self._notify()

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self._state)
            except Exception as exc:
                logger.error("상태 콜백 오류: %s", exc)
