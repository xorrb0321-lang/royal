"""Repository 테스트."""

from pathlib import Path

from database.connection import DatabaseConnection
from database.repository import InstagramRepository, SaveResult


def test_save_if_new_and_duplicate(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    repo = InstagramRepository(DatabaseConnection(db_path))

    assert repo.save_if_new("ABC") == SaveResult.NEW
    assert repo.save_if_new("abc") == SaveResult.DUPLICATE
    assert repo.exists("AbC") is True
    assert repo.count() == 1

    records = repo.list_all()
    assert len(records) == 1
    assert records[0].username == "abc"
