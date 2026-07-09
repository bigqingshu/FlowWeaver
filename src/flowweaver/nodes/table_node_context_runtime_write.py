from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import suppress
from typing import Any

from flowweaver.nodes.table_node_errors import BuiltinTableNodeValidationError
from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def publish_runtime_row_batches(
    context: Any,
    task: NodeTaskModel,
    *,
    output_name: str,
    schema: Sequence[FieldSchemaModel],
    row_batches: Iterable[Sequence[dict[str, Any]]],
    role: TableRole = TableRole.CURRENT,
    version: int = 1,
) -> TableRefModel:
    staging_ref = context.table_provider.create_staging_table(
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        output_name=output_name,
        schema=schema,
        role=role,
        version=version,
    )
    for rows in row_batches:
        context.table_provider.insert_rows(staging_ref, rows)
    context.registry.register_staging(staging_ref)
    return context.registry.publish(staging_ref.table_ref_id)


def replace_runtime_table_batches(
    context: Any,
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
    staging_ref = context.table_provider.create_staging_table(
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        output_name=staging_output_name,
        schema=schema,
        role=target_ref.role,
        version=target_ref.version,
    )
    try:
        for rows in row_batches:
            context.table_provider.insert_rows(staging_ref, rows)
        context.table_provider.publish_staging(staging_ref, target_ref)
    finally:
        with suppress(Exception):
            context.table_provider.drop_table(staging_ref)
    return target_ref
