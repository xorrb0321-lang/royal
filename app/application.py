"""애플리케이션 서비스."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.coordinator import CollectorCoordinator
from app.lifecycle import LifecycleManager
from collector.process_monitor import KakaoProcessMonitor
from config.settings import Settings, load_settings
from database.connection import DatabaseConnection
from database.repository import InstagramRepository
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


@dataclass
class ApplicationState:
    """UI/상태 표시용."""

    running: bool = False
    rooms: int = 0
    messages_processed: int = 0
    accounts_saved: int = 0
    total_accounts: int = 0


class ApplicationService:
    """전체 애플리케이션 조립 및 실행."""

    def __init__(self, settings: Settings | None = None, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._settings = settings or load_settings(base_dir=self._base_dir)
        setup_logging(self._settings.logging, self._base_dir)

        db_path = self._settings.resolve_path(self._settings.database.path)
        self._repository = InstagramRepository(DatabaseConnection(db_path))
        self._state = ApplicationState(total_accounts=self._repository.count())
        self._state_callbacks: list[Callable[[ApplicationState], None]] = []

        self._coordinator = CollectorCoordinator(
            settings=self._settings,
            repository=self._repository,
            on_stats_update=self._on_stats_update,
        )
        self._lifecycle = LifecycleManager(
            settings=self._settings,
            process_monitor=KakaoProcessMonitor(self._settings.kakao),
            coordinator=self._coordinator,
        )
        self._thread: threading.Thread | None = None

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def state(self) -> ApplicationState:
        return self._state

    @property
    def repository(self) -> InstagramRepository:
        return self._repository

    def on_state_change(self, callback: Callable[[ApplicationState], None]) -> None:
        self._state_callbacks.append(callback)

    def start(self) -> None:
        """백그라운드 수집 시작."""
        if self._state.running:
            return
        self._state.running = True
        self._thread = threading.Thread(target=self._run, name="collector-main", daemon=True)
        self._thread.start()
        logger.info("수집기 시작")

    def stop(self) -> None:
        """수집 중지."""
        if not self._state.running:
            return
        self._lifecycle.stop()
        self._coordinator.stop_all()
        self._state.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("수집기 중지")
        self._notify_state()

    def _run(self) -> None:
        try:
            self._lifecycle.run()
        except Exception as exc:
            logger.error("ApplicationService 치명적 오류: %s", exc)
        finally:
            self._state.running = False
            self._notify_state()

    def _on_stats_update(self, stats: dict[str, int]) -> None:
        self._state.rooms = stats.get("rooms", 0)
        self._state.messages_processed = stats.get("messages_processed", 0)
        self._state.accounts_saved = stats.get("accounts_saved", 0)
        self._state.total_accounts = stats.get("total_accounts", 0)
        self._notify_state()

    def _notify_state(self) -> None:
        for callback in self._state_callbacks:
            try:
                callback(self._state)
            except Exception as exc:
                logger.error("상태 콜백 오류: %s", exc)
