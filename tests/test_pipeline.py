"""ExportPipeline 통합 테스트."""

from pathlib import Path

from app.pipeline import ExportPipeline
from config.settings import Settings, load_settings


def test_pipeline_extracts_instagram(tmp_path: Path) -> None:
    base = tmp_path
    exports = base / "exports"
    exports.mkdir()
    fixture = Path(__file__).parent / "fixtures" / "sample_export_win_ko.txt"
    (exports / "sample.txt").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    settings = load_settings(base_dir=base)

    pipeline = ExportPipeline(settings)
    result = pipeline.process_watch_dir()

    assert result.stats.files_processed == 1
    assert result.stats.new_accounts == 2
    assert pipeline.store.count_accounts() == 2
    assert result.csv_path is not None
    assert result.csv_path.exists()

    # 재처리 시 중복 스킵
    result2 = pipeline.process_watch_dir()
    assert result2.stats.files_processed == 0
