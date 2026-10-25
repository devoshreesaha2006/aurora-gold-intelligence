from pathlib import Path
from sqlalchemy.engine import make_url

from backend.app.config import PROJECT_ROOT, Settings


def test_relative_sqlite_database_path_is_anchored_to_project_root():
    settings = Settings(database_url="sqlite:///./aurora.db")

    assert make_url(settings.database_url).database == (PROJECT_ROOT / "aurora.db").as_posix()


def test_absolute_sqlite_database_path_is_preserved():
    explicit_path = (PROJECT_ROOT / "data" / "aurora-custom.db").resolve()
    settings = Settings(database_url=f"sqlite:///{explicit_path.as_posix()}")

    assert settings.database_url == f"sqlite:///{explicit_path.as_posix()}"


def test_non_sqlite_database_url_is_preserved():
    url = "postgresql://aurora:secret@localhost/market"

    assert Settings(database_url=url).database_url == url
