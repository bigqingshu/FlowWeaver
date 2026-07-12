from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from pydantic import Field, field_validator

from flowweaver.protocols.base import StrictModel

WorkflowProcessExecutionMode = Literal["immediate", "threaded"]

DEFAULT_WORKFLOW_PROCESS_EXECUTION_MODE: WorkflowProcessExecutionMode = "immediate"
DEFAULT_WORKFLOW_PROCESS_MAX_CONCURRENT_NODE_TASKS = 1
DEFAULT_MEMORY_TABLE_SOFT_ROW_LIMIT = 100_000
ALLOWED_WORKFLOW_PROCESS_EXECUTION_MODES = {"immediate", "threaded"}
ALLOWED_WORKFLOW_PROCESS_MAX_CONCURRENT_NODE_TASKS = {1, 2}


@dataclass(frozen=True)
class MemoryTableLimits:
    soft_row_limit: int = DEFAULT_MEMORY_TABLE_SOFT_ROW_LIMIT

    def __post_init__(self) -> None:
        if isinstance(self.soft_row_limit, bool) or self.soft_row_limit < 0:
            raise ValueError("memory table soft row limit must be non-negative")


def resolve_workflow_process_execution_mode(
    value: object | None,
) -> WorkflowProcessExecutionMode:
    if value is None:
        return DEFAULT_WORKFLOW_PROCESS_EXECUTION_MODE
    if value not in ALLOWED_WORKFLOW_PROCESS_EXECUTION_MODES:
        raise ValueError(
            "workflow_process_execution_mode must be 'immediate' or 'threaded'"
        )
    return cast(WorkflowProcessExecutionMode, value)


def resolve_workflow_process_max_concurrent_node_tasks(
    value: object | None,
) -> int:
    if value is None:
        return DEFAULT_WORKFLOW_PROCESS_MAX_CONCURRENT_NODE_TASKS
    if isinstance(value, bool):
        raise ValueError("workflow_process_max_concurrent_node_tasks must be 1 or 2")
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError as exc:
            raise ValueError(
                "workflow_process_max_concurrent_node_tasks must be 1 or 2"
            ) from exc
    if value not in ALLOWED_WORKFLOW_PROCESS_MAX_CONCURRENT_NODE_TASKS:
        raise ValueError("workflow_process_max_concurrent_node_tasks must be 1 or 2")
    return int(value)


class EngineConfig(StrictModel):
    data_dir: Path = Path("runtime")
    metadata_db_path: Path | None = None
    runtime_dir: Path | None = None
    log_dir: Path | None = None
    temp_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    local_api_token: str | None = None
    enforce_single_instance: bool = True
    max_concurrent_workflows: int = 4
    max_executors_per_workflow: int = 2
    max_ipc_message_bytes: int = 1024 * 1024
    max_runtime_db_bytes: int = 1024 * 1024 * 1024
    max_log_file_bytes: int = 10 * 1024 * 1024
    memory_table_soft_row_limit: int = Field(
        default=DEFAULT_MEMORY_TABLE_SOFT_ROW_LIMIT,
        ge=0,
        strict=True,
    )
    staging_ttl_seconds: int = 3600
    orphan_cleanup_interval: int = 300
    workflow_process_heartbeat_interval_seconds: int = 2
    workflow_process_lost_threshold_seconds: int = 10
    workflow_process_start_timeout_seconds: int = 10
    workflow_process_cancel_grace_seconds: int = 5
    workflow_process_execution_mode: WorkflowProcessExecutionMode = (
        DEFAULT_WORKFLOW_PROCESS_EXECUTION_MODE
    )
    workflow_process_max_concurrent_node_tasks: int = (
        DEFAULT_WORKFLOW_PROCESS_MAX_CONCURRENT_NODE_TASKS
    )
    supervisor_maintenance_interval_seconds: float = 1.0
    shared_publication_cleanup_enabled: bool = False
    shared_publication_cleanup_interval_seconds: float = Field(
        default=60.0,
        ge=0.05,
        le=86_400.0,
    )
    shared_publication_cleanup_publication_batch_size: int = Field(
        default=20,
        ge=1,
        le=1000,
    )
    shared_publication_cleanup_table_ref_batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
    )
    shared_publication_cleanup_cycle_budget_seconds: float = Field(
        default=5.0,
        ge=0.05,
        le=300.0,
    )
    shared_publication_releasing_stale_seconds: int = Field(
        default=300,
        ge=1,
        le=604_800,
    )
    allowed_origins: set[str] = Field(default_factory=lambda: {"http://127.0.0.1"})

    @field_validator("workflow_process_execution_mode", mode="before")
    @classmethod
    def _validate_workflow_process_execution_mode(cls, value: object) -> object:
        return resolve_workflow_process_execution_mode(value)

    @field_validator("workflow_process_max_concurrent_node_tasks", mode="before")
    @classmethod
    def _validate_workflow_process_max_concurrent_node_tasks(
        cls,
        value: object,
    ) -> int:
        return resolve_workflow_process_max_concurrent_node_tasks(value)

    def resolved_metadata_db_path(self) -> Path:
        return self.metadata_db_path or self.data_dir / "metadata" / "flowweaver.db"

    def resolved_runtime_dir(self) -> Path:
        return self.runtime_dir or self.data_dir / "workflow_runs"

    def resolved_log_dir(self) -> Path:
        return self.log_dir or self.data_dir / "logs"

    def resolved_temp_dir(self) -> Path:
        return self.temp_dir or self.data_dir / "temp"

    def memory_table_limits(self) -> MemoryTableLimits:
        return MemoryTableLimits(soft_row_limit=self.memory_table_soft_row_limit)
