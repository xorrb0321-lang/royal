"""수집 파이프라인 조율."""

from __future__ import annotations

import threading
from typing import Callable

from collector.chat_room import ChatRoomDescriptor
from collector.chat_room_registry import ChatRoomRegistry
from collector.message_reader import MessageReader, RawMessage
from collector.message_watcher import MessageWatcher
from collector.process_monitor import KakaoProcessMonitor
from collector.selector_engine import SelectorEngine
from collector.uia_bridge import UiaEventBridge
from config.selector_config import load_selectors
from config.settings import Settings
from database.repository import InstagramRepository, SaveResult
from parser.instagram import InstagramNormalizer
from parser.url_extractor import UrlExtractor
from utils.hash_cache import HashCache
from utils.logger import get_logger
from utils.retry import RetryPolicy

logger = get_logger(__name__)


class CollectorCoordinator:
    """채팅방 감시 및 Instagram 저장 파이프라인."""

    def __init__(
        self,
        settings: Settings,
        repository: InstagramRepository,
        on_stats_update: Callable[[dict[str, int]], None] | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._on_stats_update = on_stats_update

        retry = RetryPolicy(
            max_attempts=settings.collector.uia_retry_count,
            base_delay_sec=settings.collector.uia_retry_base_delay_sec,
        )
        self._process_monitor = KakaoProcessMonitor(settings.kakao)
        selectors = load_selectors()
        self._selector_engine = SelectorEngine(selectors=selectors, retry=retry)
        self._message_reader = MessageReader(selectors=selectors)
        self._url_extractor = UrlExtractor()
        self._instagram = InstagramNormalizer()
        self._hash_cache = HashCache(settings.collector.message_hash_cache_size)
        self._event_bridge = UiaEventBridge()
        self._watchers: dict[str, MessageWatcher] = {}
        self._registry = ChatRoomRegistry(
            selector_engine=self._selector_engine,
            parser_config=settings.parser,
            on_room_discovered=self._on_room_discovered,
        )
        self._lock = threading.Lock()
        self._messages_processed = 0
        self._accounts_saved = 0

    @property
    def stats(self) -> dict[str, int]:
        return {
            "rooms": len(self._watchers),
            "messages_processed": self._messages_processed,
            "accounts_saved": self._accounts_saved,
            "total_accounts": self._repository.count(),
        }

    def scan_rooms(self) -> None:
        """카카오톡 프로세스에서 채팅방 재스캔."""
        process = self._process_monitor.find_process()
        if process is None:
            return
        self._registry.scan(process.pid)

    def tick_all_watchers(self) -> None:
        """모든 watcher 1회 처리."""
        for watcher in list(self._watchers.values()):
            watcher.tick()

    def stop_all(self) -> None:
        """감시 중지."""
        for watcher in self._watchers.values():
            watcher.stop()
        self._watchers.clear()
        self._registry.clear()
        self._event_bridge.clear()

    def _on_room_discovered(self, room: ChatRoomDescriptor) -> None:
        with self._lock:
            if room.room_id in self._watchers:
                return
            watcher = MessageWatcher(
                room=room,
                selector_engine=self._selector_engine,
                message_reader=self._message_reader,
                config=self._settings.collector,
                hash_cache=self._hash_cache,
                on_message=self._handle_message,
                event_bridge=self._event_bridge,
            )
            watcher.initialize()
            self._watchers[room.room_id] = watcher

    def _handle_message(self, message: RawMessage) -> None:
        self._messages_processed += 1
        urls = self._url_extractor.extract(message.text)
        if not urls:
            return

        profiles = self._instagram.parse_text(message.text, urls)
        for profile in profiles:
            logger.info("instagram 링크 발견: %s", profile.username)
            result = self._repository.save_if_new(profile.username)
            if result == SaveResult.NEW:
                self._accounts_saved += 1

        if self._on_stats_update:
            self._on_stats_update(self.stats)
