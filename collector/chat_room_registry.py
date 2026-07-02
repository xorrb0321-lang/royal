"""채팅방 등록 및 재스캔."""

from __future__ import annotations

import sys
import threading
from typing import Callable

from collector.chat_room import ChatRoomDescriptor, WatcherState
from collector.selector_engine import SelectorEngine
from config.settings import ParserConfig
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatRoomRegistry:
    """열린 채팅방 탐색·등록."""

    def __init__(
        self,
        selector_engine: SelectorEngine,
        parser_config: ParserConfig,
        on_room_discovered: Callable[[ChatRoomDescriptor], None] | None = None,
    ) -> None:
        self._selector_engine = selector_engine
        self._parser_config = parser_config
        self._on_room_discovered = on_room_discovered
        self._rooms: dict[str, ChatRoomDescriptor] = {}
        self._lock = threading.Lock()

    @property
    def rooms(self) -> list[ChatRoomDescriptor]:
        with self._lock:
            return list(self._rooms.values())

    def clear(self) -> None:
        with self._lock:
            self._rooms.clear()

    def scan(self, pid: int) -> list[ChatRoomDescriptor]:
        """채팅방 창 스캔."""
        if sys.platform != "win32":
            return []

        windows = self._selector_engine.find_chat_windows(pid)
        discovered: list[ChatRoomDescriptor] = []

        for window in windows:
            try:
                title = (window.Name or "").strip()
                if not title:
                    continue
                if not self._is_allowed_room(title):
                    continue
                handle = int(window.NativeWindowHandle or 0)
                room_id = f"{pid}:{handle}:{title}"
                descriptor = ChatRoomDescriptor(
                    room_id=room_id,
                    title=title,
                    window_handle=handle,
                    element=window,
                    state=WatcherState.INITIALIZING,
                )
                with self._lock:
                    is_new = room_id not in self._rooms
                    self._rooms[room_id] = descriptor
                discovered.append(descriptor)
                if is_new:
                    logger.info("채팅방 감지: %s", title)
                    if self._on_room_discovered:
                        self._on_room_discovered(descriptor)
            except Exception as exc:
                logger.error("채팅방 스캔 실패: %s", exc)

        return discovered

    def _is_allowed_room(self, title: str) -> bool:
        whitelist = self._parser_config.room_title_whitelist
        if not whitelist:
            return True
        return any(token in title for token in whitelist)
