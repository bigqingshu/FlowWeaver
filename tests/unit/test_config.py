from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from flowweaver.common.config import (
    DEFAULT_MEMORY_TABLE_SOFT_ROW_LIMIT,
    EngineConfig,
    MemoryTableLimits,
    resolve_workflow_process_execution_mode,
    resolve_workflow_process_max_concurrent_node_tasks,
)


def test_engine_config_defaults_to_immediate_single_task_execution() -> None:
    config = EngineConfig()

    assert config.workflow_process_execution_mode == "immediate"
    assert config.workflow_process_max_concurrent_node_tasks == 1
    assert resolve_workflow_process_execution_mode(None) == "immediate"
    assert resolve_workflow_process_max_concurrent_node_tasks(None) == 1
    assert config.shared_publication_cleanup_enabled is False
    assert config.shared_publication_cleanup_publication_batch_size == 20
    assert config.shared_publication_cleanup_table_ref_batch_size == 50
    assert (
        config.memory_table_soft_row_limit
        == DEFAULT_MEMORY_TABLE_SOFT_ROW_LIMIT
    )
    assert config.memory_table_limits() == MemoryTableLimits()
    assert config.resolved_plugin_dir() == Path("plugins")


def test_engine_config_accepts_threaded_mode_with_two_tasks() -> None:
    config = EngineConfig(
        workflow_process_execution_mode="threaded",
        workflow_process_max_concurrent_node_tasks=2,
    )

    assert config.workflow_process_execution_mode == "threaded"
    assert config.workflow_process_max_concurrent_node_tasks == 2
    assert resolve_workflow_process_execution_mode("threaded") == "threaded"
    assert resolve_workflow_process_max_concurrent_node_tasks("2") == 2


def test_engine_config_accepts_disabled_memory_table_soft_limit() -> None:
    config = EngineConfig(memory_table_soft_row_limit=0)

    assert config.memory_table_limits() == MemoryTableLimits(soft_row_limit=0)


@pytest.mark.parametrize("soft_row_limit", [-1, True])
def test_engine_config_rejects_invalid_memory_table_soft_limit(
    soft_row_limit: object,
) -> None:
    with pytest.raises(ValidationError):
        EngineConfig(memory_table_soft_row_limit=soft_row_limit)


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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("shared_publication_cleanup_interval_seconds", 0),
        ("shared_publication_cleanup_publication_batch_size", 0),
        ("shared_publication_cleanup_table_ref_batch_size", 1001),
        ("shared_publication_cleanup_cycle_budget_seconds", 0),
        ("shared_publication_releasing_stale_seconds", 0),
    ],
)
def test_engine_config_rejects_invalid_shared_cleanup_limits(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        EngineConfig.model_validate({field_name: value})
