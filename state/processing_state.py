"""처리 상태 및 Instagram 계정 저장."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    first_seen_at TEXT NOT NULL,
    message_datetime TEXT,
    author TEXT,
    room_name TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS message_fingerprints (
    fingerprint TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS processed_file_groups (
    group_hash TEXT PRIMARY KEY,
    file_names TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


class SaveResult(Enum):
    NEW = "new"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class AccountRecord:
    username: str
    first_seen_at: str
    message_datetime: str | None
    author: str | None
    room_name: str | None
    source_url: str | None


class ProcessingStateStore:
    """SQLite: 중복 username, 메시지 fingerprint, 파일 그룹 이력."""

    def __init__(self, db_path: Path) -> None:
        self._db = DatabaseConnection(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._db.session() as conn:
            conn.executescript(_SCHEMA)

    def is_fingerprint_seen(self, fingerprint: str) -> bool:
        with self._db.session() as conn:
            row = conn.execute(
                "SELECT 1 FROM message_fingerprints WHERE fingerprint = ? LIMIT 1",
                (fingerprint,),
            ).fetchone()
            return row is not None

    def mark_fingerprint(self, fingerprint: str) -> None:
        with self._db.session() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO message_fingerprints (fingerprint) VALUES (?)",
                (fingerprint,),
            )

    def is_file_group_processed(self, group_hash: str) -> bool:
        with self._db.session() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_file_groups WHERE group_hash = ? LIMIT 1",
                (group_hash,),
            ).fetchone()
            return row is not None

    def mark_file_group(self, group_hash: str, file_names: str) -> None:
        with self._db.session() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_file_groups (group_hash, file_names)
                VALUES (?, ?)
                """,
                (group_hash, file_names),
            )

    def save_username(
        self,
        username: str,
        message_datetime: datetime | None,
        author: str | None,
        room_name: str | None,
        source_url: str | None,
    ) -> SaveResult:
        normalized = username.strip().lower()
        if not normalized:
            return SaveResult.SKIPPED

        now = datetime.now().isoformat(timespec="seconds")
        msg_dt = message_datetime.isoformat(timespec="seconds") if message_datetime else None

        with self._db.session() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO instagram_accounts
                    (username, first_seen_at, message_datetime, author, room_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized, now, msg_dt, author, room_name, source_url),
            )
            if cursor.rowcount == 1:
                logger.info("instagram 링크 저장: %s", normalized)
                return SaveResult.NEW
            logger.info("이미 존재하는 username: %s", normalized)
            return SaveResult.DUPLICATE

    def count_accounts(self) -> int:
        with self._db.session() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM instagram_accounts").fetchone()
            return int(row["c"]) if row else 0

    def list_accounts(self) -> list[AccountRecord]:
        with self._db.session() as conn:
            rows = conn.execute(
                """
                SELECT username, first_seen_at, message_datetime, author, room_name, source_url
                FROM instagram_accounts
                ORDER BY id ASC
                """
            ).fetchall()
            return [
                AccountRecord(
                    username=row["username"],
                    first_seen_at=row["first_seen_at"],
                    message_datetime=row["message_datetime"],
                    author=row["author"],
                    room_name=row["room_name"],
                    source_url=row["source_url"],
                )
                for row in rows
            ]
