"""채팅방별 메시지 감시."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from collector.chat_room import ChatRoomDescriptor, WatcherState
from collector.message_reader import MessageReader, RawMessage
from collector.selector_engine import SelectorEngine
from collector.uia_bridge import UiaEventBridge
from config.settings import CollectorConfig
from utils.hash_cache import HashCache
from utils.logger import get_logger

logger = get_logger(__name__)


class MessageWatcher:
    """단일 채팅방 메시지 감시."""

    def __init__(
        self,
        room: ChatRoomDescriptor,
        selector_engine: SelectorEngine,
        message_reader: MessageReader,
        config: CollectorConfig,
        hash_cache: HashCache,
        on_message: Callable[[RawMessage], None],
        event_bridge: UiaEventBridge | None = None,
    ) -> None:
        self._room = room
        self._selector_engine = selector_engine
        self._message_reader = message_reader
        self._config = config
        self._hash_cache = hash_cache
        self._on_message = on_message
        self._event_bridge = event_bridge
        self._container: Any = None
        self._baseline_initialized = False
        self._last_snapshot: list[str] = []
        self._use_polling = True
        self._stop_event = threading.Event()

    @property
    def room(self) -> ChatRoomDescriptor:
        return self._room

    def stop(self) -> None:
        self._stop_event.set()
        self._room.state = WatcherState.PAUSED

    def initialize(self) -> bool:
        """메시지 컨테이너 탐색 및 베이스라인 설정."""
        self._room.state = WatcherState.INITIALIZING
        window = self._room.element
        if window is None:
            self._room.state = WatcherState.DISCONNECTED
            return False

        self._container = self._selector_engine.find_message_container(window)
        if self._container is None:
            logger.error("메시지 영역을 찾지 못함: room=%s", self._room.title)
            self._room.state = WatcherState.DISCONNECTED
            return False

        self._seed_baseline()
        if self._event_bridge and self._event_bridge.available:
            subscribed = self._event_bridge.subscribe_structure_changed(
                self._container,
                self._room.room_id,
            )
            self._use_polling = not subscribed
            if subscribed:
                logger.info("이벤트 감시 시작: room=%s", self._room.title)
            else:
                logger.warning("UI 이벤트 미지원, 폴링 모드 전환: room=%s", self._room.title)

        self._room.state = WatcherState.DEGRADED if self._use_polling else WatcherState.WATCHING
        return True

    def _seed_baseline(self) -> None:
        """시작 시점 이후 메시지만 수집하도록 기존 메시지 등록."""
        items = self._selector_engine.iter_message_items(self._container)
        messages = self._message_reader.read_latest_messages(
            self._room.room_id,
            self._room.title,
            items,
            limit=50,
        )
        for message in messages:
            self._hash_cache.add(message.fingerprint)
            self._last_snapshot.append(message.fingerprint)
        self._last_snapshot = self._last_snapshot[-50:]
        self._baseline_initialized = True
        logger.info("베이스라인 초기화 완료: room=%s, count=%d", self._room.title, len(messages))

    def tick(self) -> None:
        """폴링 또는 이벤트 큐 처리 1회."""
        if self._stop_event.is_set():
            return

        if not self._baseline_initialized:
            if not self.initialize():
                return

        if self._event_bridge and not self._use_polling:
            event = self._event_bridge.poll(timeout=0.01)
            if event and event.room_id == self._room.room_id:
                self._scan_new_messages()
            return

        self._scan_new_messages()

    def run_loop(self) -> None:
        """폴링 루프 (스레드용)."""
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                logger.error("MessageWatcher 오류: room=%s, error=%s", self._room.title, exc)
            time.sleep(self._config.polling_interval_sec)

    def _scan_new_messages(self) -> None:
        if self._container is None:
            return

        items = self._selector_engine.iter_message_items(self._container)
        messages = self._message_reader.read_latest_messages(
            self._room.room_id,
            self._room.title,
            items,
            limit=30,
        )

        for message in messages:
            if message.fingerprint in self._last_snapshot:
                continue
            if not self._hash_cache.add(message.fingerprint):
                continue
            self._last_snapshot.append(message.fingerprint)
            self._last_snapshot = self._last_snapshot[-50:]
            logger.info("새 메시지 발견: room=%s", self._room.title)
            self._on_message(message)
