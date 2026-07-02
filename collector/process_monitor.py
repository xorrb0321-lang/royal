"""카카오톡 프로세스 감시."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from config.settings import KakaoConfig
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProcessInfo:
    """실행 중인 프로세스 정보."""

    pid: int
    name: str


class KakaoProcessMonitor:
    """KakaoTalk.exe 실행 여부 확인."""

    def __init__(self, config: KakaoConfig) -> None:
        self._config = config
        self._psutil = None
        if sys.platform == "win32":
            import psutil

            self._psutil = psutil

    def is_running(self) -> bool:
        """카카오톡 실행 여부."""
        if sys.platform != "win32":
            logger.warning("Windows가 아닌 환경에서는 프로세스 감지를 지원하지 않습니다.")
            return False
        return self.find_process() is not None

    def find_process(self) -> ProcessInfo | None:
        """실행 중인 카카오톡 프로세스 탐색."""
        if self._psutil is None:
            return None

        target = self._config.process_name.lower()
        for proc in self._psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name == target:
                    return ProcessInfo(pid=int(proc.info["pid"]), name=proc.info["name"])
            except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                continue
        return None

    def wait_until_running(self, stop_event=None) -> ProcessInfo:
        """카카오톡이 실행될 때까지 대기."""
        while True:
            if stop_event is not None and stop_event.is_set():
                raise RuntimeError("중지 요청으로 대기를 종료합니다.")

            info = self.find_process()
            if info:
                logger.info("카카오톡 프로세스 감지 (PID=%s)", info.pid)
                return info

            logger.error(
                "카카오톡 미실행, %.0f초 후 재시도",
                self._config.reconnect_interval_sec,
            )
            time.sleep(self._config.reconnect_interval_sec)
