from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.protocols.enums import TableRole, TableStorageKind

OUTPUT_TARGET_CONFIG_KEY = "output_target"
OUTPUT_TARGETS_CONFIG_KEYS = ("output_targets", "output_table_targets")
OUTPUT_SAVE_CONFIG_KEY = "output_save"


class TableOutputTargetKind(str, Enum):
    CURRENT = "current"
    NEW_MEMORY = "new_memory"
    NEW_RUNTIME_SQL = "new_runtime_sql"
    EXISTING_MEMORY = "existing_memory"
    EXISTING_RUNTIME_SQL = "existing_runtime_sql"


class TableOutputTargetResolutionStatus(str, Enum):
    NO_CONFIG = "NO_CONFIG"
    RESOLVED = "RESOLVED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class TableOutputTarget:
    slot: str
    target_kind: TableOutputTargetKind
    role: TableRole
    storage_kind: TableStorageKind | None = None
    logical_table_id: str | None = None

    @property
    def is_existing_target(self) -> bool:
        return self.target_kind in {
            TableOutputTargetKind.EXISTING_MEMORY,
            TableOutputTargetKind.EXISTING_RUNTIME_SQL,
        }

    @property
    def is_new_target(self) -> bool:
        return self.target_kind in {
            TableOutputTargetKind.NEW_MEMORY,
            TableOutputTargetKind.NEW_RUNTIME_SQL,
        }


@dataclass(frozen=True)
class TableOutputTargetIssue:
    slot: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class TableOutputTargetResolution:
    status: TableOutputTargetResolutionStatus
    targets: tuple[TableOutputTarget, ...] = ()
    issue: TableOutputTargetIssue | None = None


def default_current_output_target(slot: str = "out") -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.CURRENT,
        role=TableRole.CURRENT,
    )
