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
