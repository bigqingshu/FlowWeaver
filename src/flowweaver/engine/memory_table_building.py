from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.engine.memory_table_rows import normalize_rows as _normalize_rows
from flowweaver.engine.memory_table_storage import MemoryTable
from flowweaver.protocols.table_ref import FieldSchemaModel


def build_memory_table_from_batches(
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> MemoryTable:
    schema_copy = list(schema)
    cleaned_rows: list[dict[str, Any]] = []
    for rows in row_batches:
        cleaned_rows.extend(_normalize_rows(schema_copy, rows))
    return MemoryTable(schema=schema_copy, rows=cleaned_rows)
