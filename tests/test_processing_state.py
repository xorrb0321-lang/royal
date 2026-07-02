"""ProcessingStateStore 테스트."""

from pathlib import Path

from state.processing_state import ProcessingStateStore, SaveResult


def test_username_dedup(tmp_path: Path) -> None:
    store = ProcessingStateStore(tmp_path / "test.db")
    assert store.save_username("ABC", None, None, None, None) == SaveResult.NEW
    assert store.save_username("abc", None, None, None, None) == SaveResult.DUPLICATE
    assert store.count_accounts() == 1
