from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.node_executor import (
    DELAY_TEST_NODE_TYPE,
    LocalNodeExecutorIpcClient,
)
from flowweaver.node_executor.runtime_logger import NodeTaskLogger
from flowweaver.protocols.enums import IPCMessageType, NodeResultStatus
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.workflow_process.main import run_workflow_process


@dataclass(frozen=True)
class WorkflowFeedbackRunResult:
    ipc_messages: tuple[IPCEnvelope, ...]
    runtime_event_types: tuple[str, ...]
    runtime_event_payload_bytes: int
    workflow_status: str
    node_status: str
    output_refs: tuple[str, ...]


class CountingLocalNodeExecutorIpcClient(LocalNodeExecutorIpcClient):
    def __init__(
        self,
        *,
        executor_id: str,
        executor_factory=None,
    ) -> None:
        super().__init__(
            executor_id=executor_id,
            executor_factory=executor_factory,
        )
        self.ipc_messages: list[IPCEnvelope] = []

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        if handler is None:
            super().set_event_handler(None)
            return

        def count_and_forward(task: NodeTaskModel, envelope: IPCEnvelope) -> None:
            self.ipc_messages.append(envelope)
            handler(task, envelope)

        super().set_event_handler(count_and_forward)


class RuntimeLoggingSuccessExecutor:
    def __init__(self, executor_id: str) -> None:
        self.executor_id = executor_id
        self.runtime_logger: NodeTaskLogger | None = None

    def set_runtime_logger(self, logger: NodeTaskLogger | None) -> None:
        self.runtime_logger = logger

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        assert self.runtime_logger is not None
        self.runtime_logger.debug("node debug", context={"sequence": 1})
        self.runtime_logger.info("node info", context={"sequence": 2})
        self.runtime_logger.warn("node warning", context={"sequence": 3})
        self.runtime_logger.error("node error", context={"sequence": 4})
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=["business-output"],
            summary={"business_rows": 3},
            started_at=now,
            finished_at=now,
        )


@pytest.mark.parametrize(
    ("run_mode", "trigger_source"),
    [
        ("full", "manual"),
        ("preview_to_node", "manual"),
        ("full", "background_manual"),
    ],
)
def test_normal_and_background_fast_reduce_feedback_for_all_run_entries(
    tmp_path: Path,
    run_mode: str,
    trigger_source: str,
) -> None:
    store = make_store(tmp_path)
    scenario = f"{run_mode}-{trigger_source}".replace("_", "-")

    normal = run_delay_workflow(
        store,
        scenario=f"{scenario}-normal",
        run_mode=run_mode,
        trigger_source=trigger_source,
        background_fast=False,
    )
    background_fast = run_delay_workflow(
        store,
        scenario=f"{scenario}-background-fast",
        run_mode=run_mode,
        trigger_source=trigger_source,
        background_fast=True,
    )

    normal_progress_ipc = sum(
        envelope.message_type == IPCMessageType.NODE_TASK_PROGRESS
        for envelope in normal.ipc_messages
    )
    background_progress_ipc = sum(
        envelope.message_type == IPCMessageType.NODE_TASK_PROGRESS
        for envelope in background_fast.ipc_messages
    )
    assert normal_progress_ipc > 0
    assert background_progress_ipc == 0
    assert len(background_fast.ipc_messages) < len(normal.ipc_messages)

    normal_progress_events = normal.runtime_event_types.count("NODE_PROGRESS")
    background_progress_events = background_fast.runtime_event_types.count(
        "NODE_PROGRESS"
    )
    assert normal_progress_events > 0
    assert background_progress_events == 0
    assert len(background_fast.runtime_event_types) < len(normal.runtime_event_types)
    assert (
        background_fast.runtime_event_payload_bytes
        < normal.runtime_event_payload_bytes
    )
    assert set(normal.runtime_event_types) - {"NODE_PROGRESS"} == set(
        background_fast.runtime_event_types
    )
    for critical_event_type in (
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ):
        assert normal.runtime_event_types.count(critical_event_type) == 1
        assert background_fast.runtime_event_types.count(critical_event_type) == 1

    assert normal.workflow_status == background_fast.workflow_status == "SUCCEEDED"
    assert normal.node_status == background_fast.node_status == "SUCCEEDED"
    assert normal.output_refs == background_fast.output_refs == ()


def test_node_sender_and_main_program_apply_run_scoped_log_levels(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)

    inherited_warn = run_logging_workflow(
        store,
        scenario="workflow-warn",
        node_debug_override=False,
    )
    node_debug = run_logging_workflow(
        store,
        scenario="node-debug",
        node_debug_override=True,
    )

    assert node_log_levels(inherited_warn.ipc_messages) == ["WARN", "ERROR"]
    assert node_log_levels(node_debug.ipc_messages) == [
        "DEBUG",
        "INFO",
        "WARN",
        "ERROR",
    ]
    assert runtime_node_log_levels(store, "run-workflow-warn") == ["WARN", "ERROR"]
    assert runtime_node_log_levels(store, "run-node-debug") == [
        "DEBUG",
        "INFO",
        "WARN",
        "ERROR",
    ]
    assert not runtime_event_types(store, "run-workflow-warn").count("WORKFLOW_LOG")
    assert not runtime_event_types(store, "run-node-debug").count("WORKFLOW_LOG")
    assert inherited_warn.workflow_status == node_debug.workflow_status == "SUCCEEDED"
    assert inherited_warn.node_status == node_debug.node_status == "SUCCEEDED"
    assert inherited_warn.output_refs == node_debug.output_refs == ("business-output",)


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")
    return RuntimeStore.from_sqlite_path(database_path)


def run_delay_workflow(
    store: RuntimeStore,
    *,
    scenario: str,
    run_mode: str,
    trigger_source: str,
    background_fast: bool,
) -> WorkflowFeedbackRunResult:
    definition = {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "test-node",
                "node_type": DELAY_TEST_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "duration_seconds": 0.04,
                    "heartbeat_interval_seconds": 0.005,
                    "progress_interval_seconds": 0.005,
                },
            }
        ],
        "connections": [],
    }
    if background_fast:
        definition["runtime_options"] = {
            "workflow": {"profile": "background_fast"}
        }
    workflow = store.create_workflow_definition(
        name=f"Runtime feedback {scenario}",
        definition=definition,
        workflow_id=f"workflow-{scenario}",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=f"run-{scenario}",
        run_mode=run_mode,
        trigger_source=trigger_source,
        target_node_instance_id=(
            "test-node" if run_mode == "preview_to_node" else None
        ),
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id=f"process-{scenario}",
    )
    assert process is not None
    executor = CountingLocalNodeExecutorIpcClient(
        executor_id=f"executor-{scenario}"
    )

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    return collect_result(store, run.workflow_run_id, executor.ipc_messages)


def run_logging_workflow(
    store: RuntimeStore,
    *,
    scenario: str,
    node_debug_override: bool,
) -> WorkflowFeedbackRunResult:
    runtime_options: dict[str, object] = {
        "workflow": {
            "telemetry": {
                "log_level": "WARN",
                "event_level": "verbose",
            }
        }
    }
    if node_debug_override:
        runtime_options["node_overrides"] = {
            "source": {"telemetry": {"log_level": "DEBUG"}}
        }
    workflow = store.create_workflow_definition(
        name=f"Runtime logging {scenario}",
        definition={
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                }
            ],
            "connections": [],
            "runtime_options": runtime_options,
        },
        workflow_id=f"workflow-{scenario}",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=f"run-{scenario}",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id=f"process-{scenario}",
    )
    assert process is not None
    executor_id = f"executor-{scenario}"
    executor = CountingLocalNodeExecutorIpcClient(
        executor_id=executor_id,
        executor_factory=lambda _task: RuntimeLoggingSuccessExecutor(executor_id),
    )

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    return collect_result(store, run.workflow_run_id, executor.ipc_messages)


def collect_result(
    store: RuntimeStore,
    workflow_run_id: str,
    ipc_messages: list[IPCEnvelope],
) -> WorkflowFeedbackRunResult:
    run = store.get_workflow_run(workflow_run_id)
    node_run = store.list_node_runs(workflow_run_id)[0]
    result = store.get_latest_succeeded_node_task_result_for_node_run(
        node_run.node_run_id
    )
    events = [
        event
        for event in store.list_runtime_events()
        if event.workflow_run_id == workflow_run_id
    ]
    assert run is not None
    assert result is not None, {
        "workflow_status": run.status,
        "node_status": node_run.status,
        "node_error": node_run.error,
        "event_types": [event.event_type for event in events],
    }
    return WorkflowFeedbackRunResult(
        ipc_messages=tuple(ipc_messages),
        runtime_event_types=tuple(event.event_type for event in events),
        runtime_event_payload_bytes=sum(
            len(
                json.dumps(
                    event.payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            for event in events
        ),
        workflow_status=run.status,
        node_status=node_run.status,
        output_refs=tuple(result.output_refs),
    )


def node_log_levels(ipc_messages: tuple[IPCEnvelope, ...]) -> list[str]:
    return [
        str(envelope.payload["level"])
        for envelope in ipc_messages
        if envelope.message_type == IPCMessageType.NODE_TASK_LOG
    ]


def runtime_node_log_levels(store: RuntimeStore, workflow_run_id: str) -> list[str]:
    return [
        str(event.payload["level"])
        for event in store.list_runtime_events()
        if event.workflow_run_id == workflow_run_id
        and event.event_type == "NODE_LOG"
    ]


def runtime_event_types(store: RuntimeStore, workflow_run_id: str) -> list[str]:
    return [
        event.event_type
        for event in store.list_runtime_events()
        if event.workflow_run_id == workflow_run_id
    ]
