from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner
from flowweaver.nodes.builtin_table_node_types import (
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
    STATUS_OUTPUT_NODE_TYPES,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetResolutionStatus,
    default_current_output_target,
    resolve_configured_output_targets,
)


class BuiltinTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
        memory_provider: MemoryTableProvider | None = None,
    ) -> None:
        memory_provider = memory_provider or MemoryTableProvider()
        self._context = BuiltinTableNodeContext(
            store=store,
            registry=registry,
            table_provider=table_provider,
            memory_provider=memory_provider,
            sql_mapping_runner=SqlMappingNodeRunner(store=store),
        )
        self._handler_registry = _create_builtin_table_node_handler_registry()

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            output_refs = self._execute_node(task)
        except BuiltinTableNodeValidationError as exc:
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.FAILED,
                error={
                    "error_code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "origin": ErrorOrigin.NODE.value,
                },
                started_at=started_at,
                finished_at=utc_now(),
            )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[table_ref.table_ref_id for table_ref in output_refs],
            output_slot_bindings=_output_slot_bindings_for_result(task, output_refs),
            summary=_table_output_summary(output_refs),
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_node(self, task: NodeTaskModel) -> list[TableRefModel]:
        handler = self._handler_registry.get(task.node_type)
        if handler is not None:
            return handler.execute(task, self._context)
        raise BuiltinTableNodeValidationError(
            f"Unsupported builtin node type: {task.node_type}"
        )


def _create_builtin_table_node_handler_registry():
    from flowweaver.nodes.builtin_table import (
        create_builtin_table_node_handler_registry,
    )

    return create_builtin_table_node_handler_registry()


def _table_output_summary(output_refs: list[TableRefModel]) -> dict[str, Any]:
    return {
        "output_ref_count": len(output_refs),
        "outputs": [
            {
                "table_ref_id": table_ref.table_ref_id,
                "logical_table_id": table_ref.logical_table_id,
                "role": table_ref.role.value,
                "storage_kind": table_ref.storage_kind.value,
            }
            for table_ref in output_refs
        ],
    }


def _output_slot_bindings_for_result(
    task: NodeTaskModel,
    output_refs: list[TableRefModel],
) -> dict[str, str]:
    if not output_refs:
        return {}
    output_ref_ids = [table_ref.table_ref_id for table_ref in output_refs]
    if task.node_type == SAVE_MEMORY_TABLE_NODE_TYPE:
        return _sequence_output_slot_bindings(("out", "memory"), output_ref_ids)
    if task.node_type == SAVE_RUN_TABLE_NODE_TYPE:
        return _sequence_output_slot_bindings(("out", "transit"), output_ref_ids)
    if task.node_type in STATUS_OUTPUT_NODE_TYPES:
        return _sequence_output_slot_bindings(("status",), output_ref_ids)
    target_bindings = _primary_output_target_slot_bindings(task, output_refs)
    if target_bindings:
        return target_bindings
    if len(output_ref_ids) == 1:
        return {"out": output_ref_ids[0]}
    return {}


def _primary_output_target_slot_bindings(
    task: NodeTaskModel,
    output_refs: list[TableRefModel],
) -> dict[str, str]:
    targets = _primary_output_targets(task.config)
    if targets is None or len(targets) != len(output_refs):
        return {}
    return {
        target.slot: table_ref.table_ref_id
        for target, table_ref in zip(targets, output_refs, strict=True)
    }


def _primary_output_targets(
    config: dict[str, Any],
) -> tuple[TableOutputTarget, ...] | None:
    resolution = resolve_configured_output_targets(config)
    if resolution.status == TableOutputTargetResolutionStatus.NO_CONFIG:
        return (default_current_output_target("out"),)
    if resolution.status == TableOutputTargetResolutionStatus.ERROR:
        return None
    targets = list(resolution.targets)
    if _output_save_enabled(config) and not any(
        target.slot == "out" for target in targets
    ):
        targets.insert(0, default_current_output_target("out"))
    if not targets:
        return (default_current_output_target("out"),)
    return tuple(targets)


def _output_save_enabled(config: dict[str, Any]) -> bool:
    output_save = config.get("output_save")
    return isinstance(output_save, dict) and output_save.get("enabled") is True


def _sequence_output_slot_bindings(
    slots: Sequence[str],
    output_ref_ids: Sequence[str],
) -> dict[str, str]:
    return {
        slot: output_ref_id
        for slot, output_ref_id in zip(slots, output_ref_ids, strict=False)
    }
