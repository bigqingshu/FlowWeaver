from __future__ import annotations

from flowweaver.workflow.definition import (
    ControlProtocolMode,
    WorkflowDefinitionModel,
)
from flowweaver.workflow.validation_models import WorkflowValidationIssue

_EXPECTED_LOOP_BRANCHES = {
    "continue_branch": "continue_loop",
    "end_branch": "end_loop",
}


def validate_control_protocol(
    model: WorkflowDefinitionModel,
    *,
    node_id_set: set[str],
    errors: list[WorkflowValidationIssue],
) -> None:
    protocol = model.control_protocol
    if protocol is None:
        return
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

        if region.enabled and protocol.mode != ControlProtocolMode.ENABLED:
            errors.append(
                WorkflowValidationIssue(
                    code="LOOP_REGION_ENABLED_REQUIRES_CONTROL_PROTOCOL",
                    path=f"{path}.enabled",
                    message=(
                        "Loop region execution requires control_protocol.mode=enabled"
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
        for branch_key, expected_branch in _EXPECTED_LOOP_BRANCHES.items():
            branch_name = getattr(region, branch_key)
            if not branch_name.strip():
                errors.append(
                    WorkflowValidationIssue(
                        code="LOOP_REGION_BRANCH_REQUIRED",
                        path=f"{path}.{branch_key}",
                        message=f"Loop region {branch_key} must not be blank",
                    )
                )
            elif branch_name != expected_branch:
                errors.append(
                    WorkflowValidationIssue(
                        code="LOOP_REGION_BRANCH_UNSUPPORTED",
                        path=f"{path}.{branch_key}",
                        message=(
                            f"Loop region {branch_key} must be "
                            f"{expected_branch} in control protocol 1.0"
                        ),
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
