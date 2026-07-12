from __future__ import annotations

from flowweaver.nodes.builtin_table_execution_result import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.builtin_table_node_types import (
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
)
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    write_table_output_target as _write_table_output_target,
)
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetKind,
    TableOutputTargetResolutionStatus,
    resolve_configured_output_targets,
)

_NodeValidationError = BuiltinTableNodeValidationError


class SaveMemoryTableNodeHandler:
    node_type = SAVE_MEMORY_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveMemoryTableNode mode: {mode}"
            )
        target, warnings = _save_memory_target(task.config)
        write_result = _write_table_output_target(
            task,
            context,
            target=target,
            schema=input_ref.schema,
            row_batches=context.iter_row_batches(input_ref),
        )
        return BuiltinTableExecutionResult(
            output_refs=(input_ref, write_result.table_ref),
            writes=(write_result,),
            output_slot_bindings={
                "out": input_ref.table_ref_id,
                "memory": write_result.table_ref.table_ref_id,
            },
            summary_details={"warnings": warnings} if warnings else {},
        )


class SaveRunTableNodeHandler:
    node_type = SAVE_RUN_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        save_memory = _bool_config(
            task.config,
            "save_memory",
            default=True,
        )
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveRunTableNode mode: {mode}"
            )
        target, warnings = _save_run_target(
            task.config,
            save_memory=save_memory,
        )
        if target is None:
            return BuiltinTableExecutionResult(
                output_refs=(input_ref,),
                output_slot_bindings={"out": input_ref.table_ref_id},
                summary_details={"warnings": warnings} if warnings else {},
            )
        write_result = _write_table_output_target(
            task,
            context,
            target=target,
            schema=input_ref.schema,
            row_batches=context.iter_row_batches(input_ref),
        )
        return BuiltinTableExecutionResult(
            output_refs=(input_ref, write_result.table_ref),
            writes=(write_result,),
            output_slot_bindings={
                "out": input_ref.table_ref_id,
                "transit": write_result.table_ref.table_ref_id,
            },
            summary_details={"warnings": warnings} if warnings else {},
        )


def _save_memory_target(
    config: dict[str, object],
) -> tuple[TableOutputTarget, list[str]]:
    targets, has_explicit_targets = _save_targets(
        config,
        node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
        output_slot="memory",
    )
    warnings: list[str] = []
    if has_explicit_targets:
        target = targets.get("memory")
        if target is None:
            raise _NodeValidationError(
                "SaveMemoryTableNode output_targets requires memory"
            )
        _require_memory_target(target, node_type=SAVE_MEMORY_TABLE_NODE_TYPE)
        legacy_name = _optional_named_output(config, ("table_name",))
        if legacy_name is not None and legacy_name != target.logical_table_id:
            warnings.append(
                "legacy table_name ignored in favor of output_targets.memory"
            )
        return target, warnings
    table_name = _named_output_config(
        config,
        node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
        keys=("table_name",),
    )
    return _new_memory_target("memory", table_name), warnings


def _save_run_target(
    config: dict[str, object],
    *,
    save_memory: bool,
) -> tuple[TableOutputTarget | None, list[str]]:
    targets, has_explicit_targets = _save_targets(
        config,
        node_type=SAVE_RUN_TABLE_NODE_TYPE,
        output_slot="transit",
    )
    warnings: list[str] = []
    if has_explicit_targets:
        target = targets.get("transit")
        if target is None:
            return None, warnings
        _require_memory_target(target, node_type=SAVE_RUN_TABLE_NODE_TYPE)
        if not save_memory:
            warnings.append(
                "legacy save_memory=false ignored in favor of output_targets.transit"
            )
        legacy_name = _optional_named_output(
            config,
            ("transit_name", "table_name"),
        )
        if legacy_name is not None and legacy_name != target.logical_table_id:
            warnings.append(
                "legacy transit name ignored in favor of output_targets.transit"
            )
        return target, warnings
    if not save_memory:
        return None, warnings
    table_name = _named_output_config(
        config,
        node_type=SAVE_RUN_TABLE_NODE_TYPE,
        keys=("transit_name", "table_name"),
    )
    return _new_memory_target("transit", table_name), warnings


def _save_targets(
    config: dict[str, object],
    *,
    node_type: str,
    output_slot: str,
) -> tuple[dict[str, TableOutputTarget], bool]:
    resolution = resolve_configured_output_targets(config)
    if resolution.status == TableOutputTargetResolutionStatus.ERROR:
        issue = resolution.issue
        message = issue.message if issue is not None else "invalid output target"
        raise _NodeValidationError(f"{node_type} {message}")
    if resolution.status == TableOutputTargetResolutionStatus.NO_CONFIG:
        return {}, False
    targets = {target.slot: target for target in resolution.targets}
    unsupported_slots = set(targets) - {"out", output_slot}
    if unsupported_slots:
        raise _NodeValidationError(
            f"{node_type} unsupported output slots: {sorted(unsupported_slots)}"
        )
    out_target = targets.get("out")
    if (
        out_target is not None
        and out_target.target_kind != TableOutputTargetKind.CURRENT
    ):
        raise _NodeValidationError(f"{node_type} out must remain current pass-through")
    return targets, True


def _require_memory_target(target: TableOutputTarget, *, node_type: str) -> None:
    if target.target_kind not in {
        TableOutputTargetKind.NEW_MEMORY,
        TableOutputTargetKind.EXISTING_MEMORY,
    }:
        raise _NodeValidationError(
            f"{node_type} {target.slot} requires a memory output target"
        )


def _new_memory_target(slot: str, table_name: str) -> TableOutputTarget:
    return TableOutputTarget(
        slot=slot,
        target_kind=TableOutputTargetKind.NEW_MEMORY,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
        logical_table_id=table_name,
    )


def _optional_named_output(
    config: dict[str, object],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
