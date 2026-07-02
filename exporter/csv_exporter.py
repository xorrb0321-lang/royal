"""CSV보내기."""

from __future__ import annotations

import csv
from pathlib import Path

from state.processing_state import AccountRecord, ProcessingStateStore
from utils.logger import get_logger

logger = get_logger(__name__)

_CSV_HEADERS = (
    "username",
    "first_seen_at",
    "message_datetime",
    "author",
    "room_name",
    "source_url",
)


class CsvExporter:
    """SQLite 계정 목록 → CSV (엑셀 호환 UTF-8 BOM)."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def output_path(self) -> Path:
        return self._output_path

    def export_from_store(self, store: ProcessingStateStore) -> Path:
        records = store.list_accounts()
        self._write(records)
        logger.info("CSV 저장 완료: %s (%d rows)", self._output_path, len(records))
        return self._output_path

    def _write(self, records: list[AccountRecord]) -> None:
        with self._output_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=_CSV_HEADERS)
            writer.writeheader()
            for rec in records:
                writer.writerow(
                    {
                        "username": rec.username,
                        "first_seen_at": rec.first_seen_at,
                        "message_datetime": rec.message_datetime or "",
                        "author": rec.author or "",
                        "room_name": rec.room_name or "",
                        "source_url": rec.source_url or "",
                    }
                )
