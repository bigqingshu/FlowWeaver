from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from flowweaver.engine.runtime_models import (
    InputSnapshot,
    ReadLease,
    SharedPublication,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.table_ref import TableRefModel


class SharedTableVersionPolicy(str, Enum):
    LATEST = "LATEST"
    EXACT_VERSION = "EXACT_VERSION"


@dataclass(frozen=True)
class SharedTableReadResult:
    publication: SharedPublication
    table_refs: tuple[TableRefModel, ...]
    input_snapshot: InputSnapshot
    read_lease: ReadLease


class SharedTableReader:
    def __init__(self, store: RuntimeStore) -> None:
        self._store = store

    def read(
        self,
        *,
        consumer_workflow_run_id: str,
        share_name: str,
        version_policy: SharedTableVersionPolicy | str,
        exact_version: int | None = None,
        selected_members: tuple[str, ...] | None = None,
        lease_expires_at: datetime,
    ) -> SharedTableReadResult:
        policy = SharedTableVersionPolicy(version_policy)
        acquisition = self._store.acquire_shared_table_read(
            workflow_run_id=consumer_workflow_run_id,
            share_name=share_name,
            version_policy=policy.value,
            exact_version=exact_version,
            selected_members=selected_members,
            expires_at=lease_expires_at,
        )
        return SharedTableReadResult(
            publication=acquisition.publication,
            table_refs=acquisition.table_refs,
            input_snapshot=acquisition.input_snapshot,
            read_lease=acquisition.read_lease,
        )
