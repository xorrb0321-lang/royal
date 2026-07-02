"""재시도 정책."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryPolicy:
    """지수 백오프 재시도."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_sec: float = 0.5,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self._max_attempts = max(1, max_attempts)
        self._base_delay_sec = base_delay_sec
        self._exceptions = exceptions

    def run(self, func: Callable[[], T], on_retry: Callable[[int, BaseException], None] | None = None) -> T:
        """함수 실행, 실패 시 재시도."""
        last_error: BaseException | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return func()
            except self._exceptions as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break
                if on_retry:
                    on_retry(attempt, exc)
                time.sleep(self._base_delay_sec * (2 ** (attempt - 1)))
        assert last_error is not None
        raise last_error
