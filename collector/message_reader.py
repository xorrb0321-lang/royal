"""메시지 텍스트 읽기."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from typing import Any

from config.selector_config import SelectorConfig
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RawMessage:
    """UI에서 읽은 원시 메시지."""

    room_id: str
    room_title: str
    runtime_id: str
    text: str
    fingerprint: str


class MessageReader:
    """ListItem에서 텍스트·URL 추출."""

    def __init__(self, selectors: SelectorConfig) -> None:
        self._selectors = selectors

    def read_latest_messages(self, room_id: str, room_title: str, items: list[Any], limit: int = 20) -> list[RawMessage]:
        """최신 메시지 limit개 읽기."""
        messages: list[RawMessage] = []
        for item in items[-limit:]:
            raw = self._read_item(room_id, room_title, item)
            if raw:
                messages.append(raw)
        return messages

    def _read_item(self, room_id: str, room_title: str, item: Any) -> RawMessage | None:
        try:
            runtime_id = self._get_runtime_id(item)
            text = self._extract_text(item).strip()
            if not text:
                return None
            fingerprint = self._build_fingerprint(room_id, runtime_id, text)
            return RawMessage(
                room_id=room_id,
                room_title=room_title,
                runtime_id=runtime_id,
                text=text,
                fingerprint=fingerprint,
            )
        except Exception as exc:
            logger.error("UI Element 접근 실패 (read item): %s", exc)
            return None

    def _extract_text(self, item: Any) -> str:
        parts: list[str] = []
        allowed = set(self._selectors.message_text.control_types)

        def walk(control: Any, depth: int = 0) -> None:
            if depth > 8:
                return
            try:
                type_name = control.ControlTypeName.replace("Control", "")
                name = (control.Name or "").strip()
                if type_name in allowed and name:
                    parts.append(name)
                for child in control.GetChildren():
                    walk(child, depth + 1)
            except Exception:
                return

        walk(item)
        if not parts:
            try:
                return item.Name or ""
            except Exception:
                return ""
        return "\n".join(parts)

    @staticmethod
    def _get_runtime_id(item: Any) -> str:
        try:
            rid = item.GetRuntimeId()
            if rid:
                return "-".join(str(x) for x in rid)
        except Exception:
            pass
        try:
            return str(item.NativeWindowHandle or id(item))
        except Exception:
            return str(id(item))

    @staticmethod
    def _build_fingerprint(room_id: str, runtime_id: str, text: str) -> str:
        payload = f"{room_id}|{runtime_id}|{text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
