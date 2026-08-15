"""Persist and restore instagrapi session settings."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SessionStore(ABC):
    @abstractmethod
    def load(self) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, settings: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError


class FileSessionStore(SessionStore):
    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, settings: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
        logger.info("Saved session settings to %s", self.path)


class RedisSessionStore(SessionStore):
    def __init__(self, redis_url: str, key: str) -> None:
        try:
            import redis
        except ImportError as exc:
            raise ImportError(
                "redis package is required for Redis session storage."
            ) from exc

        self.key = key
        self.client = redis.from_url(redis_url, decode_responses=True)

    def exists(self) -> bool:
        return bool(self.client.exists(self.key))

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        raw = self.client.get(self.key)
        if not raw:
            return None
        return json.loads(raw)

    def save(self, settings: dict[str, Any]) -> None:
        self.client.set(self.key, json.dumps(settings))
        logger.info("Saved session settings to Redis key %s", self.key)


class SessionManager:
    """Load and dump instagrapi settings through a pluggable backend."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    @classmethod
    def from_config(cls, config) -> SessionManager:
        if config.session_storage == "redis":
            store = RedisSessionStore(config.redis_url, config.redis_session_key)
        else:
            store = FileSessionStore(config.session_file)
        return cls(store)

    def load_into_client(self, client) -> bool:
        settings = self.store.load()
        if not settings:
            return False
        client.set_settings(settings)
        logger.info("Loaded saved session settings")
        return True

    def save_from_client(self, client) -> None:
        self.store.save(client.get_settings())

    def has_saved_session(self) -> bool:
        return self.store.exists()
