from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_storage_kinds import (
    NODE_EXECUTION_READABLE_TABLE_STORAGE_KINDS,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
    TableOutputTargetResolutionStatus,
    default_current_output_target,
    resolve_configured_output_targets,
)


def primary_input_ref(
    task: NodeTaskModel,
    context: BuiltinTableNodeContext,
    *,
    node_type: str,
) -> TableRefModel:
    if task.input_slot_bindings:
        return context.require_input_slot(
            task,
            "in",
            node_type=node_type,
            allowed_storage_kinds=NODE_EXECUTION_READABLE_TABLE_STORAGE_KINDS,
        )
    return context.require_single_input_ref(
        task,
        node_type=node_type,
    )


def publish_primary_table_output(
    task: NodeTaskModel,
    context: BuiltinTableNodeContext,
    *,
    node_type: str,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> list[TableRefModel]:
    targets = primary_output_targets(task.config, node_type=node_type)
    primary_ref = write_table_output_target(
        task,
        context,
        target=targets[0],
        schema=schema,
        row_batches=row_batches,
    )
    output_refs = [primary_ref]
    for target in targets[1:]:
        output_refs.append(
            write_table_output_target(
                task,
                context,
                target=target,
                schema=primary_ref.schema,
                row_batches=context.iter_row_batches(primary_ref),
            )
        )
    return output_refs


def primary_output_targets(
    config: dict[str, Any],
    *,
    node_type: str,
) -> tuple[TableOutputTarget, ...]:
    resolution = resolve_configured_output_targets(config)
    if resolution.status == TableOutputTargetResolutionStatus.NO_CONFIG:
        return (default_current_output_target("out"),)
    if resolution.status == TableOutputTargetResolutionStatus.ERROR:
        issue = resolution.issue
        message = issue.message if issue is not None else "invalid output target"
        raise BuiltinTableNodeValidationError(f"{node_type} {message}")
    targets = list(resolution.targets)
    if output_save_enabled(config) and not any(
        target.slot == "out" for target in targets
    ):
        targets.insert(0, default_current_output_target("out"))
    if not targets:
        return (default_current_output_target("out"),)
    return tuple(targets)


def write_table_output_target(
    task: NodeTaskModel,
    context: BuiltinTableNodeContext,
    *,
    target: TableOutputTarget,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
) -> TableRefModel:
    if target.is_existing_target:
        result = context.replace_output_target_batches(
            task,
            target=target,
            schema=schema,
            row_batches=row_batches,
        )
    else:
        result = context.publish_output_target_batches(
            task,
            target=target,
            output_name=f"{task.node_instance_id}_output",
            schema=schema,
            row_batches=row_batches,
        )
    return result.table_ref


def output_save_enabled(config: dict[str, Any]) -> bool:
    output_save = config.get("output_save")
    return isinstance(output_save, dict) and output_save.get("enabled") is True
