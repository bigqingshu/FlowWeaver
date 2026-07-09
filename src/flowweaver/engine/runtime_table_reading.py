from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_table_connections import (
    connect_runtime_table as _connect_runtime_table,
)
from flowweaver.engine.runtime_table_sql import (
    order_clause as _order_clause,
)
from flowweaver.engine.runtime_table_sql import (
    quote_identifier as _quote_identifier,
)
from flowweaver.engine.runtime_table_sql import (
    selected_columns as _selected_columns,
)
from flowweaver.engine.runtime_table_sql import (
    table_location as _table_location,
)
from flowweaver.engine.runtime_table_sql import (
    where_clause as _where_clause,
)
from flowweaver.protocols.table_ref import TableRefModel


def count_runtime_rows(
    table_ref: TableRefModel,
    *,
    provider_id: str,
    busy_timeout_ms: int,
) -> int:
    _, table_name = _table_location(table_ref)
    with _connect_runtime_table(
        table_ref,
        provider_id=provider_id,
        busy_timeout_ms=busy_timeout_ms,
    ) as connection:
        return int(
            connection.execute(
                f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}"
            ).fetchone()[0]
        )


def read_runtime_rows(
    table_ref: TableRefModel,
    *,
    provider_id: str,
    busy_timeout_ms: int,
    offset: int,
    limit: int,
    columns: list[str] | None = None,
    order_by: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if limit < 0:
        raise ValueError("limit must be non-negative")
    _, table_name = _table_location(table_ref)
    selected_columns = _selected_columns(table_ref, columns)
    where_clause, parameters = _where_clause(table_ref, filters)
    order_clause = _order_clause(table_ref, order_by)
    selected_sql = ", ".join(
        _quote_identifier(column) for column in selected_columns
    )
    query = (
        f"SELECT {selected_sql} "
        f"FROM {_quote_identifier(table_name)}"
        f"{where_clause}{order_clause} LIMIT ? OFFSET ?"
    )
    with _connect_runtime_table(
        table_ref,
        provider_id=provider_id,
        busy_timeout_ms=busy_timeout_ms,
    ) as connection:
        cursor = connection.execute(query, [*parameters, limit, offset])
        return [dict(row) for row in cursor.fetchall()]
