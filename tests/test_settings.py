from pathlib import Path

from src import settings


def test_normalize_db_path_empty() -> None:
    assert settings.normalize_db_path(None) is None
    assert settings.normalize_db_path("") is None
    assert settings.normalize_db_path("   ") is None


def test_normalize_db_path_resolves_relative(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    relative = "data/finance.db"
    expected = str(Path(relative).expanduser().resolve(strict=False))
    assert settings.normalize_db_path(relative) == expected


def test_normalize_db_path_expands_user() -> None:
    path = "~/finance.db"
    expected = str(Path(path).expanduser().resolve(strict=False))
    assert settings.normalize_db_path(path) == expected
