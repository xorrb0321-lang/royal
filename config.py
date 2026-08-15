"""Configuration for Instagram session management."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class InstagramConfig:
    username: str
    password: str
    totp_secret: str | None
    session_storage: str
    session_file: Path
    redis_url: str
    redis_session_key: str
    proxy: str | None
    country: str
    locale: str
    timezone_offset: int


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_config() -> InstagramConfig:
    session_file = Path(os.getenv("SESSION_FILE", "sessions/session.json"))
    totp_secret = os.getenv("IG_TOTP_SECRET", "").strip() or None

    return InstagramConfig(
        username=_require("IG_USERNAME"),
        password=_require("IG_PASSWORD"),
        totp_secret=totp_secret,
        session_storage=os.getenv("SESSION_STORAGE", "file").strip().lower(),
        session_file=session_file,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        redis_session_key=os.getenv("REDIS_SESSION_KEY", "ig:session:default"),
        proxy=os.getenv("IG_PROXY", "").strip() or None,
        country=os.getenv("IG_COUNTRY", "US"),
        locale=os.getenv("IG_LOCALE", "en_US"),
        timezone_offset=int(os.getenv("IG_TIMEZONE_OFFSET", "-14400")),
    )
