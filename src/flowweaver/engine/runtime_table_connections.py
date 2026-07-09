from __future__ import annotations

import sqlite3

from flowweaver.engine.runtime_table_sql import table_location as _table_location
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.table_ref import TableRefModel


def connect_runtime_table(
    table_ref: TableRefModel,
    *,
    provider_id: str,
    busy_timeout_ms: int,
) -> sqlite3.Connection:
    validate_runtime_table_ref(table_ref, provider_id=provider_id)
    database_path, _ = _table_location(table_ref)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def validate_runtime_table_ref(
    table_ref: TableRefModel,
    *,
    provider_id: str,
) -> None:
    if table_ref.provider_id != provider_id:
        raise ValueError("table_ref belongs to a different provider")
    if table_ref.storage_kind != TableStorageKind.RUNTIME_SQL:
        raise ValueError("SQLiteRuntimeTableProvider only supports RUNTIME_SQL")
