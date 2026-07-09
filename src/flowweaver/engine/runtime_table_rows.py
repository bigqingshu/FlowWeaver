from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from flowweaver.engine.runtime_table_sql import quote_identifier, table_location
from flowweaver.protocols.enums import LifecycleStatus, TableMutability
from flowweaver.protocols.table_ref import TableRefModel


@dataclass(frozen=True)
class RuntimeInsertRowsStatement:
    sql: str
    values: list[list[Any]]


def runtime_insert_rows_statement(
    table_ref: TableRefModel,
    rows: Sequence[dict[str, Any]],
) -> RuntimeInsertRowsStatement | None:
    if not rows:
        return None
    if (
        table_ref.lifecycle_status != LifecycleStatus.STAGING
        or table_ref.mutability != TableMutability.WORKING_MUTABLE
    ):
        raise ValueError("only STAGING working tables can be written")
    _, table_name = table_location(table_ref)
    schema_columns = [field.name for field in table_ref.schema]
    for row in rows:
        unknown_columns = set(row) - set(schema_columns)
        if unknown_columns:
            raise ValueError(
                f"row contains columns not declared in schema: "
                f"{sorted(unknown_columns)}"
            )
    placeholders = ", ".join("?" for _ in schema_columns)
    quoted_columns = ", ".join(quote_identifier(column) for column in schema_columns)
    return RuntimeInsertRowsStatement(
        sql=(
            f"INSERT INTO {quote_identifier(table_name)} "
            f"({quoted_columns}) VALUES ({placeholders})"
        ),
        values=[
            [row.get(column) for column in schema_columns]
            for row in rows
        ],
    )
