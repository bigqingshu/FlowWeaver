from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetKind,
)

DEFAULT_ROW_BATCH_SIZE = 1000

if TYPE_CHECKING:
    from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner


class BuiltinTableNodeValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TableOutputWriteResult:
    slot: str
    target_kind: TableOutputTargetKind
    table_ref: TableRefModel
    write_mode: str
    affected_rows: int
    target_existed: bool = False

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


@dataclass(frozen=True)
class BuiltinTableNodeContext:
    store: RuntimeStore
    registry: RuntimeDataRegistry
    table_provider: SQLiteRuntimeTableProvider
    memory_provider: MemoryTableProvider
    sql_mapping_runner: SqlMappingNodeRunner | None = None
    row_batch_size: int = DEFAULT_ROW_BATCH_SIZE

    def input_ref(self, table_ref_id: str) -> TableRefModel:
        return self.registry.get(table_ref_id)

    def require_single_input_ref(
        self,
        task: NodeTaskModel,
        *,
        node_type: str,
    ) -> TableRefModel:
        if len(task.input_refs) != 1:
            raise BuiltinTableNodeValidationError(
                f"{node_type} requires exactly one input_ref"
            )
        return self.input_ref(task.input_refs[0])

    def require_input_slot(
        self,
        task: NodeTaskModel,
        slot: str,
        *,
        node_type: str,
        allowed_storage_kinds: Sequence[TableStorageKind] | None = None,
    ) -> TableRefModel:
        table_ref_id = task.input_slot_bindings.get(slot)
        if table_ref_id is None:
            raise BuiltinTableNodeValidationError(
                f"{node_type} requires input slot: {slot}"
            )
        table_ref = self.input_ref(table_ref_id)
        if (
            allowed_storage_kinds is not None
            and table_ref.storage_kind not in allowed_storage_kinds
        ):
            allowed = ", ".join(kind.value for kind in allowed_storage_kinds)
            raise BuiltinTableNodeValidationError(
                f"{node_type} input slot {slot} requires storage kind: "
                f"{allowed}; got {table_ref.storage_kind.value}"
            )
        return table_ref

    def iter_slot_batches(
        self,
        task: NodeTaskModel,
        slot: str,
        *,
        node_type: str,
        allowed_storage_kinds: Sequence[TableStorageKind] | None = None,
        batch_size: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        table_ref = self.require_input_slot(
            task,
            slot,
            node_type=node_type,
            allowed_storage_kinds=allowed_storage_kinds,
        )
        return self.iter_row_batches(table_ref, batch_size=batch_size)

    def read_all_rows(self, table_ref: TableRefModel) -> list[dict[str, Any]]:
        provider = self._reader_for(table_ref)
        return provider.read_rows(
            table_ref,
            offset=0,
            limit=provider.count_rows(table_ref),
        )

    def count_rows(self, table_ref: TableRefModel) -> int:
        return self._reader_for(table_ref).count_rows(table_ref)

    def iter_row_batches(
        self,
        table_ref: TableRefModel,
        *,
        batch_size: int | None = None,
    ) -> Iterable[list[dict[str, Any]]]:
        limit = self.row_batch_size if batch_size is None else batch_size
        if limit <= 0:
            raise BuiltinTableNodeValidationError("row batch size must be positive")
        provider = self._reader_for(table_ref)
        total_rows = provider.count_rows(table_ref)
        offset = 0
        while offset < total_rows:
            rows = provider.read_rows(
                table_ref,
                offset=offset,
                limit=limit,
            )
            if not rows:
                break
            yield rows
            offset += len(rows)

    def publish_rows(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
        role: TableRole = TableRole.CURRENT,
        version: int = 1,
    ) -> TableRefModel:
        return self.publish_row_batches(
            task,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
            role=role,
            version=version,
        )

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
        staging_ref = self.table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=output_name,
            schema=schema,
            role=role,
            version=version,
        )
        for rows in row_batches:
            self.table_provider.insert_rows(staging_ref, rows)
        self.registry.register_staging(staging_ref)
        return self.registry.publish(staging_ref.table_ref_id)

    def create_memory_table(
        self,
        task: NodeTaskModel,
        *,
        logical_table_id: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
        role: TableRole = TableRole.AUXILIARY,
        version: int = 1,
    ) -> TableRefModel:
        memory_ref = self.memory_provider.create_memory_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            rows=rows,
            role=role,
            version=version,
        )
        self.store.register_table_ref(memory_ref)
        return memory_ref

    def replace_runtime_table_rows(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableRefModel:
        return self.replace_runtime_table_batches(
            task,
            target_ref=target_ref,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
        )

    def replace_runtime_table_batches(
        self,
        task: NodeTaskModel,
        *,
        target_ref: TableRefModel,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableRefModel:
        if target_ref.storage_kind != TableStorageKind.RUNTIME_SQL:
            raise BuiltinTableNodeValidationError(
                "replace_runtime_table_batches requires a RUNTIME_SQL target"
            )
        staging_output_name = f"{output_name}__replace_{target_ref.table_ref_id}"
        staging_ref = self.table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=staging_output_name,
            schema=schema,
            role=target_ref.role,
            version=target_ref.version,
        )
        try:
            for rows in row_batches:
                self.table_provider.insert_rows(staging_ref, rows)
            self.table_provider.publish_staging(staging_ref, target_ref)
        finally:
            with suppress(Exception):
                self.table_provider.drop_table(staging_ref)
        return target_ref

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
        memory_ref = self.memory_provider.create_memory_table_from_batches(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            logical_table_id=logical_table_id,
            schema=schema,
            row_batches=row_batches,
            role=role,
            version=version,
        )
        self.store.register_table_ref(memory_ref)
        return memory_ref

    def replace_memory_table_rows(
        self,
        table_ref: TableRefModel,
        rows: Sequence[dict[str, Any]],
    ) -> None:
        self.memory_provider.replace_rows(table_ref, rows)

    def replace_memory_table_batches(
        self,
        table_ref: TableRefModel,
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> None:
        self.memory_provider.replace_row_batches(table_ref, row_batches)

    def find_latest_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel | None:
        if target.logical_table_id is None or target.storage_kind is None:
            return None
        matches = [
            table_ref
            for table_ref in self.registry.list_by_workflow_run(workflow_run_id)
            if table_ref.logical_table_id == target.logical_table_id
            and table_ref.storage_kind == target.storage_kind
            and table_ref.role == target.role
        ]
        if not matches:
            return None
        return max(matches, key=lambda table_ref: table_ref.version)

    def require_existing_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel:
        if not target.is_existing_target:
            raise BuiltinTableNodeValidationError(
                "output target must be an existing target"
            )
        table_ref = self.find_latest_output_target_ref(
            workflow_run_id=workflow_run_id,
            target=target,
        )
        if table_ref is None:
            raise BuiltinTableNodeValidationError(
                f"output target does not exist: {target.logical_table_id}"
            )
        return table_ref

    def publish_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.publish_output_target_batches(
            task,
            target=target,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
        )

    def publish_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        if target.is_existing_target:
            raise BuiltinTableNodeValidationError(
                "publish_output_target_batches does not accept existing targets"
            )
        if target.is_new_target:
            existing_ref = self.find_latest_output_target_ref(
                workflow_run_id=task.workflow_run_id,
                target=target,
            )
            if existing_ref is not None:
                raise BuiltinTableNodeValidationError(
                    f"output target already exists: {target.logical_table_id}"
                )

        counter = _RowBatchCounter(row_batches)
        if target.target_kind == TableOutputTargetKind.CURRENT:
            table_ref = self.publish_row_batches(
                task,
                output_name=output_name,
                schema=schema,
                row_batches=counter,
                role=target.role,
            )
        elif target.target_kind == TableOutputTargetKind.NEW_MEMORY:
            logical_table_id = _required_target_table_name(target)
            table_ref = self.create_memory_table_from_batches(
                task,
                logical_table_id=logical_table_id,
                schema=schema,
                row_batches=counter,
                role=target.role,
            )
        elif target.target_kind == TableOutputTargetKind.NEW_RUNTIME_SQL:
            logical_table_id = _required_target_table_name(target)
            table_ref = self.publish_row_batches(
                task,
                output_name=logical_table_id,
                schema=schema,
                row_batches=counter,
                role=target.role,
            )
        else:
            raise BuiltinTableNodeValidationError(
                f"unsupported output target kind: {target.target_kind.value}"
            )
        return TableOutputWriteResult(
            slot=target.slot,
            target_kind=target.target_kind,
            table_ref=table_ref,
            write_mode="create",
            affected_rows=counter.row_count,
        )

    def replace_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.replace_output_target_batches(
            task,
            target=target,
            schema=schema,
            row_batches=(rows,),
        )

    def replace_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        target_ref = self.require_existing_output_target_ref(
            workflow_run_id=task.workflow_run_id,
            target=target,
        )
        counter = _RowBatchCounter(row_batches)
        if target.target_kind == TableOutputTargetKind.EXISTING_MEMORY:
            self.replace_memory_table_batches(target_ref, counter)
            table_ref = target_ref
        elif target.target_kind == TableOutputTargetKind.EXISTING_RUNTIME_SQL:
            table_ref = self.replace_runtime_table_batches(
                task,
                target_ref=target_ref,
                output_name=target_ref.logical_table_id,
                schema=schema,
                row_batches=counter,
            )
        else:
            raise BuiltinTableNodeValidationError(
                "replace_output_target_batches requires an existing target"
            )
        return TableOutputWriteResult(
            slot=target.slot,
            target_kind=target.target_kind,
            table_ref=table_ref,
            write_mode="overwrite",
            affected_rows=counter.row_count,
            target_existed=True,
        )

    def _reader_for(self, table_ref: TableRefModel):
        if table_ref.storage_kind == TableStorageKind.MEMORY:
            return self.memory_provider
        if table_ref.storage_kind == TableStorageKind.RUNTIME_SQL:
            return self.table_provider
        raise BuiltinTableNodeValidationError(
            f"Unsupported table storage kind: {table_ref.storage_kind.value}"
        )


class BuiltinTableNodeHandler(Protocol):
    node_type: str

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        ...


class _RowBatchCounter:
    def __init__(self, row_batches: Iterable[Sequence[dict[str, Any]]]) -> None:
        self._row_batches = row_batches
        self.row_count = 0

    def __iter__(self):
        for rows in self._row_batches:
            self.row_count += len(rows)
            yield rows


def _required_target_table_name(target: TableOutputTarget) -> str:
    if target.logical_table_id is None:
        raise BuiltinTableNodeValidationError(
            f"output target {target.slot} requires a table name"
        )
    return target.logical_table_id


class BuiltinTableNodeHandlerRegistry:
    def __init__(
        self,
        handlers: Sequence[BuiltinTableNodeHandler] = (),
    ) -> None:
        self._handlers: dict[str, BuiltinTableNodeHandler] = {}
        for handler in handlers:
            self.register(handler)

    def register(self, handler: BuiltinTableNodeHandler) -> None:
        if handler.node_type in self._handlers:
            raise ValueError(
                f"Duplicate builtin table node handler: {handler.node_type}"
            )
        self._handlers[handler.node_type] = handler

    def get(self, node_type: str) -> BuiltinTableNodeHandler | None:
        return self._handlers.get(node_type)

    def node_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
