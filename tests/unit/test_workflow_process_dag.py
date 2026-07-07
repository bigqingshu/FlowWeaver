from __future__ import annotations

import pytest
from pydantic import ValidationError

from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag import build_workflow_dag


def test_build_workflow_dag_calculates_ready_and_topological_order() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "transform",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [
                {
                    "connection_id": "c1",
                    "source_node_id": "source",
                    "source_port": "out",
                    "target_node_id": "transform",
                    "target_port": "input",
                }
            ],
        }
    )

    dag = build_workflow_dag(definition)

    assert dag.ready_node_ids == ("source",)
    assert dag.topological_order == ("source", "transform")
    assert dag.nodes[1].upstream_node_ids == ("source",)


def test_build_workflow_dag_rejects_cycle() -> None:
    definition = WorkflowDefinitionModel.model_validate(
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
                    "connection_id": "ab",
                    "source_node_id": "a",
                    "source_port": "out",
                    "target_node_id": "b",
                    "target_port": "in",
                },
                {
                    "connection_id": "ba",
                    "source_node_id": "b",
                    "source_port": "out",
                    "target_node_id": "a",
                    "target_port": "in",
                },
            ],
        }
    )

    with pytest.raises(ValueError, match="cycle"):
        build_workflow_dag(definition)


def test_workflow_definition_accepts_missing_runtime_options() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [],
            "connections": [],
        }
    )

    assert definition.runtime_options is None
    assert definition.model_dump(mode="json")["runtime_options"] is None


def test_workflow_definition_parses_runtime_options() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "version": "1.0",
                "workflow": {
                    "profile": "normal",
                    "strict_validation": True,
                    "telemetry": {
                        "log_level": "INFO",
                        "event_level": "progress",
                        "event_rate_limit_per_second": 0,
                        "progress_enabled": True,
                        "progress_interval_seconds": 0,
                    },
                    "diagnostics": {
                        "capture_error_context": True,
                        "include_metrics": True,
                        "payload_byte_limit": 0,
                        "ttl_seconds": 0,
                        "redact_columns": ["password"],
                        "mask_policy": "partial",
                    },
                },
                "node_overrides": {
                    "source": {
                        "telemetry": {
                            "log_level": "DEBUG",
                            "event_level": "verbose",
                        },
                        "diagnostics": {
                            "include_metrics": False,
                        },
                    },
                },
            },
        }
    )

    assert definition.runtime_options is not None
    assert definition.runtime_options.workflow.profile == "normal"
    assert definition.runtime_options.workflow.telemetry.progress_enabled is True
    assert (
        definition.runtime_options.node_overrides["source"].telemetry is not None
    )
    assert (
        definition.runtime_options.node_overrides["source"].telemetry.log_level
        == "DEBUG"
    )

    dag = build_workflow_dag(definition)

    assert dag.ready_node_ids == ("source",)
    dumped = definition.model_dump(mode="json")
    assert dumped["runtime_options"]["node_overrides"]["source"]["telemetry"][
        "log_level"
    ] == "DEBUG"


def test_workflow_definition_rejects_invalid_runtime_options() -> None:
    with pytest.raises(ValidationError, match="event_level"):
        WorkflowDefinitionModel.model_validate(
            {
                "schema_version": "1.0",
                "nodes": [],
                "connections": [],
                "runtime_options": {
                    "workflow": {
                        "telemetry": {
                            "event_level": "chatty",
                        },
                    },
                },
            }
        )
