from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session


@contextmanager
def immediate_session(
    engine: Engine,
    *,
    database_url: str | None = None,
) -> Iterator[Session]:
    connection: Connection = engine.connect()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        if database_url is not None and not database_url.startswith("sqlite"):
            connection.begin()
        else:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        yield session
        session.flush()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        session.close()
        connection.close()
