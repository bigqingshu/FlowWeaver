from __future__ import annotations

from flowweaver.nodes.registry import NodeDefinitionSpec, NodePortSpec, NodeRegistry
from flowweaver.workflow.validation import validate_workflow_definition


def registry() -> NodeRegistry:
    node_registry = NodeRegistry()
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.source",
            node_version="1.0",
            display_name="Source",
            output_ports=(NodePortSpec("out"),),
        )
    )
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.transform",
            node_version="1.0",
            display_name="Transform",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
        )
    )
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.loop_start",
            node_version="1.0",
            display_name="Loop Start",
            output_ports=(NodePortSpec("status"),),
        )
    )
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.loop_judge",
            node_version="1.0",
            display_name="Loop Judge",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("status"),),
        )
    )
    return node_registry


def test_valid_dag_passes_validation() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "a",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "b",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "c1",
                    "source_node_id": "a",
                    "source_port": "out",
                    "target_node_id": "b",
                    "target_port": "in",
                }
            ],
        },
        registry(),
    )

    assert result.valid is True
    assert result.errors == []


def test_reserved_skip_dependents_policy_is_rejected() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [],
            "connections": [],
            "failure_policy": {"mode": "SKIP_DEPENDENTS"},
        },
        registry(),
    )

    assert result.valid is False
    assert [(error.code, error.path) for error in result.errors] == [
        ("UNAVAILABLE_FAILURE_POLICY", "failure_policy.mode")
    ]
    assert "reserved and not available yet" in result.errors[0].message


def test_cycle_is_rejected() -> None:
    node_registry = registry()
    node_registry.register(
        NodeDefinitionSpec(
            node_type="core.loop",
            node_version="1.0",
            display_name="Loop",
            input_ports=(NodePortSpec("in"),),
            output_ports=(NodePortSpec("out"),),
        )
    )

    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "a",
                    "node_type": "core.loop",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "b",
                    "node_type": "core.loop",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "c1",
                    "source_node_id": "a",
                    "source_port": "out",
                    "target_node_id": "b",
                    "target_port": "in",
                },
                {
                    "connection_id": "c2",
                    "source_node_id": "b",
                    "source_port": "out",
                    "target_node_id": "a",
                    "target_port": "in",
                },
            ],
        },
        node_registry,
    )

    assert result.valid is False
    assert {error.code for error in result.errors} == {"DAG_CYCLE_DETECTED"}


def test_unknown_node_and_missing_required_input_are_rejected() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "a",
                    "node_type": "missing.node",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "b",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
        },
        registry(),
    )

    assert result.valid is False
    assert {error.code for error in result.errors} == {
        "UNKNOWN_NODE_TYPE",
        "REQUIRED_INPUT_NOT_CONNECTED",
    }


def test_preview_loop_region_protocol_passes_validation() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "loop_start",
                    "node_type": "core.loop_start",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "body",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "loop_judge",
                    "node_type": "core.loop_judge",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "after_loop",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "start-to-body",
                    "source_node_id": "loop_start",
                    "source_port": "status",
                    "target_node_id": "body",
                    "target_port": "in",
                },
                {
                    "connection_id": "body-to-judge",
                    "source_node_id": "body",
                    "source_port": "out",
                    "target_node_id": "loop_judge",
                    "target_port": "in",
                },
                {
                    "connection_id": "judge-to-after",
                    "source_node_id": "loop_judge",
                    "source_port": "status",
                    "target_node_id": "after_loop",
                    "target_port": "in",
                },
            ],
            "control_protocol": {
                "version": "1.0",
                "mode": "preview",
                "loop_regions": [
                    {
                        "loop_id": "orders_loop",
                        "start_node_id": "loop_start",
                        "judge_node_id": "loop_judge",
                        "body_node_ids": ["body"],
                        "end_node_id": "after_loop",
                        "max_iterations": 10,
                    }
                ],
            },
        },
        registry(),
    )

    assert result.valid is True
    assert result.errors == []


def test_real_control_protocol_enable_is_rejected_until_scheduler_exists() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "loop_start",
                    "node_type": "core.loop_start",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "body",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "loop_judge",
                    "node_type": "core.loop_judge",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "start-to-body",
                    "source_node_id": "loop_start",
                    "source_port": "status",
                    "target_node_id": "body",
                    "target_port": "in",
                },
                {
                    "connection_id": "body-to-judge",
                    "source_node_id": "body",
                    "source_port": "out",
                    "target_node_id": "loop_judge",
                    "target_port": "in",
                },
            ],
            "control_protocol": {
                "mode": "enabled",
                "loop_regions": [
                    {
                        "loop_id": "orders_loop",
                        "start_node_id": "loop_start",
                        "judge_node_id": "loop_judge",
                        "body_node_ids": ["body"],
                        "enabled": True,
                    }
                ],
            },
        },
        registry(),
    )

    assert result.valid is False
    assert {
        (error.code, error.path)
        for error in result.errors
    } >= {
        ("CONTROL_PROTOCOL_EXECUTION_UNAVAILABLE", "control_protocol.mode"),
        (
            "LOOP_REGION_EXECUTION_UNAVAILABLE",
            "control_protocol.loop_regions[0].enabled",
        ),
    }


def test_invalid_loop_region_protocol_is_rejected() -> None:
    result = validate_workflow_definition(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "loop_start",
                    "node_type": "core.loop_start",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "body",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "loop_judge",
                    "node_type": "core.loop_judge",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "start-to-body",
                    "source_node_id": "loop_start",
                    "source_port": "status",
                    "target_node_id": "body",
                    "target_port": "in",
                },
                {
                    "connection_id": "body-to-judge",
                    "source_node_id": "body",
                    "source_port": "out",
                    "target_node_id": "loop_judge",
                    "target_port": "in",
                },
            ],
            "control_protocol": {
                "loop_regions": [
                    {
                        "loop_id": "orders_loop",
                        "start_node_id": "loop_start",
                        "judge_node_id": "loop_judge",
                        "body_node_ids": ["body"],
                    },
                    {
                        "loop_id": "orders_loop",
                        "start_node_id": "loop_start",
                        "judge_node_id": "missing_judge",
                        "body_node_ids": ["loop_start", "body", "body"],
                        "continue_branch": "",
                    },
                    {
                        "loop_id": "nested_loop",
                        "start_node_id": "loop_judge",
                        "judge_node_id": "loop_start",
                        "body_node_ids": ["body"],
                    },
                ],
            },
        },
        registry(),
    )

    assert result.valid is False
    assert {
        error.code
        for error in result.errors
    } >= {
        "DUPLICATE_LOOP_REGION_ID",
        "UNKNOWN_LOOP_JUDGE_NODE",
        "LOOP_REGION_BODY_DUPLICATE_NODE",
        "LOOP_REGION_BODY_CONTAINS_BOUNDARY",
        "LOOP_REGION_BRANCH_REQUIRED",
        "NESTED_LOOP_REGION_UNAVAILABLE",
    }
