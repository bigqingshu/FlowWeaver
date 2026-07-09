from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from flowweaver.protocols.table_ref import FieldSchemaModel


@dataclass
class MemoryTable:
    schema: list[FieldSchemaModel]
    rows: list[dict[str, Any]]


GLOBAL_MEMORY_TABLES: dict[str, MemoryTable] = {}
GLOBAL_MEMORY_TABLES_LOCK = RLock()
