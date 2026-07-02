"""채팅방 메타데이터."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WatcherState(Enum):
    """채팅방 감시 상태."""

    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    WATCHING = "watching"
    DEGRADED = "degraded"
    PAUSED = "paused"


@dataclass
class ChatRoomDescriptor:
    """감시 대상 채팅방."""

    room_id: str
    title: str
    window_handle: int
    element: Any = field(default=None, repr=False)
    state: WatcherState = WatcherState.DISCONNECTED

    def __hash__(self) -> int:
        return hash(self.room_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ChatRoomDescriptor):
            return NotImplemented
        return self.room_id == other.room_id
