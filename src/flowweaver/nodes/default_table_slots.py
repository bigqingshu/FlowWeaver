from __future__ import annotations

from flowweaver.nodes.registry import (
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)
from flowweaver.protocols.enums import TableRole, TableStorageKind

_READABLE_TABLE_STORAGE_KINDS = (
    TableStorageKind.RUNTIME_SQL,
    TableStorageKind.MEMORY,
    TableStorageKind.EXTERNAL_SQL,
)
_NODE_EXECUTION_READABLE_TABLE_STORAGE_KINDS = (
    TableStorageKind.RUNTIME_SQL,
    TableStorageKind.MEMORY,
)


def _input_table_slot(
    name: str,
    *,
    display_name: str,
    description: str,
    required: bool = True,
    allowed_storage_kinds: tuple[TableStorageKind, ...] = _READABLE_TABLE_STORAGE_KINDS,
) -> NodeTableInputSlotSpec:
    return NodeTableInputSlotSpec(
        name=name,
        display_name=display_name,
        description=description,
        required=required,
        allowed_storage_kinds=allowed_storage_kinds,
        default_source="upstream_current",
    )


def _single_transform_input_table_slots() -> tuple[NodeTableInputSlotSpec, ...]:
    return (
        _input_table_slot(
            "in",
            display_name="Input table",
            description="Workflow-local table to transform.",
            allowed_storage_kinds=_NODE_EXECUTION_READABLE_TABLE_STORAGE_KINDS,
        ),
    )


def _single_transform_output_table_slots() -> tuple[NodeTableOutputSlotSpec, ...]:
    return (
        NodeTableOutputSlotSpec(
            name="out",
            display_name="Result table",
            description="Primary transformed table for the workflow chain.",
            default_role=TableRole.CURRENT,
            allow_current=True,
            allow_new_memory=True,
            allow_new_runtime_sql=True,
            allow_existing_memory=True,
            allow_existing_runtime_sql=True,
        ),
    )


def _current_output_table_slot(
    name: str,
    *,
    display_name: str,
    description: str,
) -> NodeTableOutputSlotSpec:
    return NodeTableOutputSlotSpec(
        name=name,
        display_name=display_name,
        description=description,
        default_role=TableRole.CURRENT,
        allow_current=True,
    )


def _source_output_table_slot(
    name: str,
    *,
    display_name: str,
    description: str,
) -> NodeTableOutputSlotSpec:
    return NodeTableOutputSlotSpec(
        name=name,
        display_name=display_name,
        description=description,
        default_role=TableRole.CURRENT,
        allow_current=True,
        allow_new_memory=True,
        allow_new_runtime_sql=True,
        allow_existing_memory=True,
        allow_existing_runtime_sql=True,
    )


def _auxiliary_output_table_slot(
    name: str,
    *,
    display_name: str,
    description: str,
    allow_new_memory: bool = False,
    allow_new_runtime_sql: bool = False,
    allow_existing_memory: bool = False,
    allow_existing_runtime_sql: bool = False,
) -> NodeTableOutputSlotSpec:
    return NodeTableOutputSlotSpec(
        name=name,
        display_name=display_name,
        description=description,
        default_role=TableRole.AUXILIARY,
        allow_current=False,
        allow_new_memory=allow_new_memory,
        allow_new_runtime_sql=allow_new_runtime_sql,
        allow_existing_memory=allow_existing_memory,
        allow_existing_runtime_sql=allow_existing_runtime_sql,
    )
