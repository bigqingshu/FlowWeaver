from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from flowweaver.engine.runtime_table_sql import quote_identifier as _quote_identifier
from flowweaver.engine.runtime_table_sql import sqlite_type as _sqlite_type
from flowweaver.engine.runtime_table_sql import table_location as _table_location
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def runtime_table_columns_sql(schema: Sequence[FieldSchemaModel]) -> str:
    return ", ".join(
        f"{_quote_identifier(field.name)} {_sqlite_type(field.data_type)}"
        for field in schema
    )


def create_runtime_table_on_connection(
    connection: sqlite3.Connection,
    table_ref: TableRefModel,
    *,
    if_not_exists: bool = False,
) -> None:
    _, table_name = _table_location(table_ref)
    existence_clause = " IF NOT EXISTS" if if_not_exists else ""
    columns_sql = runtime_table_columns_sql(table_ref.schema)
    connection.execute(
        f"CREATE TABLE{existence_clause} "
        f"{_quote_identifier(table_name)} ({columns_sql})"
    )


def drop_runtime_table_on_connection(
    connection: sqlite3.Connection,
    table_ref: TableRefModel,
) -> None:
    _, table_name = _table_location(table_ref)
    connection.execute(f"DROP TABLE IF EXISTS {_quote_identifier(table_name)}")


def publish_runtime_staging_on_connection(
    connection: sqlite3.Connection,
    *,
    staging_ref: TableRefModel,
    published_ref: TableRefModel,
) -> None:
    if staging_ref.lifecycle_status != LifecycleStatus.STAGING:
        raise ValueError("publish_staging requires a STAGING source")
    if published_ref.lifecycle_status != LifecycleStatus.PUBLISHED:
        raise ValueError("publish_staging requires a PUBLISHED target")
    staging_database, staging_table = _table_location(staging_ref)
    published_database, published_table = _table_location(published_ref)
    if staging_database != published_database:
        raise ValueError("staging and published tables must share a runtime database")
    if staging_ref.schema_fingerprint != published_ref.schema_fingerprint:
        raise ValueError("published table schema must match staging schema")
    quoted_columns = ", ".join(
        _quote_identifier(field.name) for field in staging_ref.schema
    )
    connection.execute("BEGIN")
    drop_runtime_table_on_connection(connection, published_ref)
    create_runtime_table_on_connection(connection, published_ref)
    connection.execute(
        f"INSERT INTO {_quote_identifier(published_table)} "
        f"({quoted_columns}) "
        f"SELECT {quoted_columns} FROM {_quote_identifier(staging_table)}"
    )
    connection.execute("COMMIT")
