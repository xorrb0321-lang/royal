"""Instagram 계정 저장소."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum

from database.connection import DatabaseConnection
from database.schema import SchemaManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SaveResult(Enum):
    """저장 결과."""

    NEW = "new"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class AccountRecord:
    """저장된 계정 레코드."""

    id: int
    username: str
    created_at: str


class InstagramRepository:
    """instagram_accounts 테이블 접근."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self._connection = connection
        self._schema = SchemaManager()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection.session() as conn:
            self._schema.initialize(conn)

    def save_if_new(self, username: str) -> SaveResult:
        """username이 없으면 저장."""
        normalized = username.strip().lower()
        if not normalized:
            return SaveResult.DUPLICATE

        with self._connection.session() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO instagram_accounts (username)
                    VALUES (?)
                    """,
                    (normalized,),
                )
                if cursor.rowcount == 1:
                    logger.info("instagram 링크 저장: %s", normalized)
                    return SaveResult.NEW
                logger.info("이미 존재하는 username: %s", normalized)
                return SaveResult.DUPLICATE
            except sqlite3.Error as exc:
                logger.error("DB 저장 실패: username=%s, error=%s", normalized, exc)
                raise

    def exists(self, username: str) -> bool:
        """username 존재 여부."""
        normalized = username.strip().lower()
        with self._connection.session() as conn:
            row = conn.execute(
                "SELECT 1 FROM instagram_accounts WHERE username = ? LIMIT 1",
                (normalized,),
            ).fetchone()
            return row is not None

    def count(self) -> int:
        """저장된 계정 수."""
        with self._connection.session() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM instagram_accounts").fetchone()
            return int(row["cnt"]) if row else 0

    def list_all(self, limit: int = 100, offset: int = 0) -> list[AccountRecord]:
        """계정 목록 조회."""
        with self._connection.session() as conn:
            rows = conn.execute(
                """
                SELECT id, username, created_at
                FROM instagram_accounts
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            return [
                AccountRecord(id=row["id"], username=row["username"], created_at=row["created_at"])
                for row in rows
            ]
