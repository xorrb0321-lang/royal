"""카카오 export 오픈소스 어댑터."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import kakaotalk_msg_preprocessor as ktp

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ChatMessage:
    """구조화된 채팅 메시지."""

    datetime: datetime
    author: str
    text: str
    room_name: str


class KakaoExportAdapter:
    """kakaotalk-msg-preprocessor 래퍼."""

    def detect_format(self, file_path: Path) -> str:
        return ktp.check_export_file_type(str(file_path))

    def load_messages(self, file_path: Path, room_name: str | None = None) -> list[ChatMessage]:
        """export txt → ChatMessage 목록."""
        file_type = self.detect_format(file_path)
        raw_messages = ktp.parse(file_type, str(file_path))
        resolved_room = room_name or self._infer_room_name(file_path)
        messages: list[ChatMessage] = []
        for item in raw_messages:
            dt = item.get("datetime")
            author = (item.get("user_name") or "").strip()
            text = (item.get("text") or "").strip()
            if not isinstance(dt, datetime) or not text:
                continue
            messages.append(
                ChatMessage(
                    datetime=dt,
                    author=author,
                    text=text,
                    room_name=resolved_room,
                )
            )
        logger.info("메시지 파싱 완료: file=%s, count=%d", file_path.name, len(messages))
        return messages

    @staticmethod
    def _infer_room_name(file_path: Path) -> str:
        """파일명에서 채팅방 이름 추정."""
        stem = file_path.stem
        if "KakaoTalk" in stem:
            parts = stem.split("_", 2)
            if len(parts) >= 3:
                return parts[2]
        return stem
