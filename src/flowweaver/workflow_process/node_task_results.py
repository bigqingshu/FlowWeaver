from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NodeTaskApplyStatus(str, Enum):
    APPLIED = "APPLIED"
    ALREADY_APPLIED = "ALREADY_APPLIED"
    REJECTED_INVALID_TASK = "REJECTED_INVALID_TASK"
    REJECTED_STALE_ATTEMPT = "REJECTED_STALE_ATTEMPT"
    REJECTED_STALE_GENERATION = "REJECTED_STALE_GENERATION"
    REJECTED_EXECUTOR_MISMATCH = "REJECTED_EXECUTOR_MISMATCH"
    REJECTED_NODE_TERMINAL = "REJECTED_NODE_TERMINAL"


class NodeTaskTimeoutStatus(str, Enum):
    TIMED_OUT = "TIMED_OUT"
    NOT_TIMED_OUT = "NOT_TIMED_OUT"
    REJECTED_INVALID_TASK = "REJECTED_INVALID_TASK"
    REJECTED_WORKFLOW_NOT_RUNNING = "REJECTED_WORKFLOW_NOT_RUNNING"
    REJECTED_NODE_NOT_RUNNING = "REJECTED_NODE_NOT_RUNNING"


@dataclass(frozen=True)
class NodeTaskApplyResult:
    status: NodeTaskApplyStatus
    node_run_id: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class NodeTaskTimeoutResult:
    status: NodeTaskTimeoutStatus
    node_run_id: str | None = None
    detail: str | None = None
