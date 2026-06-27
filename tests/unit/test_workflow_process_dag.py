from __future__ import annotations

import pytest

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
