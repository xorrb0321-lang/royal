"""카카오톡 UI 수집 모듈 (Windows UI Automation)."""

from collector.chat_room import ChatRoomDescriptor, WatcherState
from collector.chat_room_registry import ChatRoomRegistry
from collector.message_reader import MessageReader, RawMessage
from collector.message_watcher import MessageWatcher
from collector.process_monitor import KakaoProcessMonitor

__all__ = [
    "ChatRoomDescriptor",
    "ChatRoomRegistry",
    "KakaoProcessMonitor",
    "MessageReader",
    "MessageWatcher",
    "RawMessage",
    "WatcherState",
]
