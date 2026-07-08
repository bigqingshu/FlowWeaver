from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    NodeDefinitionCatalogStateView,
    NodeDefinitionView,
    NodePortDefinitionView,
    NodeTableInputSlotView,
    NodeTableOutputSlotView,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_node_registry,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.node_executor.builtin_fault import BUILTIN_FAULT_NODE_TYPES
from flowweaver.nodes.registry import (
    NodeDefinitionSpec,
    NodePortSpec,
    NodeRegistry,
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)

router = APIRouter(
    prefix="/api/v1/node-definitions",
    tags=["node-definitions"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_node_definitions(
    request: Request,
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    definitions = [
        _to_node_definition_view(definition)
        for definition in registry.list_definitions()
        if definition.node_type not in BUILTIN_FAULT_NODE_TYPES
    ]
    return ok_response(
        request,
        [definition.model_dump(mode="json") for definition in definitions],
    )


@router.get("/state", response_model=APIResponseModel)
def get_node_definition_catalog_state(
    request: Request,
    registry: Annotated[NodeRegistry, Depends(get_node_registry)],
):
    state = registry.catalog_state(excluded_node_types=BUILTIN_FAULT_NODE_TYPES)
    return ok_response(
        request,
        NodeDefinitionCatalogStateView(
            catalog_hash=state.catalog_hash,
            node_count=state.node_count,
        ).model_dump(mode="json"),
    )


def _to_node_definition_view(definition: NodeDefinitionSpec) -> NodeDefinitionView:
    return NodeDefinitionView(
        node_type=definition.node_type,
        node_version=definition.node_version,
        display_name=definition.display_name,
        input_ports=[_to_port_view(port) for port in definition.input_ports],
        output_ports=[_to_port_view(port) for port in definition.output_ports],
        input_table_slots=[
            _to_input_table_slot_view(slot)
            for slot in definition.input_table_slots
        ],
        output_table_slots=[
            _to_output_table_slot_view(slot)
            for slot in definition.output_table_slots
        ],
        execution_mode=definition.execution_mode,
        default_timeout_seconds=definition.default_timeout_seconds,
        retry_safe=definition.retry_safe,
        ui_visibility="visible",
        config_schema_version=definition.config_schema_version,
        config_schema=(
            definition.config_schema.to_schema()
            if definition.config_schema is not None
            else None
        ),
    )


def _to_port_view(port: NodePortSpec) -> NodePortDefinitionView:
    return NodePortDefinitionView(name=port.name, required=port.required)


def _to_input_table_slot_view(
    slot: NodeTableInputSlotSpec,
) -> NodeTableInputSlotView:
    return NodeTableInputSlotView(
        name=slot.name,
        required=slot.required,
        allowed_storage_kinds=[
            storage_kind.value for storage_kind in slot.allowed_storage_kinds
        ],
        display_name=slot.display_name,
        description=slot.description,
        default_source=slot.default_source,
    )


def _to_output_table_slot_view(
    slot: NodeTableOutputSlotSpec,
) -> NodeTableOutputSlotView:
    return NodeTableOutputSlotView(
        name=slot.name,
        default_role=slot.default_role.value,
        allow_current=slot.allow_current,
        allow_new_memory=slot.allow_new_memory,
        allow_new_runtime_sql=slot.allow_new_runtime_sql,
        allow_existing_memory=slot.allow_existing_memory,
        allow_existing_runtime_sql=slot.allow_existing_runtime_sql,
        display_name=slot.display_name,
        description=slot.description,
    )
