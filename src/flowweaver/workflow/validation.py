from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pydantic import ValidationError

from flowweaver.nodes.registry import NodeDefinitionSpec, NodeRegistry
from flowweaver.protocols.base import StrictModel
from flowweaver.workflow.definition import (
    UNAVAILABLE_FAILURE_POLICY_MODES,
    ControlProtocolMode,
    WorkflowDefinitionModel,
    failure_policy_unavailable_message,
)


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
    if model.failure_policy.mode in UNAVAILABLE_FAILURE_POLICY_MODES:
        errors.append(
            WorkflowValidationIssue(
                code="UNAVAILABLE_FAILURE_POLICY",
                path="failure_policy.mode",
                message=failure_policy_unavailable_message(
                    model.failure_policy.mode
                ),
            )
        )

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

    _validate_control_protocol(
        model,
        node_id_set=node_id_set,
        errors=errors,
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


def _validate_control_protocol(
    model: WorkflowDefinitionModel,
    *,
    node_id_set: set[str],
    errors: list[WorkflowValidationIssue],
) -> None:
    protocol = model.control_protocol
    if protocol is None:
        return
    if protocol.mode == ControlProtocolMode.ENABLED:
        errors.append(
            WorkflowValidationIssue(
                code="CONTROL_PROTOCOL_EXECUTION_UNAVAILABLE",
                path="control_protocol.mode",
                message=(
                    "Real control protocol execution is not available yet; "
                    "use preview mode until the scheduler is upgraded"
                ),
            )
        )

    loop_ids: set[str] = set()
    node_to_loop: dict[str, str] = {}
    for index, region in enumerate(protocol.loop_regions):
        path = f"control_protocol.loop_regions[{index}]"
        loop_id = region.loop_id.strip()
        if not loop_id:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_ID_REQUIRED",
                    path=f"{path}.loop_id",
                    message="Loop region loop_id is required",
                )
            )
        elif loop_id in loop_ids:
            errors.append(
                WorkflowValidationIssue(
                    code="DUPLICATE_LOOP_REGION_ID",
                    path=f"{path}.loop_id",
                    message=f"Loop region ID must be unique: {loop_id}",
                )
            )
        else:
            loop_ids.add(loop_id)

        if region.enabled:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_EXECUTION_UNAVAILABLE",
                    path=f"{path}.enabled",
                    message=(
                        "Real loop execution is not available yet; "
                        "keep loop regions disabled for preview metadata"
                    ),
                )
            )
        _validate_loop_node_ref(
            region.start_node_id,
            node_id_set=node_id_set,
            path=f"{path}.start_node_id",
            code="UNKNOWN_LOOP_START_NODE",
            role="start",
            errors=errors,
        )
        _validate_loop_node_ref(
            region.judge_node_id,
            node_id_set=node_id_set,
            path=f"{path}.judge_node_id",
            code="UNKNOWN_LOOP_JUDGE_NODE",
            role="judge",
            errors=errors,
        )
        if region.start_node_id == region.judge_node_id:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_INVALID_BOUNDARY",
                    path=path,
                    message="Loop start node and judge node must be different",
                )
            )
        if not region.body_node_ids:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_BODY_EMPTY",
                    path=f"{path}.body_node_ids",
                    message="Loop region body_node_ids must not be empty",
                )
            )
        body_ids = set(region.body_node_ids)
        if len(body_ids) != len(region.body_node_ids):
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_BODY_DUPLICATE_NODE",
                    path=f"{path}.body_node_ids",
                    message="Loop region body_node_ids must be unique",
                )
            )
        for body_index, body_node_id in enumerate(region.body_node_ids):
            _validate_loop_node_ref(
                body_node_id,
                node_id_set=node_id_set,
                path=f"{path}.body_node_ids[{body_index}]",
                code="UNKNOWN_LOOP_BODY_NODE",
                role="body",
                errors=errors,
            )
        boundary_nodes = {region.start_node_id, region.judge_node_id}
        boundary_in_body = sorted(body_ids & boundary_nodes)
        if boundary_in_body:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_BODY_CONTAINS_BOUNDARY",
                    path=f"{path}.body_node_ids",
                    message=(
                        "Loop region body cannot contain start or judge nodes: "
                        + ", ".join(boundary_in_body)
                    ),
                )
            )
        if region.end_node_id is not None:
            end_node_id = region.end_node_id.strip()
            if not end_node_id:
                errors.append(
                    WorkflowValidationIssue(
                        code="LOOP_REGION_END_NODE_REQUIRED",
                        path=f"{path}.end_node_id",
                        message="Loop region end_node_id must not be blank",
                    )
                )
            else:
                _validate_loop_node_ref(
                    end_node_id,
                    node_id_set=node_id_set,
                    path=f"{path}.end_node_id",
                    code="UNKNOWN_LOOP_END_NODE",
                    role="end",
                    errors=errors,
                )
        for branch_key, branch_name in (
            ("continue_branch", region.continue_branch),
            ("end_branch", region.end_branch),
        ):
            if not branch_name.strip():
                errors.append(
                    WorkflowValidationIssue(
                        code="LOOP_REGION_BRANCH_REQUIRED",
                        path=f"{path}.{branch_key}",
                        message=f"Loop region {branch_key} must not be blank",
                    )
                )

        membership_nodes = (
            [region.start_node_id, region.judge_node_id]
            + region.body_node_ids
            + ([region.end_node_id] if region.end_node_id else [])
        )
        for node_id in membership_nodes:
            if node_id not in node_id_set:
                continue
            existing_loop_id = node_to_loop.get(node_id)
            if existing_loop_id is not None and existing_loop_id != loop_id:
                errors.append(
                    WorkflowValidationIssue(
                        code="NESTED_LOOP_REGION_UNAVAILABLE",
                        path=path,
                        message=(
                            "Loop regions cannot overlap in the first real loop "
                            f"phase: node {node_id} is already in {existing_loop_id}"
                        ),
                    )
                )
            elif loop_id:
                node_to_loop[node_id] = loop_id


def _validate_loop_node_ref(
    node_id: str,
    *,
    node_id_set: set[str],
    path: str,
    code: str,
    role: str,
    errors: list[WorkflowValidationIssue],
) -> None:
    if not node_id.strip():
        errors.append(
            WorkflowValidationIssue(
                code=code,
                path=path,
                message=f"Loop {role} node ID is required",
            )
        )
    elif node_id not in node_id_set:
        errors.append(
            WorkflowValidationIssue(
                code=code,
                path=path,
                message=f"Loop {role} node does not exist: {node_id}",
            )
        )


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
