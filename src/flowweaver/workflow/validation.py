from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pydantic import ValidationError

from flowweaver.nodes.registry import NodeDefinitionSpec, NodeRegistry
from flowweaver.protocols.base import StrictModel
from flowweaver.workflow.definition import WorkflowDefinitionModel


class WorkflowValidationIssue(StrictModel):
    code: str
    path: str
    message: str


class WorkflowValidationResult(StrictModel):
    valid: bool
    errors: list[WorkflowValidationIssue] = []
    warnings: list[WorkflowValidationIssue] = []


def validate_workflow_definition(
    definition: dict[str, Any] | WorkflowDefinitionModel,
    registry: NodeRegistry,
) -> WorkflowValidationResult:
    try:
        model = (
            definition
            if isinstance(definition, WorkflowDefinitionModel)
            else WorkflowDefinitionModel.model_validate(definition)
        )
    except ValidationError as exc:
        return WorkflowValidationResult(
            valid=False,
            errors=[
                WorkflowValidationIssue(
                    code="SCHEMA_VALIDATION_ERROR",
                    path="definition",
                    message=str(exc),
                )
            ],
        )

    errors: list[WorkflowValidationIssue] = []
    node_ids = [node.node_instance_id for node in model.nodes]
    node_id_set = set(node_ids)
    if len(node_ids) != len(node_id_set):
        errors.append(
            WorkflowValidationIssue(
                code="DUPLICATE_NODE_INSTANCE_ID",
                path="nodes",
                message="Node instance IDs must be unique",
            )
        )

    definitions: dict[str, NodeDefinitionSpec] = {}
    for index, node in enumerate(model.nodes):
        registered = registry.get(node.node_type, node.node_version)
        if registered is None:
            errors.append(
                WorkflowValidationIssue(
                    code="UNKNOWN_NODE_TYPE",
                    path=f"nodes[{index}]",
                    message=(
                        "Unknown node type/version: "
                        f"{node.node_type}@{node.node_version}"
                    ),
                )
            )
            continue
        definitions[node.node_instance_id] = registered

    incoming_ports: set[tuple[str, str]] = set()
    graph: dict[str, list[str]] = defaultdict(list)
    indegree = dict.fromkeys(node_id_set, 0)
    for index, connection in enumerate(model.connections):
        path = f"connections[{index}]"
        if connection.source_node_id not in node_id_set:
            errors.append(
                WorkflowValidationIssue(
                    code="UNKNOWN_SOURCE_NODE",
                    path=path,
                    message=f"Source node does not exist: {connection.source_node_id}",
                )
            )
        if connection.target_node_id not in node_id_set:
            errors.append(
                WorkflowValidationIssue(
                    code="UNKNOWN_TARGET_NODE",
                    path=path,
                    message=f"Target node does not exist: {connection.target_node_id}",
                )
            )

        source_definition = definitions.get(connection.source_node_id)
        if source_definition and connection.source_port not in {
            port.name for port in source_definition.output_ports
        }:
            errors.append(
                WorkflowValidationIssue(
                    code="UNKNOWN_SOURCE_PORT",
                    path=path,
                    message=f"Source port does not exist: {connection.source_port}",
                )
            )

        target_definition = definitions.get(connection.target_node_id)
        if target_definition and connection.target_port not in {
            port.name for port in target_definition.input_ports
        }:
            errors.append(
                WorkflowValidationIssue(
                    code="UNKNOWN_TARGET_PORT",
                    path=path,
                    message=f"Target port does not exist: {connection.target_port}",
                )
            )

        target_key = (connection.target_node_id, connection.target_port)
        if target_key in incoming_ports:
            errors.append(
                WorkflowValidationIssue(
                    code="INPUT_PORT_ALREADY_CONNECTED",
                    path=path,
                    message=(
                        "Input port is already connected: "
                        f"{connection.target_node_id}.{connection.target_port}"
                    ),
                )
            )
        incoming_ports.add(target_key)

        if (
            connection.source_node_id in node_id_set
            and connection.target_node_id in node_id_set
        ):
            graph[connection.source_node_id].append(connection.target_node_id)
            indegree[connection.target_node_id] += 1

    for node in model.nodes:
        node_definition = definitions.get(node.node_instance_id)
        if node_definition is None:
            continue
        for port in node_definition.input_ports:
            port_key = (node.node_instance_id, port.name)
            if port.required and port_key not in incoming_ports:
                errors.append(
                    WorkflowValidationIssue(
                        code="REQUIRED_INPUT_NOT_CONNECTED",
                        path=f"nodes.{node.node_instance_id}",
                        message=f"Required input is not connected: {port.name}",
                    )
                )

    if _has_cycle(node_id_set, graph, indegree):
        errors.append(
            WorkflowValidationIssue(
                code="DAG_CYCLE_DETECTED",
                path="connections",
                message="Workflow contains a cycle",
            )
        )

    return WorkflowValidationResult(valid=not errors, errors=errors, warnings=[])


def _has_cycle(
    node_ids: set[str],
    graph: dict[str, list[str]],
    indegree: dict[str, int],
) -> bool:
    queue = deque([node_id for node_id in node_ids if indegree[node_id] == 0])
    visited = 0
    while queue:
        node_id = queue.popleft()
        visited += 1
        for next_node_id in graph[node_id]:
            indegree[next_node_id] -= 1
            if indegree[next_node_id] == 0:
                queue.append(next_node_id)
    return visited != len(node_ids)
