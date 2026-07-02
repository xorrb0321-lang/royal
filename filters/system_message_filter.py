"""시스템·입퇴장 메시지 필터 (zeikar 규칙 참고)."""

from __future__ import annotations

import re

from adapters.kakao_preprocessor import ChatMessage

_DATE_LINE = re.compile(r"^-{5,}\s*\d{4}년\s*\d{1,2}월", re.MULTILINE)

_SYSTEM_PATTERNS = (
    re.compile(r"님이 들어왔습니다\.?$"),
    re.compile(r"님이 나갔습니다\.?$"),
    re.compile(r"님을 초대했습니다\.?$"),
    re.compile(r"님이 삭제되었습니다\.?$"),
    re.compile(r"^사진$"),
    re.compile(r"^동영상$"),
    re.compile(r"^이모티콘$"),
    re.compile(r"^삭제된 메시지입니다\.?$"),
    re.compile(r"joined the open chat", re.I),
    re.compile(r"left the open chat", re.I),
)


class SystemMessageFilter:
    """시스템 메시지 제외."""

    def filter(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        result: list[ChatMessage] = []
        for msg in messages:
            if self._is_system(msg):
                continue
            result.append(msg)
        return result

    def _is_system(self, msg: ChatMessage) -> bool:
        text = msg.text.strip()
        if not text:
            return True
        if _DATE_LINE.match(text):
            return True
        if not msg.author:
            return True
        return any(p.search(text) for p in _SYSTEM_PATTERNS)
