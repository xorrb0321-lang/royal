"""URL 추출."""

from __future__ import annotations

import re

# 공백·괄호 등으로 끊기는 URL 후보
_URL_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+",
    re.IGNORECASE,
)

# 스킴 없는 instagram.com 도메인
_BARE_INSTAGRAM_PATTERN = re.compile(
    r"(?:^|[\s(])((?:www\.)?instagram\.com/[^\s<>\"']+)",
    re.IGNORECASE,
)


class UrlExtractor:
    """텍스트에서 URL 후보 추출."""

    def extract(self, text: str) -> list[str]:
        """텍스트 내 URL 목록 반환 (중복 제거, 순서 유지)."""
        if not text:
            return []

        found: list[str] = []
        seen: set[str] = set()

        for match in _URL_PATTERN.finditer(text):
            url = self._trim_trailing_punctuation(match.group(0))
            if url not in seen:
                seen.add(url)
                found.append(url)

        for match in _BARE_INSTAGRAM_PATTERN.finditer(text):
            url = self._trim_trailing_punctuation(match.group(1))
            if not url.lower().startswith("http"):
                url = "https://" + url
            if url not in seen:
                seen.add(url)
                found.append(url)

        return found

    @staticmethod
    def _trim_trailing_punctuation(url: str) -> str:
        return url.rstrip(".,);!?]\"'")
