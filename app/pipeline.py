"""export 처리 파이프라인."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from adapters.kakao_preprocessor import KakaoExportAdapter
from config.settings import Settings
from exporter.csv_exporter import CsvExporter
from filters.instagram_filter import InstagramFilter
from filters.system_message_filter import SystemMessageFilter
from ingest.file_loader import ExportFileLoader
from ingest.split_file_merger import SplitFileMerger
from state.processing_state import ProcessingStateStore, SaveResult
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineStats:
    """처리 통계."""

    files_processed: int = 0
    messages_parsed: int = 0
    instagram_found: int = 0
    new_accounts: int = 0
    duplicates_skipped: int = 0
    fingerprints_skipped: int = 0


@dataclass
class PipelineResult:
    stats: PipelineStats = field(default_factory=PipelineStats)
    csv_path: Path | None = None


class ExportPipeline:
    """txt 파싱 → Instagram 추출 → 중복 제거 → CSV."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._adapter = KakaoExportAdapter()
        self._system_filter = SystemMessageFilter()
        self._instagram_filter = InstagramFilter()
        self._loader = ExportFileLoader(settings.ingest)
        self._merger = SplitFileMerger()
        db_path = settings.resolve_path(settings.database.path)
        self._store = ProcessingStateStore(db_path)
        csv_path = settings.resolve_path(settings.export.output_dir) / settings.export.csv_filename
        self._csv_exporter = CsvExporter(csv_path)

    @property
    def store(self) -> ProcessingStateStore:
        return self._store

    @property
    def csv_path(self) -> Path:
        return self._csv_exporter.output_path

    @property
    def watch_dir(self) -> Path:
        return self._settings.resolve_path(self._settings.ingest.watch_dir)

    def process_paths(self, paths: list[Path]) -> PipelineResult:
        """파일 경로 목록 처리."""
        result = PipelineResult()
        allowed = [p for p in paths if self._loader.is_allowed(p)]
        if not allowed:
            return result

        groups = self._merger.group_export_sets(allowed)
        for group in groups:
            self._process_group(group, result)
        if result.stats.new_accounts > 0 or result.stats.files_processed > 0:
            result.csv_path = self._csv_exporter.export_from_store(self._store)
        return result

    def process_watch_dir(self) -> PipelineResult:
        """감시 폴더 전체 스캔."""
        watch_dir = self.watch_dir
        watch_dir.mkdir(parents=True, exist_ok=True)
        files = self._loader.list_txt_files(watch_dir)
        return self.process_paths(files)

    def _process_group(self, group: list[Path], result: PipelineResult) -> None:
        group_hash = self._merger.group_hash(group)
        if self._settings.ingest.incremental and self._store.is_file_group_processed(group_hash):
            logger.info("이미 처리한 파일 그룹 스킵: %s", group[0].name)
            return

        primary = self._merger.pick_primary(group)
        messages = self._adapter.load_messages(primary)
        result.stats.files_processed += 1
        messages = self._system_filter.filter(messages)
        result.stats.messages_parsed += len(messages)

        hits = self._instagram_filter.extract_from_messages(messages)
        result.stats.instagram_found += len(hits)

        for hit in hits:
            if self._settings.ingest.incremental and self._store.is_fingerprint_seen(hit.fingerprint):
                result.stats.fingerprints_skipped += 1
                continue
            self._store.mark_fingerprint(hit.fingerprint)
            logger.info("instagram 링크 발견: %s", hit.username)
            save = self._store.save_username(
                username=hit.username,
                message_datetime=hit.message.datetime,
                author=hit.message.author,
                room_name=hit.message.room_name,
                source_url=hit.source_url,
            )
            if save == SaveResult.NEW:
                result.stats.new_accounts += 1
            elif save == SaveResult.DUPLICATE:
                result.stats.duplicates_skipped += 1

        names = ", ".join(p.name for p in group)
        self._store.mark_file_group(group_hash, names)
        logger.info("채팅방 파일 처리 완료: %s", names)
