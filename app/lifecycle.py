"""카카오톡 수명주기 관리."""

from __future__ import annotations

import threading
import time

from app.coordinator import CollectorCoordinator
from collector.process_monitor import KakaoProcessMonitor
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


class LifecycleManager:
    """카카오톡 실행/종료에 따른 재연결."""

    def __init__(
        self,
        settings: Settings,
        process_monitor: KakaoProcessMonitor,
        coordinator: CollectorCoordinator,
    ) -> None:
        self._settings = settings
        self._process_monitor = process_monitor
        self._coordinator = coordinator
        self._stop_event = threading.Event()
        self._connected = False

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        """메인 루프."""
        last_rescan = 0.0
        while not self._stop_event.is_set():
            try:
                if not self._process_monitor.is_running():
                    if self._connected:
                        logger.warning("카카오톡 연결 해제, 감시 중지")
                        self._coordinator.stop_all()
                        self._connected = False
                    logger.error(
                        "카카오톡 미실행, %.0f초 후 재시도",
                        self._settings.kakao.reconnect_interval_sec,
                    )
                    time.sleep(self._settings.kakao.reconnect_interval_sec)
                    continue

                if not self._connected:
                    self._process_monitor.wait_until_running(self._stop_event)
                    self._coordinator.scan_rooms()
                    self._connected = True

                now = time.monotonic()
                if now - last_rescan >= self._settings.kakao.room_rescan_interval_sec:
                    self._coordinator.scan_rooms()
                    last_rescan = now

                self._coordinator.tick_all_watchers()
                time.sleep(self._settings.collector.polling_interval_sec)
            except Exception as exc:
                logger.error("LifecycleManager 오류: %s", exc)
                time.sleep(self._settings.kakao.reconnect_interval_sec)
