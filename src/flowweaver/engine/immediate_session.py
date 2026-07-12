from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from time import sleep
from typing import TypeVar

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

T = TypeVar("T")


@contextmanager
def immediate_session(
    engine: Engine,
    *,
    database_url: str | None = None,
    busy_timeout_ms: int | None = None,
) -> Iterator[Session]:
    connection: Connection = engine.connect()
    session = Session(bind=connection, expire_on_commit=False)
    previous_busy_timeout_ms: int | None = None
    try:
        if database_url is not None and not database_url.startswith("sqlite"):
            connection.begin()
        else:
            if busy_timeout_ms is not None:
                previous_busy_timeout_ms = int(
                    connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
                )
                connection.exec_driver_sql(
                    f"PRAGMA busy_timeout = {max(0, busy_timeout_ms)}"
                )
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        yield session
        session.flush()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        session.close()
        if previous_busy_timeout_ms is not None:
            connection.exec_driver_sql(
                f"PRAGMA busy_timeout = {previous_busy_timeout_ms}"
            )
        connection.close()


def run_immediate_transaction(
    engine: Engine,
    operation: Callable[[Session], T],
    *,
    max_attempts: int = 3,
    retry_delay_seconds: float = 0.01,
    database_url: str | None = None,
    busy_timeout_ms: int = 250,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    for attempt in range(max_attempts):
        try:
            with immediate_session(
                engine,
                database_url=database_url,
                busy_timeout_ms=busy_timeout_ms,
            ) as session:
                return operation(session)
        except OperationalError as exc:
            if attempt + 1 >= max_attempts or not _is_busy_error(exc):
                raise
            sleep(retry_delay_seconds * (attempt + 1))
    raise RuntimeError("Immediate transaction retry exhausted")


def _is_busy_error(error: OperationalError) -> bool:
    message = str(error).lower()
    return "database is locked" in message or "database is busy" in message
