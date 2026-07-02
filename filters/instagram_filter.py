"""Instagram 프로필 링크 추출."""

from __future__ import annotations

from dataclasses import dataclass

from adapters.kakao_preprocessor import ChatMessage
from parser.instagram import InstagramNormalizer
from parser.url_extractor import UrlExtractor


@dataclass(frozen=True)
class InstagramHit:
    """Instagram 프로필 1건."""

    username: str
    source_url: str
    message: ChatMessage
    fingerprint: str


class InstagramFilter:
    """메시지에서 Instagram 프로필 username만 추출."""

    def __init__(self) -> None:
        self._url_extractor = UrlExtractor()
        self._normalizer = InstagramNormalizer()

    def extract_from_messages(self, messages: list[ChatMessage]) -> list[InstagramHit]:
        hits: list[InstagramHit] = []
        seen_in_batch: set[str] = set()
        for msg in messages:
            urls = self._url_extractor.extract(msg.text)
            profiles = self._normalizer.parse_text(msg.text, urls)
            for profile in profiles:
                if profile.username in seen_in_batch:
                    continue
                seen_in_batch.add(profile.username)
                fingerprint = self.build_fingerprint(msg, profile.username)
                hits.append(
                    InstagramHit(
                        username=profile.username,
                        source_url=profile.source_url,
                        message=msg,
                        fingerprint=fingerprint,
                    )
                )
        return hits

    @staticmethod
    def build_fingerprint(msg: ChatMessage, username: str) -> str:
        payload = (
            f"{msg.room_name}|{msg.datetime.isoformat()}|"
            f"{msg.author}|{username}|{msg.text}"
        )
        import hashlib

        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
