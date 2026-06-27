from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine


def create_sqlite_engine(
    database_url: str,
    *,
    busy_timeout_ms: int = 5000,
) -> Engine:
    engine = create_engine(database_url, future=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
            if not _is_memory_sqlite_url(database_url):
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.close()

    return engine


def sqlite_url(path: str | Path) -> str:
    return f"sqlite:///{Path(path).as_posix()}"


def _is_memory_sqlite_url(database_url: str) -> bool:
    return database_url in {"sqlite://", "sqlite:///:memory:"} or database_url.endswith(
        "/:memory:"
    )
