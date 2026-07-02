"""애플리케이션 설정 로더."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "settings.yaml"


@dataclass(frozen=True)
class AppConfig:
    """앱 전역 설정."""

    name: str = "kakao-instagram-collector"
    headless: bool = True


@dataclass(frozen=True)
class KakaoConfig:
    """카카오톡 프로세스 관련 설정."""

    process_name: str = "KakaoTalk.exe"
    reconnect_interval_sec: float = 10.0
    room_rescan_interval_sec: float = 60.0


@dataclass(frozen=True)
class CollectorConfig:
    """UI 수집기 설정."""

    polling_interval_sec: float = 3.0
    message_hash_cache_size: int = 1000
    uia_retry_count: int = 3
    uia_retry_base_delay_sec: float = 0.5


@dataclass(frozen=True)
class DatabaseConfig:
    """SQLite 설정."""

    path: str = "data/instagram.db"


@dataclass(frozen=True)
class LoggingConfig:
    """로깅 설정."""

    directory: str = "logs"
    level: str = "INFO"
    max_bytes: int = 10_485_760
    backup_count: int = 5


@dataclass(frozen=True)
class ParserConfig:
    """파서 및 채팅방 필터 설정."""

    room_title_whitelist: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Settings:
    """전체 설정 루트."""

    app: AppConfig = field(default_factory=AppConfig)
    kakao: KakaoConfig = field(default_factory=KakaoConfig)
    collector: CollectorConfig = field(default_factory=CollectorConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    base_dir: Path = field(default_factory=lambda: Path.cwd())

    def resolve_path(self, relative: str) -> Path:
        """상대 경로를 base_dir 기준 절대 경로로 변환."""
        path = Path(relative)
        if path.is_absolute():
            return path
        return self.base_dir / path


def _build_dataclass(cls: type, data: dict[str, Any]) -> Any:
    """알려진 필드만으로 dataclass 인스턴스 생성."""
    field_names = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def load_settings(path: Path | None = None, base_dir: Path | None = None) -> Settings:
    """YAML 설정 파일을 로드."""
    settings_path = path or _DEFAULT_SETTINGS_PATH
    with settings_path.open(encoding="utf-8") as fp:
        raw: dict[str, Any] = yaml.safe_load(fp) or {}

    return Settings(
        app=_build_dataclass(AppConfig, raw.get("app", {})),
        kakao=_build_dataclass(KakaoConfig, raw.get("kakao", {})),
        collector=_build_dataclass(CollectorConfig, raw.get("collector", {})),
        database=_build_dataclass(DatabaseConfig, raw.get("database", {})),
        logging=_build_dataclass(LoggingConfig, raw.get("logging", {})),
        parser=_build_dataclass(ParserConfig, raw.get("parser", {})),
        base_dir=base_dir or Path.cwd(),
    )
