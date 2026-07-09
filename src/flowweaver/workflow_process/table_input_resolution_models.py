from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.protocols.enums import TableRole, TableStorageKind


class TableInputResolutionStatus(str, Enum):
    NO_CONFIG = "NO_CONFIG"
    RESOLVED = "RESOLVED"
    WAITING = "WAITING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TableInputSelector:
    slot: str
    source_node_instance_id: str
    output_role: TableRole | None = None
    storage_kind: TableStorageKind | None = None
    logical_table_id: str | None = None
    output_slot: str | None = None


@dataclass(frozen=True)
class TableInputResolutionIssue:
    slot: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class TableInputResolution:
    status: TableInputResolutionStatus
    input_refs: tuple[str, ...] = ()
    input_slot_bindings: dict[str, str] | None = None
    issue: TableInputResolutionIssue | None = None
