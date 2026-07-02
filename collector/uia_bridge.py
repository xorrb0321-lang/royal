"""UIA 이벤트 브릿지 (Windows)."""

from __future__ import annotations

import queue
import sys
import threading
from dataclasses import dataclass
from typing import Any, Callable

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class UiaEvent:
    """UI Automation 이벤트."""

    event_type: str
    room_id: str
    source: Any


class UiaEventBridge:
    """COM 이벤트 → thread-safe Queue."""

    def __init__(self) -> None:
        self._queue: queue.Queue[UiaEvent] = queue.Queue()
        self._handlers: list[Any] = []
        self._running = False

    @property
    def available(self) -> bool:
        return sys.platform == "win32"

    def poll(self, timeout: float = 0.5) -> UiaEvent | None:
        """이벤트 1건 수신."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def subscribe_structure_changed(
        self,
        element: Any,
        room_id: str,
        callback: Callable[[UiaEvent], None] | None = None,
    ) -> bool:
        """StructureChanged 이벤트 구독."""
        if not self.available:
            return False

        try:
            import uiautomation as uia

            def handler(sender, changes, cached):
                event = UiaEvent(event_type="structure_changed", room_id=room_id, source=sender)
                self._queue.put(event)
                if callback:
                    callback(event)

            element.AddStructureChangedEventHandler(uia.StructureChangeType.ChildAdded, handler)
            self._handlers.append((element, handler))
            return True
        except Exception as exc:
            logger.warning("UI 이벤트 구독 실패, 폴링 모드 사용: %s", exc)
            return False

    def clear(self) -> None:
        """구독 해제."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._handlers.clear()
