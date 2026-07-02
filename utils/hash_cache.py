"""LRU 기반 메시지 fingerprint 캐시."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock


class HashCache:
    """중복 이벤트 억제용 LRU 캐시."""

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max(1, max_size)
        self._cache: OrderedDict[str, None] = OrderedDict()
        self._lock = Lock()

    def contains(self, fingerprint: str) -> bool:
        """fingerprint 존재 여부."""
        with self._lock:
            return fingerprint in self._cache

    def add(self, fingerprint: str) -> bool:
        """
        fingerprint 추가.

        Returns:
            True면 신규, False면 이미 존재.
        """
        with self._lock:
            if fingerprint in self._cache:
                self._cache.move_to_end(fingerprint)
                return False
            self._cache[fingerprint] = None
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            return True

    def clear(self) -> None:
        """캐시 비우기."""
        with self._lock:
            self._cache.clear()
