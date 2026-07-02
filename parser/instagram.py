"""Instagram 프로필 URL 정규화."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

# 프로필: instagram.com/{username} 단일 세그먼트
_PROFILE_PATH_PATTERN = re.compile(
    r"^/([A-Za-z0-9._]+)/?$",
)

# 수집 제외 path prefix
_EXCLUDED_SEGMENTS = frozenset(
    {
        "p",
        "reel",
        "reels",
        "stories",
        "tv",
        "explore",
        "accounts",
        "direct",
        "about",
        "legal",
        "developer",
    }
)

_VALID_USERNAME_PATTERN = re.compile(r"^[a-z0-9._]+$")


@dataclass(frozen=True)
class ParseResult:
    """파싱 결과."""

    username: str
    source_url: str
    is_profile: bool = True


class InstagramNormalizer:
    """Instagram URL → username 변환."""

    def parse_url(self, url: str) -> ParseResult | None:
        """URL이 프로필이면 ParseResult, 아니면 None."""
        if not url:
            return None

        normalized_url = self._normalize_url_string(url)
        if "instagram.com" not in normalized_url.lower():
            return None

        username = self._extract_username(normalized_url)
        if not username:
            return None

        return ParseResult(username=username, source_url=normalized_url, is_profile=True)

    def parse_text(self, text: str, urls: list[str]) -> list[ParseResult]:
        """URL 목록에서 Instagram 프로필만 추출."""
        results: list[ParseResult] = []
        seen: set[str] = set()
        for url in urls:
            parsed = self.parse_url(url)
            if parsed and parsed.username not in seen:
                seen.add(parsed.username)
                results.append(parsed)
        return results

    def _normalize_url_string(self, url: str) -> str:
        cleaned = url.strip()
        if not cleaned.lower().startswith(("http://", "https://")):
            cleaned = "https://" + cleaned.lstrip("/")
        return cleaned

    def _extract_username(self, url: str) -> str | None:
        try:
            parsed = urlparse(url)
        except ValueError:
            return None

        host = (parsed.netloc or "").lower()
        if not host.endswith("instagram.com"):
            return None
        if host not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
            return None

        path = parsed.path or ""
        first_segment = path.strip("/").split("/")[0].lower() if path.strip("/") else ""
        if not first_segment or first_segment in _EXCLUDED_SEGMENTS:
            return None

        match = _PROFILE_PATH_PATTERN.match(path)
        if not match:
            return None

        username = match.group(1).lower()
        if not _VALID_USERNAME_PATTERN.match(username):
            return None
        return username
