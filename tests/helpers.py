from pathlib import Path
import uuid

from src import db

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema.sql"
TMP_ROOT = REPO_ROOT / ".tmp_test"


def assert_not_data_path(path: Path) -> None:
    resolved = path.resolve()
    data_root = (REPO_ROOT / "data").resolve()
    if str(resolved).startswith(str(data_root)):
        raise AssertionError(f"Tests must not touch data/: {resolved}")
    if str(resolved).startswith("/data"):
        raise AssertionError(f"Tests must not touch /data: {resolved}")


def temp_db_path(prefix: str) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TMP_ROOT / f"{prefix}_{uuid.uuid4().hex}.db"
    assert_not_data_path(path)
    return path


def init_db_at(path: Path):
    assert_not_data_path(path)
    conn = db.connect(str(path))
    db.init_db(conn, str(SCHEMA_PATH))
    return conn


def init_memory_db():
    conn = db.connect(":memory:")
    db.init_db(conn, str(SCHEMA_PATH))
    return conn
