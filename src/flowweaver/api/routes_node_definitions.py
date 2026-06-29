from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    NodeDefinitionView,
    NodePortDefinitionView,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_node_registry,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.node_executor.builtin_fault import BUILTIN_FAULT_NODE_TYPES
from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec, NodeRegistry

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


def _to_node_definition_view(definition: NodeDefinitionSpec) -> NodeDefinitionView:
    return NodeDefinitionView(
        node_type=definition.node_type,
        node_version=definition.node_version,
        display_name=definition.display_name,
        input_ports=[_to_port_view(port) for port in definition.input_ports],
        output_ports=[_to_port_view(port) for port in definition.output_ports],
        execution_mode=definition.execution_mode,
        default_timeout_seconds=definition.default_timeout_seconds,
        retry_safe=definition.retry_safe,
        ui_visibility="visible",
    )


def _to_port_view(port: NodePortSpec) -> NodePortDefinitionView:
    return NodePortDefinitionView(name=port.name, required=port.required)
