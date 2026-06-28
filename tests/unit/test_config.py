from __future__ import annotations

import pytest
from pydantic import ValidationError

from flowweaver.common.config import (
    EngineConfig,
    resolve_workflow_process_execution_mode,
    resolve_workflow_process_max_concurrent_node_tasks,
)


def test_engine_config_defaults_to_immediate_single_task_execution() -> None:
    config = EngineConfig()

    assert config.workflow_process_execution_mode == "immediate"
    assert config.workflow_process_max_concurrent_node_tasks == 1
    assert resolve_workflow_process_execution_mode(None) == "immediate"
    assert resolve_workflow_process_max_concurrent_node_tasks(None) == 1


def test_engine_config_accepts_threaded_mode_with_two_tasks() -> None:
    config = EngineConfig(
        workflow_process_execution_mode="threaded",
        workflow_process_max_concurrent_node_tasks=2,
    )

    assert config.workflow_process_execution_mode == "threaded"
    assert config.workflow_process_max_concurrent_node_tasks == 2
    assert resolve_workflow_process_execution_mode("threaded") == "threaded"
    assert resolve_workflow_process_max_concurrent_node_tasks("2") == 2


@pytest.mark.parametrize("execution_mode", ["process", "", 1])
def test_engine_config_rejects_explicit_invalid_execution_mode(
    execution_mode: object,
) -> None:
    with pytest.raises(
        ValidationError,
        match="workflow_process_execution_mode must be 'immediate' or 'threaded'",
    ):
        EngineConfig(workflow_process_execution_mode=execution_mode)


@pytest.mark.parametrize("max_concurrent_node_tasks", [0, 3, True, "many"])
def test_engine_config_rejects_explicit_invalid_max_concurrent_node_tasks(
    max_concurrent_node_tasks: object,
) -> None:
    with pytest.raises(
        ValidationError,
        match="workflow_process_max_concurrent_node_tasks must be 1 or 2",
    ):
        EngineConfig(
            workflow_process_max_concurrent_node_tasks=max_concurrent_node_tasks
        )
