"""애플리케이션 설정."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent / "settings.yaml"


@dataclass(frozen=True)
class AppConfig:
    name: str = "kakao-instagram-collector"


@dataclass(frozen=True)
class IngestConfig:
    watch_dir: str = "exports"
    allowed_extensions: list[str] = field(default_factory=lambda: [".txt"])
    incremental: bool = True


@dataclass(frozen=True)
class ExportConfig:
    output_dir: str = "output"
    csv_filename: str = "instagram_accounts.csv"


@dataclass(frozen=True)
class InstagramConfig:
    enabled: bool = True


@dataclass(frozen=True)
class DatabaseConfig:
    path: str = "data/state.db"


@dataclass(frozen=True)
class LoggingConfig:
    directory: str = "logs"
    level: str = "INFO"
    max_bytes: int = 10_485_760
    backup_count: int = 5


@dataclass(frozen=True)
class Settings:
    app: AppConfig = field(default_factory=AppConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    base_dir: Path = field(default_factory=lambda: Path.cwd())

    def resolve_path(self, relative: str) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else self.base_dir / path


def _build(cls: type, data: dict[str, Any]) -> Any:
    names = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return cls(**{k: v for k, v in data.items() if k in names})


def load_settings(path: Path | None = None, base_dir: Path | None = None) -> Settings:
    settings_path = path or _DEFAULT_SETTINGS_PATH
    with settings_path.open(encoding="utf-8") as fp:
        raw: dict[str, Any] = yaml.safe_load(fp) or {}
    return Settings(
        app=_build(AppConfig, raw.get("app", {})),
        ingest=_build(IngestConfig, raw.get("ingest", {})),
        export=_build(ExportConfig, raw.get("export", {})),
        instagram=_build(InstagramConfig, raw.get("instagram", {})),
        database=_build(DatabaseConfig, raw.get("database", {})),
        logging=_build(LoggingConfig, raw.get("logging", {})),
        base_dir=base_dir or Path.cwd(),
    )
