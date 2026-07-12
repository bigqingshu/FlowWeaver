from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from flowweaver.common.config import MemoryTableLimits
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.memory_table_warnings import (
    MemoryTableSoftLimitWarningModel,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTargetKind,
)


@dataclass(frozen=True)
class TableOutputWriteResult:
    slot: str
    target_kind: TableOutputTargetKind
    table_ref: TableRefModel
    write_mode: str
    affected_rows: int
    target_existed: bool = False
    memory_table_soft_limit_warning: MemoryTableSoftLimitWarningModel | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "output_slot": self.slot,
            "target_type": self.target_kind.value,
            "target_table": self.table_ref.logical_table_id,
            "target_table_ref_id": self.table_ref.table_ref_id,
            "storage_kind": self.table_ref.storage_kind.value,
            "role": self.table_ref.role.value,
            "write_mode": self.write_mode,
            "affected_rows": self.affected_rows,
            "target_existed": self.target_existed,
        }


class TableNodeOutputContext(Protocol):
    @property
    def memory_table_limits(self) -> MemoryTableLimits:
        ...

    @property
    def registry(self) -> RuntimeDataRegistry:
        ...

    def publish_row_batches(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
        role: TableRole = TableRole.CURRENT,
        version: int = 1,
    ) -> TableRefModel:
        ...

    def create_memory_table_from_batches(
        self,
        task: NodeTaskModel,
        *,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        ...

    def replace_memory_table_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        ...

    def replace_runtime_table_batches(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableRefModel:
        ...
