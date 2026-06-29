from __future__ import annotations

import pytest

from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.builtin_table import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.nodes.permissions import resolve_builtin_node_permissions
from flowweaver.protocols.enums import PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel


def make_task(
    *,
    node_type: str,
    node_instance_id: str = "node",
    input_refs: list[str] | None = None,
    config: dict | None = None,
) -> NodeTaskModel:
    return NodeTaskModel(
        workflow_run_id="run-1",
        workflow_process_id="process-1",
        process_generation=1,
        node_run_id=f"{node_instance_id}-run",
        node_instance_id=node_instance_id,
        node_type=node_type,
        node_version="1.0",
        attempt=1,
        input_refs=input_refs or [],
        config=config or {},
        timeout_seconds=60,
    )


def test_generate_table_node_declares_output_publish_permission() -> None:
    request = resolve_builtin_node_permissions(
        make_task(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_instance_id="generate",
            config={"rows": 3, "columns": ["row_id", "amount"]},
        )
    )

    assert request.workflow_run_id == "run-1"
    assert request.node_run_id == "generate-run"
    assert [(scope.action, scope.resource_type) for scope in request.scopes] == [
        (PermissionAction.PUBLISH, "NODE_OUTPUT")
    ]
    assert request.scopes[0].resource_id == "run-1:generate:output"
    assert request.scopes[0].constraints == {
        "columns": ["row_id", "amount"],
        "rows": 3,
    }


def test_filter_rows_node_declares_read_fields_and_output_publish() -> None:
    request = resolve_builtin_node_permissions(
        make_task(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_instance_id="filter",
            input_refs=["table-orders"],
            config={"field": "amount", "operator": "GT", "value": 2},
        )
    )

    assert [scope.action for scope in request.scopes] == [
        PermissionAction.READ_TABLE,
        PermissionAction.READ_FIELDS,
        PermissionAction.PUBLISH,
    ]
    assert request.scopes[0].resource_id == "table-orders"
    assert request.scopes[1].resource_id == "table-orders"
    assert request.scopes[1].fields == ["amount"]
    assert request.scopes[1].constraints == {"operator": "GT", "value": 2}
    assert request.scopes[2].resource_id == "run-1:filter:output"


def test_publish_shared_tables_node_declares_input_reads_and_shared_publish() -> None:
    request = resolve_builtin_node_permissions(
        make_task(
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_instance_id="publish",
            input_refs=["table-orders", "table-customers"],
            config={
                "share_name": "daily_report",
                "export_names": ["orders", "customers"],
            },
        )
    )

    assert [scope.action for scope in request.scopes] == [
        PermissionAction.READ_TABLE,
        PermissionAction.READ_TABLE,
        PermissionAction.PUBLISH,
    ]
    assert [scope.resource_id for scope in request.scopes[:2]] == [
        "table-orders",
        "table-customers",
    ]
    assert request.scopes[2].resource_type == "SHARED_PUBLICATION"
    assert request.scopes[2].resource_id == "daily_report"
    assert request.scopes[2].constraints == {
        "export_names": ["orders", "customers"],
        "input_refs": ["table-orders", "table-customers"],
    }


def test_read_shared_tables_node_declares_shared_read() -> None:
    request = resolve_builtin_node_permissions(
        make_task(
            node_type=READ_SHARED_TABLES_NODE_TYPE,
            node_instance_id="read",
            config={
                "share_name": "daily_report",
                "version_policy": "EXACT_VERSION",
                "exact_version": 1,
                "selected_members": ["orders", "customers"],
            },
        )
    )

    assert len(request.scopes) == 1
    scope = request.scopes[0]
    assert scope.action == PermissionAction.READ_SHARED
    assert scope.resource_type == "SHARED_PUBLICATION"
    assert scope.resource_id == "daily_report"
    assert scope.constraints == {
        "version_policy": "EXACT_VERSION",
        "exact_version": 1,
        "selected_members": ["orders", "customers"],
    }


def test_permission_resolution_rejects_invalid_builtin_node_config() -> None:
    with pytest.raises(ValueError, match="requires exactly one input_ref"):
        resolve_builtin_node_permissions(
            make_task(
                node_type=FILTER_ROWS_NODE_TYPE,
                input_refs=[],
                config={"field": "amount"},
            )
        )

    with pytest.raises(ValueError, match="export_names must match input_refs"):
        resolve_builtin_node_permissions(
            make_task(
                node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
                input_refs=["table-orders"],
                config={
                    "share_name": "daily_report",
                    "export_names": ["orders", "customers"],
                },
            )
        )
