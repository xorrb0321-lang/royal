"""데이터베이스 스키마."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_CREATE_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

_CREATE_USERNAME_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_instagram_accounts_username
    ON instagram_accounts (username);
"""

_CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


class SchemaManager:
    """스키마 초기화 및 마이그레이션."""

    def initialize(self, conn: sqlite3.Connection) -> None:
        """스키마 생성."""
        conn.executescript(
            _CREATE_ACCOUNTS_TABLE + _CREATE_USERNAME_INDEX + _CREATE_SCHEMA_VERSION
        )
        current = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if current is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
