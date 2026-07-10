from __future__ import annotations

import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from threading import Event, Thread

import pytest
from alembic import command
from alembic.config import Config

import flowweaver.workflow_process.main as workflow_process_main
from flowweaver.common.time import utc_now
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_event_sink import DatabaseEventSink, IPCEventSink
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.node_executor import (
    DELAY_TEST_NODE_TYPE,
    FAULT_MODE_INFINITE_LOOP,
    FAULT_MODE_PROCESS_EXIT,
    FAULT_MODE_RAISE_EXCEPTION,
    FAULT_TEST_NODE_TYPE,
    BuiltinSharedTableNodeExecutor,
    BuiltinTableNodeExecutor,
    FakeNodeExecutor,
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
)
from flowweaver.protocols.enums import (
    IPCMessageType,
    LifecycleStatus,
    NodeResultStatus,
    NodeRunStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import initialize_node_runs
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.executor_pool import (
    DispatchedNodeTask,
    ExecutorTaskCompletion,
    ThreadedNodeTaskExecutionPool,
)
from flowweaver.workflow_process.main import run_workflow_process
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.ready_queue import collect_ready_node_candidates


class InjectedFailingExecutor:
    executor_id = "injected-failing-executor"

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.FAILED,
            error={"message": "injected failure"},
            started_at=now,
            finished_at=now,
        )


class NodeOutcomeExecutor:
    executor_id = "node-outcome-executor"

    def __init__(self, *, failed_nodes: set[str] | None = None) -> None:
        self._failed_nodes = failed_nodes or set()
        self.executed_nodes: list[str] = []

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.executed_nodes.append(task.node_instance_id)
        now = utc_now()
        failed = task.node_instance_id in self._failed_nodes
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.FAILED if failed else NodeResultStatus.SUCCEEDED,
            output_refs=[] if failed else [f"{task.node_instance_id}-output"],
            error=(
                {"message": f"{task.node_instance_id} injected failure"}
                if failed
                else None
            ),
            started_at=now,
            finished_at=now,
        )


class InjectedRaisingExecutor:
    executor_id = "injected-raising-executor"

    def execute(self, _task: NodeTaskModel) -> NodeTaskResultModel:
        raise RuntimeError("injected threaded failure")


class InjectedReportingExecutor:
    executor_id = "injected-reporting-executor"

    def __init__(self, *, output_refs: list[str] | None = None) -> None:
        self._event_handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None = None
        self._output_refs = list(output_refs or [])

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if self._event_handler is not None:
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "executor_id": self.executor_id,
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                    },
                ),
            )
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_PROGRESS,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "progress": 0.5,
                        "current_stage": "halfway",
                        "metrics": {"rows": 10},
                    },
                ),
            )
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=list(self._output_refs),
            started_at=now,
            finished_at=now,
        )


class BlockingReportingExecutor:
    executor_id = "blocking-reporting-executor"

    def __init__(self, *, progress_reported: Event, finish_task: Event) -> None:
        self._event_handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None = None
        self._progress_reported = progress_reported
        self._finish_task = finish_task

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if self._event_handler is not None:
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "executor_id": self.executor_id,
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                    },
                ),
            )
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_PROGRESS,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "progress": 0.25,
                        "current_stage": "streaming",
                        "metrics": {"ticks": 1},
                    },
                ),
            )
        self._progress_reported.set()
        completed = self._finish_task.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=(
                NodeResultStatus.SUCCEEDED
                if completed
                else NodeResultStatus.FAILED
            ),
            error=None if completed else {"message": "test did not release task"},
            started_at=now,
            finished_at=now,
        )

    def close(self) -> None:
        self._finish_task.set()


class CloseableBlockingSuccessExecutor:
    executor_id = "closeable-blocking-success-executor"

    def __init__(self) -> None:
        self._event_handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None = None
        self.started = Event()
        self.closed = Event()
        self.cancel_requested = Event()
        self.cancelled_task_id: str | None = None
        self.cancel_reason: str | None = None

    def set_event_handler(
        self,
        handler: Callable[[NodeTaskModel, IPCEnvelope], None] | None,
    ) -> None:
        self._event_handler = handler

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        if self._event_handler is not None:
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_HEARTBEAT,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "executor_id": self.executor_id,
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                    },
                ),
            )
            self._event_handler(
                task,
                IPCEnvelope(
                    message_type=IPCMessageType.NODE_TASK_PROGRESS,
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    payload={
                        "progress": 0.1,
                        "current_stage": "blocking",
                        "metrics": {"ticks": 1},
                    },
                ),
            )
        self.started.set()
        self.closed.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            started_at=now,
            finished_at=now,
        )

    def close(self) -> None:
        self.closed.set()

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        self.cancelled_task_id = task.task_id
        self.cancel_reason = reason
        self.cancel_requested.set()
        return True


class CooperativeCancelExecutor:
    executor_id = "cooperative-cancel-executor"

    def __init__(self) -> None:
        self.started = Event()
        self.closed = Event()
        self.cancel_requested = Event()
        self.cancelled_task_id: str | None = None

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.started.set()
        self.cancel_requested.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.CANCELLED,
            error={
                "message": "Node task cancelled cooperatively",
                "reason": "WORKFLOW_CANCEL_REQUESTED",
            },
            started_at=now,
            finished_at=now,
        )

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        self.cancelled_task_id = task.task_id
        self.cancel_requested.set()
        return True

    def close(self) -> None:
        self.closed.set()


class BlockingStagingExecutor:
    executor_id = "blocking-staging-executor"

    def __init__(
        self,
        *,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
    ) -> None:
        self._registry = registry
        self._table_provider = table_provider
        self.started = Event()
        self.closed = Event()
        self.staging_ref_ids: list[str] = []

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        staging_ref = self._table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name="partial_output",
            schema=[
                FieldSchemaModel(
                    field_id="row_id",
                    name="row_id",
                    data_type="INTEGER",
                    nullable=False,
                    ordinal=0,
                )
            ],
        )
        self._table_provider.insert_rows(staging_ref, [{"row_id": 1}])
        self._registry.register_staging(staging_ref)
        self.staging_ref_ids.append(staging_ref.table_ref_id)
        self.started.set()
        self.closed.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=list(self.staging_ref_ids),
            started_at=now,
            finished_at=now,
        )

    def close(self) -> None:
        self.closed.set()


class NodeAwareOutputExecutor:
    executor_id = "node-aware-output-executor"

    def __init__(self, output_refs_by_node: dict[str, list[str]]) -> None:
        self._output_refs_by_node = output_refs_by_node
        self.seen_input_refs_by_node: dict[str, list[str]] = {}

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.seen_input_refs_by_node[task.node_instance_id] = list(task.input_refs)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=list(self._output_refs_by_node.get(task.node_instance_id, [])),
            started_at=now,
            finished_at=now,
        )


class RecordingSuccessExecutor:
    executor_id = "recording-success-executor"

    def __init__(self) -> None:
        self.executed_nodes: list[str] = []

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.executed_nodes.append(task.node_instance_id)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[f"{task.node_instance_id}-output"],
            started_at=now,
            finished_at=now,
        )


class ReleasableBlockingExecutor:
    executor_id = "releasable-blocking-executor"

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.closed = Event()

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.started.set()
        released = self.release.wait(timeout=1)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=(
                NodeResultStatus.SUCCEEDED if released else NodeResultStatus.FAILED
            ),
            error=None if released else {"message": "test did not release task"},
            started_at=now,
            finished_at=now,
        )

    def close(self) -> None:
        self.closed.set()


class BlockingInputRefsExecutor:
    executor_id = "blocking-input-refs-executor"

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.closed = Event()
        self.seen_input_refs_by_node: dict[str, list[str]] = {}

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        self.seen_input_refs_by_node[task.node_instance_id] = list(task.input_refs)
        self.started.set()
        released = self.release.wait(timeout=5)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=(
                NodeResultStatus.SUCCEEDED if released else NodeResultStatus.FAILED
            ),
            output_refs=list(task.input_refs) if released else [],
            error=None if released else {"message": "test did not release task"},
            started_at=now,
            finished_at=now,
        )

    def close(self) -> None:
        self.closed.set()
        self.release.set()


class ReleasableMultiNodeExecutor:
    executor_id = "releasable-multi-node-executor"

    def __init__(self, *, failed_nodes: set[str] | None = None) -> None:
        self._failed_nodes = failed_nodes or set()
        self.started_by_node: dict[str, Event] = {}
        self.release_by_node: dict[str, Event] = {}
        self.executed_nodes: list[str] = []
        self.seen_input_refs_by_node: dict[str, list[str]] = {}

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        node_id = task.node_instance_id
        self.seen_input_refs_by_node[node_id] = list(task.input_refs)
        self.started_by_node.setdefault(node_id, Event()).set()
        if node_id in {"source_a", "source_b"}:
            self.release_by_node.setdefault(node_id, Event()).wait(timeout=2)
        self.executed_nodes.append(node_id)
        now = utc_now()
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=self.executor_id,
            process_generation=task.process_generation,
            status=(
                NodeResultStatus.FAILED
                if node_id in self._failed_nodes
                else NodeResultStatus.SUCCEEDED
            ),
            output_refs=[] if node_id in self._failed_nodes else [f"{node_id}-output"],
            error=(
                {"message": f"{node_id} injected failure"}
                if node_id in self._failed_nodes
                else None
            ),
            started_at=now,
            finished_at=now,
        )

    def started_event(self, node_id: str) -> Event:
        return self.started_by_node.setdefault(node_id, Event())

    def release(self, node_id: str) -> None:
        self.release_by_node.setdefault(node_id, Event()).set()


def make_dummy_dispatched_task(task_id: str = "dummy-task") -> DispatchedNodeTask:
    task = NodeTaskModel(
        task_id=task_id,
        workflow_run_id="run-dummy",
        workflow_process_id="process-dummy",
        process_generation=1,
        node_run_id=f"{task_id}-node-run",
        node_instance_id="dummy",
        node_type="core.dummy",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    executor = RecordingSuccessExecutor()
    return DispatchedNodeTask(
        task=task,
        executor=executor,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        executor_id=executor.executor_id,
    )


class RecordingImmediateExecutionPool:
    def __init__(self) -> None:
        self.submitted_task_ids: list[str] = []
        self._completed: list[ExecutorTaskCompletion] = []

    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        self.submitted_task_ids.append(dispatched_task.task.task_id)
        result = dispatched_task.executor.execute(dispatched_task.task)
        self._completed.append(
            ExecutorTaskCompletion(
                dispatched_task=dispatched_task,
                result=result,
            )
        )
        return True

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        if not self._completed:
            return None
        return self._completed.pop(0)

    def in_flight_count(self) -> int:
        return 0


class DelayedCompletionExecutionPool:
    def __init__(self) -> None:
        self.submitted: list[DispatchedNodeTask] = []
        self._completed: list[ExecutorTaskCompletion] = []

    def submit(self, dispatched_task: DispatchedNodeTask) -> bool:
        self.submitted.append(dispatched_task)
        return True

    def complete_next(self) -> bool:
        if not self.submitted:
            return False
        dispatched_task = self.submitted.pop(0)
        result = dispatched_task.executor.execute(dispatched_task.task)
        self._completed.append(
            ExecutorTaskCompletion(
                dispatched_task=dispatched_task,
                result=result,
            )
        )
        return True

    def pop_completed(self) -> ExecutorTaskCompletion | None:
        if not self._completed:
            return None
        return self._completed.pop(0)

    def in_flight_count(self) -> int:
        return len(self.submitted)


class TrackingSubprocessNodeExecutor(SubprocessNodeExecutorIpcClient):
    def __init__(
        self,
        *,
        closed_executor_ids: list[str],
        executor_id: str,
        python_executable: str,
    ) -> None:
        self._closed_executor_ids = closed_executor_ids
        super().__init__(
            executor_id=executor_id,
            python_executable=python_executable,
        )

    def close(self) -> None:
        if self.executor_id not in self._closed_executor_ids:
            self._closed_executor_ids.append(self.executor_id)
        super().close()


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def make_test_table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    logical_table_id: str,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id=None,
        mount_id=None,
        logical_table_id=logical_table_id,
        opaque_handle={
            "database_path": "runtime/run.db",
            "table_name": f"{logical_table_id}_v1",
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{logical_table_id}-field-1",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{logical_table_id}-fingerprint-1",
        version=1,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def definition() -> dict:
    return {
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
                "target_port": "in",
            }
        ],
    }


def empty_definition() -> dict:
    return {"schema_version": "1.0", "nodes": [], "connections": []}


def single_node_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source",
                "node_type": "core.source",
                "node_version": "1.0",
            }
        ],
        "connections": [],
    }


def single_test_node_definition(
    *,
    node_type: str,
    config: dict,
) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "test-node",
                "node_type": node_type,
                "node_version": "1.0",
                "config": config,
            }
        ],
        "connections": [],
    }


def table_ref_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 5,
                    "columns": ["row_id", "amount", "label"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "filter",
                "node_type": FILTER_ROWS_NODE_TYPE,
                "node_version": "1.0",
                "config": {"field": "amount", "operator": "GT", "value": 2.0},
            },
        ],
        "connections": [
            {
                "connection_id": "generate-to-filter",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "filter",
                "target_port": "in",
            }
        ],
    }


def add_columns_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 2,
                    "columns": ["row_id", "amount"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "add_column",
                "node_type": ADD_COLUMNS_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "column_name": "status",
                    "default_value": "new",
                    "data_type": "TEXT",
                },
            },
        ],
        "connections": [
            {
                "connection_id": "generate-to-add-column",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "add_column",
                "target_port": "in",
            }
        ],
    }


def save_memory_passthrough_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "generate",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 2,
                    "columns": ["row_id", "amount"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "save_memory",
                "node_type": SAVE_MEMORY_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {"table_name": "scratch", "mode": "overwrite"},
            },
            {
                "node_instance_id": "add_column",
                "node_type": ADD_COLUMNS_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "column_name": "status",
                    "default_value": "new",
                    "data_type": "TEXT",
                },
            },
        ],
        "connections": [
            {
                "connection_id": "generate-to-save-memory",
                "source_node_id": "generate",
                "source_port": "out",
                "target_node_id": "save_memory",
                "target_port": "in",
            },
            {
                "connection_id": "save-memory-to-add-column",
                "source_node_id": "save_memory",
                "source_port": "out",
                "target_node_id": "add_column",
                "target_port": "in",
            },
        ],
    }


def publish_shared_tables_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "orders",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 2,
                    "columns": ["row_id", "amount"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "customers",
                "node_type": GENERATE_TEST_TABLE_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "rows": 1,
                    "columns": ["row_id", "label"],
                    "seed": 0,
                },
            },
            {
                "node_instance_id": "publish",
                "node_type": PUBLISH_SHARED_TABLES_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "share_name": "daily_report",
                    "export_names": ["orders", "customers"],
                },
            },
        ],
        "connections": [
            {
                "connection_id": "orders-to-publish",
                "source_node_id": "orders",
                "source_port": "out",
                "target_node_id": "publish",
                "target_port": "in-orders",
            },
            {
                "connection_id": "customers-to-publish",
                "source_node_id": "customers",
                "source_port": "out",
                "target_node_id": "publish",
                "target_port": "in-customers",
            },
        ],
    }


def read_shared_tables_definition(*, exact_version: int = 1) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "read",
                "node_type": READ_SHARED_TABLES_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "share_name": "daily_report",
                    "version_policy": "EXACT_VERSION",
                    "exact_version": exact_version,
                    "selected_members": ["customers", "orders"],
                },
            }
        ],
        "connections": [],
    }


def read_shared_tables_with_consumer_definition(*, exact_version: int = 1) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "read",
                "node_type": READ_SHARED_TABLES_NODE_TYPE,
                "node_version": "1.0",
                "config": {
                    "share_name": "daily_report",
                    "version_policy": "EXACT_VERSION",
                    "exact_version": exact_version,
                    "selected_members": ["customers", "orders"],
                },
            },
            {
                "node_instance_id": "consume",
                "node_type": "core.consume",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "read-to-consume",
                "source_node_id": "read",
                "source_port": "out",
                "target_node_id": "consume",
                "target_port": "in",
            }
        ],
    }


def multi_upstream_definition() -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "node_instance_id": "source_b",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "source_a",
                "node_type": "core.source",
                "node_version": "1.0",
            },
            {
                "node_instance_id": "merge",
                "node_type": "core.merge",
                "node_version": "1.0",
            },
        ],
        "connections": [
            {
                "connection_id": "b-to-merge",
                "source_node_id": "source_b",
                "source_port": "out",
                "target_node_id": "merge",
                "target_port": "right",
            },
            {
                "connection_id": "a-to-merge",
                "source_node_id": "source_a",
                "source_port": "out",
                "target_node_id": "merge",
                "target_port": "left",
            },
        ],
    }


def test_workflow_process_executes_ready_nodes_with_default_subprocess_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Default executor workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    loaded_process = store.get_workflow_process(process.process_id)
    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert loaded_process is not None
    assert loaded_process.status == "RUNNING"
    assert loaded_process.exit_code is None
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
        "transform": "SUCCEEDED",
    }
    assert {node.executor_id for node in node_runs} == {"subprocess-node-executor"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_preview_to_node_runs_only_upstream_closure(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Preview to node workflow",
        definition={
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
                {
                    "node_instance_id": "publish",
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
                    "target_port": "in",
                },
                {
                    "connection_id": "c2",
                    "source_node_id": "transform",
                    "source_port": "out",
                    "target_node_id": "publish",
                    "target_port": "in",
                },
            ],
        },
        workflow_id="workflow-preview",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-preview",
        run_mode="preview_to_node",
        target_node_instance_id="transform",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-preview",
    )
    assert process is not None
    executor = NodeOutcomeExecutor()

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    loaded_run = store.get_workflow_run(run.workflow_run_id)
    node_runs = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }
    started_event = store.list_runtime_events()[0]
    assert exit_code == 0
    assert loaded_run is not None
    assert loaded_run.status == "SUCCEEDED"
    assert loaded_run.run_mode == "preview_to_node"
    assert loaded_run.target_node_instance_id == "transform"
    assert node_runs == {
        "source": "SUCCEEDED",
        "transform": "SUCCEEDED",
    }
    assert executor.executed_nodes == ["source", "transform"]
    assert started_event.payload["run_mode"] == "preview_to_node"
    assert started_event.payload["trigger_source"] == "manual"
    assert started_event.payload["target_node_instance_id"] == "transform"


def test_workflow_process_passes_upstream_table_refs_to_downstream_task(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-mainloop",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    workflow = store.create_workflow_definition(
        name="TableRef workflow",
        definition=table_ref_definition(),
        workflow_id="workflow-table-ref",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-table-ref",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-table-ref",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    events = store.list_runtime_events()
    queued_events = {
        event.payload["node_instance_id"]: event
        for event in events
        if event.event_type == "NODE_QUEUED"
    }
    generate_task = store.get_node_task(queued_events["generate"].payload["task_id"])
    filter_task = store.get_node_task(queued_events["filter"].payload["task_id"])
    generate_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
    )
    filter_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="filter",
    )
    assert generate_task is not None
    assert filter_task is not None
    assert generate_run is not None
    assert filter_run is not None
    generate_result = store.get_latest_succeeded_node_task_result_for_node_run(
        generate_run.node_run_id
    )
    filter_result = store.get_latest_succeeded_node_task_result_for_node_run(
        filter_run.node_run_id
    )
    assert generate_result is not None
    assert filter_result is not None
    filtered_ref = registry.get(filter_result.output_refs[0])

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert generate_task.input_refs == []
    assert filter_task.input_refs == generate_result.output_refs
    assert len(generate_result.output_refs) == 1
    assert len(filter_result.output_refs) == 1
    filtered_rows = provider.read_rows(
        filtered_ref,
        offset=0,
        limit=10,
        order_by=["row_id"],
    )
    assert filtered_rows == [
        {"row_id": 3, "amount": 3.0, "label": "label_0_3"},
        {"row_id": 4, "amount": 4.0, "label": "label_0_4"},
        {"row_id": 5, "amount": 5.0, "label": "label_0_5"},
    ]
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_runs_add_columns_node_in_table_chain(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-add-column",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    workflow = store.create_workflow_definition(
        name="Add column workflow",
        definition=add_columns_definition(),
        workflow_id="workflow-add-column",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-add-column",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-add-column",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    add_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="add_column",
    )
    assert add_run is not None
    add_result = store.get_latest_succeeded_node_task_result_for_node_run(
        add_run.node_run_id
    )
    assert add_result is not None
    output_ref = registry.get(add_result.output_refs[0])

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert [field.name for field in output_ref.schema] == [
        "row_id",
        "amount",
        "status",
    ]
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "status": "new"},
        {"row_id": 2, "amount": 2.0, "status": "new"},
    ]


def test_workflow_process_save_memory_auxiliary_ref_does_not_flow_downstream(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    memory_provider = MemoryTableProvider(tables={})
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-save-memory",
        store=store,
        registry=registry,
        table_provider=provider,
        memory_provider=memory_provider,
    )
    workflow = store.create_workflow_definition(
        name="Save memory passthrough workflow",
        definition=save_memory_passthrough_definition(),
        workflow_id="workflow-save-memory-passthrough",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-save-memory-passthrough",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-save-memory-passthrough",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    events = store.list_runtime_events()
    queued_events = {
        event.payload["node_instance_id"]: event
        for event in events
        if event.event_type == "NODE_QUEUED"
    }
    save_memory_task = store.get_node_task(
        queued_events["save_memory"].payload["task_id"]
    )
    add_column_task = store.get_node_task(
        queued_events["add_column"].payload["task_id"]
    )
    save_memory_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="save_memory",
    )
    add_column_run = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="add_column",
    )
    assert save_memory_task is not None
    assert add_column_task is not None
    assert save_memory_run is not None
    assert add_column_run is not None
    save_memory_result = store.get_latest_succeeded_node_task_result_for_node_run(
        save_memory_run.node_run_id
    )
    add_column_result = store.get_latest_succeeded_node_task_result_for_node_run(
        add_column_run.node_run_id
    )
    assert save_memory_result is not None
    assert add_column_result is not None
    assert len(save_memory_result.output_refs) == 2
    current_ref = registry.get(save_memory_result.output_refs[0])
    auxiliary_ref = registry.get(save_memory_result.output_refs[1])
    output_ref = registry.get(add_column_result.output_refs[0])

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert save_memory_task.input_refs == [current_ref.table_ref_id]
    assert add_column_task.input_refs == [current_ref.table_ref_id]
    assert current_ref.role == TableRole.CURRENT
    assert auxiliary_ref.role == TableRole.AUXILIARY
    assert auxiliary_ref.storage_kind == TableStorageKind.MEMORY
    assert memory_provider.count_rows(auxiliary_ref) == 2
    assert provider.read_rows(output_ref, offset=0, limit=10, order_by=["row_id"]) == [
        {"row_id": 1, "amount": 1.0, "status": "new"},
        {"row_id": 2, "amount": 2.0, "status": "new"},
    ]


def test_workflow_process_fails_invalid_builtin_node_config(
    tmp_path: Path,
) -> None:
    invalid_definition = table_ref_definition()
    invalid_definition["nodes"][1]["config"] = {"operator": "GT", "value": 2.0}
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-config-reject",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    workflow = store.create_workflow_definition(
        name="Invalid builtin config workflow",
        definition=invalid_definition,
        workflow_id="workflow-invalid-builtin-config",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-invalid-builtin-config",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-invalid-builtin-config",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    loaded_run = store.get_workflow_run(run.workflow_run_id)
    generate_node = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="generate",
    )
    filter_node = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="filter",
    )
    queued_nodes = [
        event.payload["node_instance_id"]
        for event in store.list_runtime_events()
        if event.event_type == "NODE_QUEUED"
    ]

    assert exit_code == 0
    assert loaded_run is not None
    assert loaded_run.status == "FAILED"
    assert loaded_run.error == {
        "error_code": "VALIDATION_ERROR",
        "message": "FilterRowsNode config.field is required",
        "origin": "NODE",
    }
    assert generate_node is not None
    assert generate_node.status == "SUCCEEDED"
    assert filter_node is not None
    assert filter_node.status == "FAILED"
    assert filter_node.error == loaded_run.error
    assert queued_nodes == ["generate", "filter"]


def test_workflow_process_runs_shared_table_nodes_in_main_loop(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    table_executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-mainloop",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    shared_executor = BuiltinSharedTableNodeExecutor(
        executor_id="builtin-shared-mainloop",
        store=store,
    )
    producer_workflow = store.create_workflow_definition(
        name="Shared table producer workflow",
        definition=publish_shared_tables_definition(),
        workflow_id="workflow-shared-producer",
    )
    producer_run = store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-shared-producer",
    )
    producer_process = store.claim_workflow_process(
        workflow_run_id=producer_run.workflow_run_id,
        process_id="process-shared-producer",
    )
    assert producer_process is not None

    producer_exit_code = run_workflow_process(
        store=store,
        workflow_run_id=producer_run.workflow_run_id,
        process_id=producer_process.process_id,
        process_generation=producer_process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=(
            lambda task: (
                shared_executor
                if task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE
                else table_executor
            )
        ),
    )

    publication = store.get_latest_shared_publication("daily_report")
    producer_queued_events = {
        event.payload["node_instance_id"]: event
        for event in store.list_runtime_events()
        if event.workflow_run_id == producer_run.workflow_run_id
        and event.event_type == "NODE_QUEUED"
    }
    publish_task = store.get_node_task(
        producer_queued_events["publish"].payload["task_id"]
    )
    assert producer_exit_code == 0
    assert store.get_workflow_run(producer_run.workflow_run_id).status == "SUCCEEDED"
    assert publish_task is not None
    assert publication is not None
    assert publication.publication_version == 1
    publication_member_refs = {
        member.export_name: member.table_ref_id for member in publication.members
    }
    assert sorted(publication_member_refs) == ["customers", "orders"]

    consumer_workflow = store.create_workflow_definition(
        name="Shared table consumer workflow",
        definition=read_shared_tables_definition(exact_version=1),
        workflow_id="workflow-shared-consumer",
    )
    consumer_run = store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-shared-consumer",
    )
    consumer_process = store.claim_workflow_process(
        workflow_run_id=consumer_run.workflow_run_id,
        process_id="process-shared-consumer",
    )
    assert consumer_process is not None

    consumer_exit_code = run_workflow_process(
        store=store,
        workflow_run_id=consumer_run.workflow_run_id,
        process_id=consumer_process.process_id,
        process_generation=consumer_process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: shared_executor,
    )

    consumer_loaded = store.get_workflow_run(consumer_run.workflow_run_id)
    consumer_queued_events = {
        event.payload["node_instance_id"]: event
        for event in store.list_runtime_events()
        if event.workflow_run_id == consumer_run.workflow_run_id
        and event.event_type == "NODE_QUEUED"
    }
    read_node = store.get_node_run_for_instance(
        workflow_run_id=consumer_run.workflow_run_id,
        node_instance_id="read",
    )
    read_task = store.get_node_task(consumer_queued_events["read"].payload["task_id"])
    assert consumer_exit_code == 0
    assert consumer_loaded is not None
    assert consumer_loaded.status == "SUCCEEDED"
    assert consumer_loaded.input_snapshot_id is not None
    assert read_node is not None
    assert read_task is not None
    read_result = store.get_latest_succeeded_node_task_result_for_node_run(
        read_node.node_run_id
    )
    assert read_result is not None
    assert read_result.output_refs == [
        publication_member_refs["customers"],
        publication_member_refs["orders"],
    ]
    snapshot = store.get_input_snapshot(consumer_loaded.input_snapshot_id)
    assert snapshot is not None
    assert snapshot.inputs[0].publication_id == publication.publication_id
    assert snapshot.inputs[0].publication_version == 1
    assert snapshot.inputs[0].selected_members == ("customers", "orders")
    leases = store.list_read_leases_by_workflow_run(consumer_run.workflow_run_id)
    assert len(leases) == 1
    assert leases[0].publication_id == publication.publication_id
    assert leases[0].selected_members == ("customers", "orders")
    assert leases[0].released_at is not None
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []


def test_stage_i_workflow_process_keeps_consumer_pinned_to_read_publication(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    table_executor = BuiltinTableNodeExecutor(
        executor_id="builtin-table-i9",
        store=store,
        registry=registry,
        table_provider=provider,
    )
    shared_executor = BuiltinSharedTableNodeExecutor(
        executor_id="builtin-shared-i9",
        store=store,
    )

    producer_workflow = store.create_workflow_definition(
        name="Stage I producer workflow",
        definition=publish_shared_tables_definition(),
        workflow_id="workflow-stage-i-producer",
    )
    producer_v1_run = store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-stage-i-producer-v1",
    )
    producer_v1_process = store.claim_workflow_process(
        workflow_run_id=producer_v1_run.workflow_run_id,
        process_id="process-stage-i-producer-v1",
    )
    assert producer_v1_process is not None

    producer_v1_exit_code = run_workflow_process(
        store=store,
        workflow_run_id=producer_v1_run.workflow_run_id,
        process_id=producer_v1_process.process_id,
        process_generation=producer_v1_process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=(
            lambda task: (
                shared_executor
                if task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE
                else table_executor
            )
        ),
    )

    publication_v1 = store.get_latest_shared_publication("daily_report")
    assert producer_v1_exit_code == 0
    assert store.get_workflow_run(producer_v1_run.workflow_run_id).status == "SUCCEEDED"
    assert publication_v1 is not None
    assert publication_v1.publication_version == 1
    publication_v1_member_refs = {
        member.export_name: member.table_ref_id for member in publication_v1.members
    }
    assert sorted(publication_v1_member_refs) == ["customers", "orders"]

    consumer_workflow = store.create_workflow_definition(
        name="Stage I consumer workflow",
        definition=read_shared_tables_with_consumer_definition(exact_version=1),
        workflow_id="workflow-stage-i-consumer",
    )
    consumer_run = store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-stage-i-consumer",
    )
    consumer_process = store.claim_workflow_process(
        workflow_run_id=consumer_run.workflow_run_id,
        process_id="process-stage-i-consumer",
    )
    assert consumer_process is not None
    blocking_consumer_executor = BlockingInputRefsExecutor()
    consumer_exit_codes: list[int] = []

    def consumer_executor_factory(task: NodeTaskModel):
        if task.node_type == READ_SHARED_TABLES_NODE_TYPE:
            return shared_executor
        return blocking_consumer_executor

    def run_consumer_workflow() -> None:
        consumer_exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=consumer_run.workflow_run_id,
                process_id=consumer_process.process_id,
                process_generation=consumer_process.process_generation,
                heartbeat_interval_seconds=0,
                executor_factory=consumer_executor_factory,
                execution_mode="threaded",
            )
        )

    consumer_thread = Thread(
        target=run_consumer_workflow,
    )
    consumer_thread.start()
    assert blocking_consumer_executor.started.wait(timeout=5)

    consumer_running = store.get_workflow_run(consumer_run.workflow_run_id)
    read_node = store.get_node_run_for_instance(
        workflow_run_id=consumer_run.workflow_run_id,
        node_instance_id="read",
    )
    assert consumer_running is not None
    assert consumer_running.status == "RUNNING"
    assert consumer_running.input_snapshot_id is not None
    consumer_snapshot = store.get_input_snapshot(consumer_running.input_snapshot_id)
    assert read_node is not None
    assert read_node.status == "SUCCEEDED"
    assert consumer_snapshot is not None
    assert consumer_snapshot.inputs[0].publication_id == publication_v1.publication_id
    assert consumer_snapshot.inputs[0].publication_version == 1
    assert consumer_snapshot.inputs[0].selected_members == ("customers", "orders")
    assert blocking_consumer_executor.seen_input_refs_by_node["consume"] == [
        publication_v1_member_refs["customers"],
        publication_v1_member_refs["orders"],
    ]
    active_leases = store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    )
    assert len(active_leases) == 1
    assert active_leases[0].publication_id == publication_v1.publication_id
    assert active_leases[0].publication_version == 1

    producer_v2_run = store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-stage-i-producer-v2",
    )
    producer_v2_process = store.claim_workflow_process(
        workflow_run_id=producer_v2_run.workflow_run_id,
        process_id="process-stage-i-producer-v2",
    )
    assert producer_v2_process is not None

    producer_v2_exit_code = run_workflow_process(
        store=store,
        workflow_run_id=producer_v2_run.workflow_run_id,
        process_id=producer_v2_process.process_id,
        process_generation=producer_v2_process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=(
            lambda task: (
                shared_executor
                if task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE
                else table_executor
            )
        ),
    )

    publication_v2 = store.get_latest_shared_publication("daily_report")
    assert producer_v2_exit_code == 0
    assert store.get_workflow_run(producer_v2_run.workflow_run_id).status == "SUCCEEDED"
    assert publication_v2 is not None
    assert publication_v2.publication_version == 2
    assert publication_v2.publication_id != publication_v1.publication_id
    assert {
        member.export_name: member.table_ref_id for member in publication_v2.members
    } != publication_v1_member_refs

    consumer_still_pinned = store.get_workflow_run(consumer_run.workflow_run_id)
    assert consumer_still_pinned is not None
    assert (
        consumer_still_pinned.input_snapshot_id
        == consumer_snapshot.input_snapshot_id
    )
    assert store.get_input_snapshot(consumer_snapshot.input_snapshot_id) == (
        consumer_snapshot
    )
    assert blocking_consumer_executor.seen_input_refs_by_node["consume"] == [
        publication_v1_member_refs["customers"],
        publication_v1_member_refs["orders"],
    ]

    blocking_consumer_executor.release.set()
    consumer_thread.join(timeout=5)
    assert not consumer_thread.is_alive()
    assert consumer_exit_codes == [0]

    consumer_loaded = store.get_workflow_run(consumer_run.workflow_run_id)
    consume_node = store.get_node_run_for_instance(
        workflow_run_id=consumer_run.workflow_run_id,
        node_instance_id="consume",
    )
    assert consumer_loaded is not None
    assert consumer_loaded.status == "SUCCEEDED"
    assert consume_node is not None
    consume_result = store.get_latest_succeeded_node_task_result_for_node_run(
        consume_node.node_run_id
    )
    assert consume_result is not None
    assert consume_result.output_refs == [
        publication_v1_member_refs["customers"],
        publication_v1_member_refs["orders"],
    ]
    leases = store.list_read_leases_by_workflow_run(consumer_run.workflow_run_id)
    assert len(leases) == 1
    assert leases[0].publication_id == publication_v1.publication_id
    assert leases[0].publication_version == 1
    assert leases[0].released_at is not None
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []


def test_workflow_process_releases_unreleased_read_leases_on_failure(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    producer_workflow = store.create_workflow_definition(
        name="Lease producer workflow",
        definition=empty_definition(),
        workflow_id="workflow-lease-producer",
    )
    producer_run = store.create_workflow_run(
        workflow_id=producer_workflow.workflow_id,
        workflow_run_id="run-lease-producer",
    )
    producer_node = store.create_node_run(
        workflow_run_id=producer_run.workflow_run_id,
        node_instance_id="producer",
        node_type="builtin.producer",
        node_run_id="node-lease-producer",
    )
    orders = make_test_table_ref(
        table_ref_id="table-lease-orders",
        workflow_run_id=producer_run.workflow_run_id,
        node_run_id=producer_node.node_run_id,
        logical_table_id="orders",
    )
    store.register_table_ref(orders)
    publication = store.create_shared_publication(
        publication_id="publication-lease",
        share_name="daily_report",
        producer_workflow_id=producer_workflow.workflow_id,
        producer_run_id=producer_run.workflow_run_id,
        members={"orders": orders.table_ref_id},
    )
    consumer_workflow = store.create_workflow_definition(
        name="Lease failure consumer workflow",
        definition=single_node_definition(),
        workflow_id="workflow-lease-consumer",
    )
    consumer_run = store.create_workflow_run(
        workflow_id=consumer_workflow.workflow_id,
        workflow_run_id="run-lease-consumer",
    )
    lease = store.create_read_lease(
        lease_id="lease-to-release",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() + timedelta(seconds=60),
    )
    expired_lease = store.create_read_lease(
        lease_id="expired-lease-to-release",
        publication_id=publication.publication_id,
        publication_version=publication.publication_version,
        consumer_workflow_run_id=consumer_run.workflow_run_id,
        selected_members=("orders",),
        expires_at=utc_now() - timedelta(seconds=1),
    )
    process = store.claim_workflow_process(
        workflow_run_id=consumer_run.workflow_run_id,
        process_id="process-lease-consumer",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=consumer_run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedFailingExecutor(),
    )

    released = store.get_read_lease(lease.lease_id)
    released_expired = store.get_read_lease(expired_lease.lease_id)
    assert exit_code == 0
    assert store.get_workflow_run(consumer_run.workflow_run_id).status == "FAILED"
    assert released is not None
    assert released.released_at is not None
    assert released_expired is not None
    assert released_expired.released_at is not None
    assert store.list_read_leases_by_workflow_run(
        consumer_run.workflow_run_id,
        active_only=True,
    ) == []


def test_workflow_process_passes_multiple_upstream_table_refs_in_stable_order(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source_b": ["table-b1"],
            "source_a": ["table-a1", "table-a2"],
            "merge": ["merged-table"],
        }
    )
    workflow = store.create_workflow_definition(
        name="Multi upstream TableRef workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-multi-upstream",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-multi-upstream",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-multi-upstream",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert executor.seen_input_refs_by_node["source_a"] == []
    assert executor.seen_input_refs_by_node["source_b"] == []
    assert executor.seen_input_refs_by_node["merge"] == [
        "table-a1",
        "table-a2",
        "table-b1",
    ]


def test_workflow_process_limits_ready_dispatch_per_cycle(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    event_sink = DatabaseEventSink(store)
    definition_data = multi_upstream_definition()
    workflow = store.create_workflow_definition(
        name="Limited ready dispatch workflow",
        definition=definition_data,
        workflow_id="workflow-limited-ready-dispatch",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-limited-ready-dispatch",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-limited-ready-dispatch",
    )
    assert process is not None
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition_data))
    initialize_node_runs(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    task_manager = NodeTaskManager(store=store, event_sink=event_sink, dag=dag)
    executor = RecordingSuccessExecutor()

    dispatched_count = workflow_process_main._dispatch_ready_nodes(
        store=store,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        dag=dag,
        task_manager=task_manager,
        executor_factory=lambda _task: executor,
        cleanup_staging_for_node=None,
        close_executor_after_task=True,
        cancel_grace_seconds=5,
        max_ready_dispatch_per_cycle=1,
        max_concurrent_node_tasks=None,
        execution_pool=RecordingImmediateExecutionPool(),
        event_sink=event_sink,
    )

    node_runs = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }
    assert dispatched_count == 1
    assert executor.executed_nodes == ["source_b"]
    assert node_runs == {
        "source_a": "READY",
        "source_b": "SUCCEEDED",
        "merge": "WAITING_DEPENDENCY",
    }
    assert store.get_workflow_run(run.workflow_run_id).status == "PENDING"
    assert [event.event_type for event in store.list_runtime_events()] == [
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
    ]


def test_workflow_process_uses_injected_execution_pool(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source": ["source-output"],
            "transform": ["transform-output"],
        }
    )
    execution_pool = RecordingImmediateExecutionPool()
    workflow = store.create_workflow_definition(
        name="Injected execution pool workflow",
        definition=definition(),
        workflow_id="workflow-injected-execution-pool",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-injected-execution-pool",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-injected-execution-pool",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
    )

    assert exit_code == 0
    assert len(execution_pool.submitted_task_ids) == 2
    assert executor.seen_input_refs_by_node == {
        "source": [],
        "transform": ["source-output"],
    }
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"


def test_workflow_process_with_threaded_pool_does_not_block_after_dispatch(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = ReleasableBlockingExecutor()
    execution_pool = ThreadedNodeTaskExecutionPool()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution pool workflow",
        definition=single_node_definition(),
        workflow_id="workflow-threaded-execution-pool",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-pool",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-pool",
    )
    assert process is not None

    def release_during_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        assert sleep_calls == 1
        assert executor.started.wait(timeout=1)
        assert execution_pool.in_flight_count() == 1
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        assert node_run.status == "RUNNING"
        assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"
        executor.release.set()
        deadline = time.monotonic() + 1
        while execution_pool.in_flight_count() > 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert execution_pool.in_flight_count() == 0

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
        sleep_func=release_during_sleep,
    )

    assert exit_code == 0
    assert sleep_calls == 1
    assert execution_pool.in_flight_count() == 0
    assert executor.closed.is_set()
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_with_threaded_pool_applies_executor_error_completion(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    execution_pool = ThreadedNodeTaskExecutionPool()
    workflow = store.create_workflow_definition(
        name="Threaded execution pool failure workflow",
        definition=single_node_definition(),
        workflow_id="workflow-threaded-execution-pool-failure",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-pool-failure",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-pool-failure",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedRaisingExecutor(),
        execution_pool=execution_pool,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]

    assert exit_code == 0
    assert execution_pool.in_flight_count() == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "FAILED"
    assert node_run.error == {
        "message": "injected threaded failure",
        "error_type": "RuntimeError",
    }
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_with_threaded_pool_requests_cancel_for_in_flight_task(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = CooperativeCancelExecutor()
    execution_pool = ThreadedNodeTaskExecutionPool()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution pool cancel workflow",
        definition=single_node_definition(),
        workflow_id="workflow-threaded-execution-pool-cancel",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-pool-cancel",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-pool-cancel",
    )
    assert process is not None

    def request_cancel_during_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        assert sleep_calls == 1
        assert executor.started.wait(timeout=1)
        assert execution_pool.in_flight_count() == 1
        store.request_workflow_process_cancel(run.workflow_run_id)

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
        sleep_func=request_cancel_during_sleep,
    )

    loaded_node = store.list_node_runs(run.workflow_run_id)[0]
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)

    assert exit_code == 0
    assert sleep_calls == 1
    assert executor.cancel_requested.is_set()
    assert executor.cancelled_task_id is not None
    assert loaded_workflow is not None
    assert loaded_workflow.status == "CANCELLED"
    assert loaded_node.status == "CANCEL_REQUESTED"
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "WORKFLOW_CANCELLED",
    ]


def test_workflow_process_with_threaded_pool_applies_parallel_ready_out_of_order(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = ReleasableMultiNodeExecutor()
    execution_pool = ThreadedNodeTaskExecutionPool()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution pool multi ready workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-threaded-execution-pool-multi-ready",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-pool-multi-ready",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-pool-multi-ready",
    )
    assert process is not None

    def wait_for_executed_nodes(expected_nodes: list[str]) -> bool:
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if executor.executed_nodes == expected_nodes:
                return True
            time.sleep(0.001)
        return executor.executed_nodes == expected_nodes

    def release_sources_out_of_order(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            assert executor.started_event("source_a").wait(timeout=1)
            assert executor.started_event("source_b").wait(timeout=1)
            assert execution_pool.in_flight_count() == 2
            executor.release("source_a")
            return
        if sleep_calls == 2:
            assert wait_for_executed_nodes(["source_a"])
            assert {
                node.node_instance_id: node.status
                for node in store.list_node_runs(run.workflow_run_id)
            } == {
                "merge": "WAITING_DEPENDENCY",
                "source_a": "SUCCEEDED",
                "source_b": "RUNNING",
            }
            executor.release("source_b")

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
        max_concurrent_node_tasks=2,
        sleep_func=release_sources_out_of_order,
    )

    node_runs = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }

    assert exit_code == 0
    assert sleep_calls == 2
    assert execution_pool.in_flight_count() == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert node_runs == {
        "merge": "SUCCEEDED",
        "source_a": "SUCCEEDED",
        "source_b": "SUCCEEDED",
    }
    assert executor.seen_input_refs_by_node == {
        "source_a": [],
        "source_b": [],
        "merge": ["source_a-output", "source_b-output"],
    }
    assert executor.executed_nodes == ["source_a", "source_b", "merge"]
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_threaded_execution_mode_allows_two_ready_tasks(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = ReleasableMultiNodeExecutor()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution mode workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-threaded-execution-mode",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-mode",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-mode",
    )
    assert process is not None

    def release_sources_when_both_running(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            assert executor.started_event("source_a").wait(timeout=1)
            assert executor.started_event("source_b").wait(timeout=1)
            assert {
                node.node_instance_id: node.status
                for node in store.list_node_runs(run.workflow_run_id)
            } == {
                "merge": "WAITING_DEPENDENCY",
                "source_a": "RUNNING",
                "source_b": "RUNNING",
            }
            executor.release("source_a")
            executor.release("source_b")

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_mode="threaded",
        max_concurrent_node_tasks=2,
        sleep_func=release_sources_when_both_running,
    )

    assert exit_code == 0
    assert sleep_calls >= 1
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    } == {
        "merge": "SUCCEEDED",
        "source_a": "SUCCEEDED",
        "source_b": "SUCCEEDED",
    }
    assert executor.seen_input_refs_by_node == {
        "source_a": [],
        "source_b": [],
        "merge": ["source_a-output", "source_b-output"],
    }


def test_workflow_process_threaded_execution_mode_defaults_to_one_task(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = ReleasableMultiNodeExecutor()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution mode default concurrency workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-threaded-execution-mode-default-concurrency",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-mode-default-concurrency",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-mode-default-concurrency",
    )
    assert process is not None

    def check_only_one_source_running(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            assert executor.started_event("source_b").wait(timeout=1)
            assert not executor.started_event("source_a").is_set()
            assert {
                node.node_instance_id: node.status
                for node in store.list_node_runs(run.workflow_run_id)
            } == {
                "merge": "WAITING_DEPENDENCY",
                "source_a": "READY",
                "source_b": "RUNNING",
            }
            executor.release("source_b")
            return
        if executor.started_event("source_a").wait(timeout=1):
            executor.release("source_a")

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_mode="threaded",
        sleep_func=check_only_one_source_running,
    )

    assert exit_code == 0
    assert sleep_calls >= 2
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"


def test_workflow_process_with_threaded_pool_keeps_failure_after_late_success(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = ReleasableMultiNodeExecutor(failed_nodes={"source_a"})
    execution_pool = ThreadedNodeTaskExecutionPool()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Threaded execution pool failure isolation workflow",
        definition=multi_upstream_definition(),
        workflow_id="workflow-threaded-execution-pool-failure-isolation",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-threaded-execution-pool-failure-isolation",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-threaded-execution-pool-failure-isolation",
    )
    assert process is not None

    def release_failure_then_late_success(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        assert executor.started_event("source_a").wait(timeout=1)
        assert executor.started_event("source_b").wait(timeout=1)
        if sleep_calls == 1:
            executor.release("source_a")
            return

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
        max_concurrent_node_tasks=2,
        sleep_func=release_failure_then_late_success,
    )

    node_runs_before_late_success = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }
    assert node_runs_before_late_success == {
        "merge": "WAITING_DEPENDENCY",
        "source_a": "FAILED",
        "source_b": "RUNNING",
    }
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert execution_pool.in_flight_count() == 1

    executor.release("source_b")
    deadline = time.monotonic() + 1
    late_completion = None
    while time.monotonic() < deadline:
        late_completion = execution_pool.pop_completed()
        if late_completion is not None:
            break
        time.sleep(0.01)

    node_runs = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }

    assert exit_code == 0
    assert sleep_calls >= 1
    assert execution_pool.closed is True
    assert execution_pool.submit(make_dummy_dispatched_task()) is False
    assert late_completion is not None
    assert late_completion.dispatched_task.node_instance_id == "source_b"
    assert late_completion.result is not None
    assert late_completion.result.status == NodeResultStatus.SUCCEEDED
    assert execution_pool.in_flight_count() == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_runs == {
        "merge": "WAITING_DEPENDENCY",
        "source_a": "FAILED",
        "source_b": "RUNNING",
    }
    assert executor.seen_input_refs_by_node == {
        "source_a": [],
        "source_b": [],
    }
    assert executor.executed_nodes == ["source_a", "source_b"]
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_drains_pending_pool_completions_before_dispatch(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source": ["source-output"],
            "transform": ["transform-output"],
        }
    )
    execution_pool = DelayedCompletionExecutionPool()
    sleep_calls = 0
    workflow = store.create_workflow_definition(
        name="Pending completion workflow",
        definition=definition(),
        workflow_id="workflow-pending-completion",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-pending-completion",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-pending-completion",
    )
    assert process is not None

    def complete_during_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        assert execution_pool.complete_next() is True

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        execution_pool=execution_pool,
        max_ready_dispatch_per_cycle=1,
        sleep_func=complete_during_sleep,
    )

    assert exit_code == 0
    assert sleep_calls == 2
    assert executor.seen_input_refs_by_node == {
        "source": [],
        "transform": ["source-output"],
    }
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_dispatches_ready_candidate_to_running_task(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    event_sink = DatabaseEventSink(store)
    definition_data = multi_upstream_definition()
    workflow = store.create_workflow_definition(
        name="Ready candidate dispatch workflow",
        definition=definition_data,
        workflow_id="workflow-ready-candidate-dispatch",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-ready-candidate-dispatch",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-ready-candidate-dispatch",
    )
    assert process is not None
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition_data))
    initialize_node_runs(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    task_manager = NodeTaskManager(store=store, event_sink=event_sink, dag=dag)
    candidates = collect_ready_node_candidates(
        store=store,
        workflow_run_id=run.workflow_run_id,
        dag=dag,
    )
    executor = RecordingSuccessExecutor()

    dispatched = workflow_process_main.dispatch_ready_node_candidate(
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        candidate=candidates[0],
        task_manager=task_manager,
        executor_factory=lambda _task: executor,
    )

    assert dispatched is not None
    assert dispatched.task.node_instance_id == "source_b"
    assert dispatched.node_instance_id == "source_b"
    assert dispatched.executor is executor
    assert dispatched.executor_id == "recording-success-executor"
    loaded_task = store.get_node_task(dispatched.task.task_id)
    loaded_node = store.get_node_run(dispatched.node_run_id)
    assert loaded_task == dispatched.task
    assert loaded_node is not None
    assert loaded_node.status == "RUNNING"
    assert loaded_node.executor_id == "recording-success-executor"
    assert loaded_node.started_at is not None
    assert [event.event_type for event in store.list_runtime_events()] == [
        "NODE_QUEUED",
        "NODE_STARTED",
    ]
    assert store.list_runtime_events()[0].payload["task_id"] == dispatched.task.task_id
    assert store.list_runtime_events()[1].payload["task_id"] == dispatched.task.task_id


def test_workflow_process_does_not_dispatch_when_capacity_is_full(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    event_sink = DatabaseEventSink(store)
    definition_data = multi_upstream_definition()
    workflow = store.create_workflow_definition(
        name="Capacity limited ready dispatch workflow",
        definition=definition_data,
        workflow_id="workflow-capacity-limited-ready-dispatch",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-capacity-limited-ready-dispatch",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-capacity-limited-ready-dispatch",
    )
    assert process is not None
    dag = build_workflow_dag(WorkflowDefinitionModel.model_validate(definition_data))
    initialize_node_runs(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        dag=dag,
    )
    source_b = store.get_node_run_for_instance(
        workflow_run_id=run.workflow_run_id,
        node_instance_id="source_b",
    )
    assert source_b is not None
    running_source_b = store.update_node_run_status(
        source_b.node_run_id,
        NodeRunStatus.RUNNING,
        expected_state_version=source_b.state_version,
        allowed_source_statuses=[NodeRunStatus.READY],
    )
    assert running_source_b is not None
    task_manager = NodeTaskManager(store=store, event_sink=event_sink, dag=dag)
    executor = RecordingSuccessExecutor()

    dispatched_count = workflow_process_main._dispatch_ready_nodes(
        store=store,
        workflow_run_id=run.workflow_run_id,
        workflow_process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        dag=dag,
        task_manager=task_manager,
        executor_factory=lambda _task: executor,
        cleanup_staging_for_node=None,
        close_executor_after_task=True,
        cancel_grace_seconds=5,
        max_ready_dispatch_per_cycle=None,
        max_concurrent_node_tasks=1,
        execution_pool=RecordingImmediateExecutionPool(),
        event_sink=event_sink,
    )

    node_runs = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }
    assert dispatched_count == 0
    assert executor.executed_nodes == []
    assert node_runs == {
        "source_a": "READY",
        "source_b": "RUNNING",
        "merge": "WAITING_DEPENDENCY",
    }
    assert store.list_runtime_events() == []


def test_workflow_process_passes_empty_input_refs_when_upstream_has_no_outputs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    executor = NodeAwareOutputExecutor(
        {
            "source": [],
            "transform": ["transform-output"],
        }
    )
    workflow = store.create_workflow_definition(
        name="Empty upstream output workflow",
        definition=definition(),
        workflow_id="workflow-empty-upstream-output",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-empty-upstream-output",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-empty-upstream-output",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert executor.seen_input_refs_by_node == {
        "source": [],
        "transform": [],
    }


def test_workflow_process_reuses_default_executor_for_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    created_executor_ids: list[str] = []
    executed_task_ids: list[str] = []
    closed_executor_ids: list[str] = []

    class TrackingReusableDefaultExecutor:
        def __init__(self) -> None:
            self.executor_id = f"default-reusable-{len(created_executor_ids) + 1}"
            created_executor_ids.append(self.executor_id)

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            executed_task_ids.append(task.task_id)
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                started_at=now,
                finished_at=now,
            )

        def close(self) -> None:
            closed_executor_ids.append(self.executor_id)

    monkeypatch.setattr(
        workflow_process_main,
        "SubprocessNodeExecutorIpcClient",
        TrackingReusableDefaultExecutor,
    )
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reusable default executor workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None

    exit_code = workflow_process_main.run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_runs = store.list_node_runs(run.workflow_run_id)
    assert exit_code == 0
    assert created_executor_ids == ["default-reusable-1"]
    assert len(executed_task_ids) == 2
    assert closed_executor_ids == ["default-reusable-1"]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.executor_id for node in node_runs} == {"default-reusable-1"}


def test_reusable_default_executor_owner_rebuilds_after_closed_executor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    created_executor_ids: list[str] = []
    executed_executor_ids: list[str] = []
    closed_executor_ids: list[str] = []

    class TrackingRebuildableDefaultExecutor:
        def __init__(self) -> None:
            self.executor_id = f"default-rebuild-{len(created_executor_ids) + 1}"
            self._closed = False
            created_executor_ids.append(self.executor_id)

        @property
        def closed(self) -> bool:
            return self._closed

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            executed_executor_ids.append(self.executor_id)
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                started_at=now,
                finished_at=now,
            )

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            closed_executor_ids.append(self.executor_id)

    monkeypatch.setattr(
        workflow_process_main,
        "SubprocessNodeExecutorIpcClient",
        TrackingRebuildableDefaultExecutor,
    )
    task = NodeTaskModel(
        task_id="task-rebuild",
        workflow_run_id="run-rebuild",
        workflow_process_id="process-rebuild",
        process_generation=1,
        node_run_id="node-run-rebuild",
        node_instance_id="node-rebuild",
        node_type="core.source",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )
    store = RuntimeStore("sqlite:///:memory:")
    owner = workflow_process_main._DefaultWorkflowProcessExecutorOwner(
        store=store,
        runtime_dir=tmp_path / "runtime",
    )
    first = owner.executor_for_task(task)
    first.close()
    second = owner.executor_for_task(task)
    result = second.execute(task)
    owner.close()
    store.dispose()

    assert first is not second
    assert result.executor_id == "default-rebuild-2"
    assert created_executor_ids == ["default-rebuild-1", "default-rebuild-2"]
    assert executed_executor_ids == ["default-rebuild-2"]
    assert closed_executor_ids == ["default-rebuild-1", "default-rebuild-2"]


def test_default_executor_owner_uses_builtin_shared_table_executor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    created_shared_executor_ids: list[str] = []
    created_subprocess_executor_ids: list[str] = []

    class TrackingSharedTableExecutor:
        def __init__(self, *, store: RuntimeStore) -> None:
            self.executor_id = f"shared-table-{len(created_shared_executor_ids) + 1}"
            created_shared_executor_ids.append(self.executor_id)
            self.store = store

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                started_at=now,
                finished_at=now,
            )

    class TrackingDefaultSubprocessExecutor:
        def __init__(self) -> None:
            self.executor_id = (
                f"default-subprocess-{len(created_subprocess_executor_ids) + 1}"
            )
            created_subprocess_executor_ids.append(self.executor_id)

        def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
            now = utc_now()
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=self.executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.SUCCEEDED,
                started_at=now,
                finished_at=now,
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        workflow_process_main,
        "BuiltinSharedTableNodeExecutor",
        TrackingSharedTableExecutor,
    )
    monkeypatch.setattr(
        workflow_process_main,
        "SubprocessNodeExecutorIpcClient",
        TrackingDefaultSubprocessExecutor,
    )
    store = RuntimeStore("sqlite:///:memory:")
    owner = workflow_process_main._DefaultWorkflowProcessExecutorOwner(
        store=store,
        runtime_dir=tmp_path / "runtime",
    )
    shared_task = NodeTaskModel(
        task_id="task-shared",
        workflow_run_id="run-shared",
        workflow_process_id="process-shared",
        process_generation=1,
        node_run_id="node-run-shared",
        node_instance_id="node-shared",
        node_type=READ_SHARED_TABLES_NODE_TYPE,
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={"share_name": "daily_report", "version_policy": "LATEST"},
        timeout_seconds=60,
    )
    normal_task = NodeTaskModel(
        task_id="task-normal",
        workflow_run_id="run-normal",
        workflow_process_id="process-normal",
        process_generation=1,
        node_run_id="node-run-normal",
        node_instance_id="node-normal",
        node_type="core.source",
        node_version="1.0",
        attempt=1,
        input_refs=[],
        config={},
        timeout_seconds=60,
    )

    shared_executor = owner.executor_for_task(shared_task)
    normal_executor = owner.executor_for_task(normal_task)
    owner.close()
    store.dispose()

    assert shared_executor.executor_id == "shared-table-1"
    assert normal_executor.executor_id == "default-subprocess-1"
    assert created_shared_executor_ids == ["shared-table-1"]
    assert created_subprocess_executor_ids == ["default-subprocess-1"]


def test_workflow_process_runs_single_node_with_subprocess_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Subprocess executor workflow",
        definition=single_node_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    executors: list[SubprocessNodeExecutorIpcClient] = []
    closed_executor_ids: list[str] = []

    def create_executor(_task: NodeTaskModel) -> SubprocessNodeExecutorIpcClient:
        executor = TrackingSubprocessNodeExecutor(
            closed_executor_ids=closed_executor_ids,
            executor_id=f"subprocess-mainloop-{len(executors) + 1}",
            python_executable=sys.executable,
        )
        executors.append(executor)
        return executor

    try:
        exit_code = run_workflow_process(
            store=store,
            workflow_run_id=run.workflow_run_id,
            process_id=process.process_id,
            process_generation=process.process_generation,
            heartbeat_interval_seconds=0,
            executor_factory=create_executor,
        )
        node_runs = store.list_node_runs(run.workflow_run_id)
        closed_executor_ids_after_run = list(closed_executor_ids)
    finally:
        for executor in executors:
            executor.close()

    assert exit_code == 0
    assert len(executors) == 1
    assert closed_executor_ids_after_run == ["subprocess-mainloop-1"]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert {node.node_instance_id: node.status for node in node_runs} == {
        "source": "SUCCEEDED",
    }
    assert {node.executor_id for node in node_runs} == {"subprocess-mainloop-1"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_runs_delay_test_node_with_default_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Delay test node workflow",
        definition=single_test_node_definition(
            node_type=DELAY_TEST_NODE_TYPE,
            config={
                "duration_seconds": 0.02,
                "heartbeat_interval_seconds": 0.005,
                "progress_interval_seconds": 0.005,
            },
        ),
        workflow_id="workflow-delay-test",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-delay-test",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-delay-test",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    events = store.list_runtime_events()
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"
    assert node_run.status == "SUCCEEDED"
    assert node_run.executor_id == "subprocess-node-executor"
    assert node_run.last_heartbeat is not None
    assert node_run.progress == 1.0
    assert node_run.current_stage == "completed"
    assert "NODE_PROGRESS" in [event.event_type for event in events]


def test_workflow_process_marks_raise_exception_fault_node_failed(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Raise exception fault workflow",
        definition=single_test_node_definition(
            node_type=FAULT_TEST_NODE_TYPE,
            config={
                "mode": FAULT_MODE_RAISE_EXCEPTION,
                "message": "expected workflow fault",
            },
        ),
        workflow_id="workflow-raise-fault",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-raise-fault",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-raise-fault",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "FAILED"
    assert node_run.error == {
        "message": "expected workflow fault",
        "error_type": "RuntimeError",
    }
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_marks_process_exit_fault_node_failed(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Process exit fault workflow",
        definition=single_test_node_definition(
            node_type=FAULT_TEST_NODE_TYPE,
            config={"mode": FAULT_MODE_PROCESS_EXIT, "exit_code": 7},
        ),
        workflow_id="workflow-process-exit-fault",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-process-exit-fault",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-exit-fault",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "FAILED"
    assert node_run.error is not None
    assert node_run.error["message"] == (
        "Node executor subprocess exited before completing task"
    )
    assert node_run.error["exit_code"] == 7


def test_workflow_process_times_out_infinite_loop_fault_node_with_default_executor(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Infinite loop fault workflow",
        definition=single_test_node_definition(
            node_type=FAULT_TEST_NODE_TYPE,
            config={
                "mode": FAULT_MODE_INFINITE_LOOP,
                "timeout_seconds": 1,
                "heartbeat_interval_seconds": 0.05,
                "progress_interval_seconds": 0.05,
            },
        ),
        workflow_id="workflow-infinite-loop-fault",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-infinite-loop-fault",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-infinite-loop-fault",
    )
    assert process is not None
    started_at = time.monotonic()

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
    )
    elapsed_seconds = time.monotonic() - started_at

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    events = store.list_runtime_events()
    assert exit_code == 0
    assert elapsed_seconds < 10
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert node_run.status == "TIMED_OUT"
    assert node_run.executor_id == "subprocess-node-executor"
    assert node_run.last_heartbeat is not None
    assert node_run.current_stage == "infinite_loop"
    assert node_run.error is not None
    assert node_run.error["timeout_seconds"] == 1
    assert store.get_latest_succeeded_node_task_result_for_node_run(
        node_run.node_run_id
    ) is None
    assert "NODE_PROGRESS" in [event.event_type for event in events]
    terminal_event_types = [
        event.event_type
        for event in events
        if event.event_type in {"NODE_TIMEOUT", "WORKFLOW_FAILED"}
    ]
    assert terminal_event_types[-2:] == [
        "NODE_TIMEOUT",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_records_executor_heartbeat_and_progress(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reporting executor workflow",
        definition=single_node_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedReportingExecutor(),
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    events = store.list_runtime_events()
    assert exit_code == 0
    assert node_run.status == "SUCCEEDED"
    assert node_run.executor_id == "injected-reporting-executor"
    assert node_run.last_heartbeat is not None
    assert node_run.progress == 0.5
    assert node_run.current_stage == "halfway"
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_PROGRESS",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]
    assert events[3].payload == {
        "process_id": process.process_id,
        "task_id": events[1].payload["task_id"],
        "executor_id": "injected-reporting-executor",
        "node_instance_id": "source",
        "progress": 0.5,
        "current_stage": "halfway",
        "metrics": {"rows": 10},
    }


def test_workflow_process_background_fast_filters_progress_feedback(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    definition_data = single_node_definition() | {
        "runtime_options": {
            "workflow": {
                "profile": "background_fast",
            }
        }
    }
    workflow = store.create_workflow_definition(
        name="Background fast reporting workflow",
        definition=definition_data,
        workflow_id="workflow-background-fast-reporting",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-background-fast-reporting",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-background-fast-reporting",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedReportingExecutor(
            output_refs=["source-output"]
        ),
    )

    node_run = store.list_node_runs(run.workflow_run_id)[0]
    result = store.get_latest_succeeded_node_task_result_for_node_run(
        node_run.node_run_id
    )
    events = store.list_runtime_events()
    assert exit_code == 0
    assert node_run.status == "SUCCEEDED"
    assert node_run.last_heartbeat is not None
    assert node_run.progress is None
    assert node_run.current_stage is None
    assert result is not None
    assert result.output_refs == ["source-output"]
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FINISHED",
    ]


def test_workflow_process_records_task_events_while_executor_is_still_running(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Streaming executor workflow",
        definition=single_node_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    progress_reported = Event()
    finish_task = Event()
    exit_codes: list[int] = []

    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0,
                executor_factory=lambda _task: BlockingReportingExecutor(
                    progress_reported=progress_reported,
                    finish_task=finish_task,
                ),
            )
        )
    )
    worker.start()
    try:
        assert progress_reported.wait(timeout=5)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        live_process = store.get_workflow_process(process.process_id)

        assert node_run.status == "RUNNING"
        assert node_run.executor_id == "blocking-reporting-executor"
        assert node_run.last_heartbeat is not None
        assert node_run.progress == 0.25
        assert node_run.current_stage == "streaming"
        assert live_process is not None
        assert live_process.last_heartbeat_at is not None
        assert store.get_workflow_run(run.workflow_run_id).status == "RUNNING"
        assert exit_codes == []
    finally:
        finish_task.set()
        worker.join(timeout=5)

    assert exit_codes == [0]
    assert store.get_workflow_run(run.workflow_run_id).status == "SUCCEEDED"


def test_workflow_process_times_out_task_while_executor_is_still_running(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Execution timeout workflow",
        definition={
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                    "config": {"timeout_seconds": 1},
                }
            ],
            "connections": [],
        },
        workflow_id="workflow-timeout",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-timeout",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-timeout",
    )
    assert process is not None
    executor = CloseableBlockingSuccessExecutor()
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0,
                executor_factory=lambda _task: executor,
            )
        )
    )
    worker.start()
    try:
        assert executor.started.wait(timeout=5)
        node_run = store.list_node_runs(run.workflow_run_id)[0]
        process_before = store.get_workflow_process(process.process_id)
        time.sleep(0.05)
        process_after = store.get_workflow_process(process.process_id)

        assert node_run.status == "RUNNING"
        assert node_run.last_heartbeat is not None
        assert node_run.progress == 0.1
        assert process_before is not None
        assert process_after is not None
        assert process_before.last_heartbeat_at is not None
        assert process_after.last_heartbeat_at is not None
        assert process_after.last_heartbeat_at > process_before.last_heartbeat_at

        worker.join(timeout=5)
    finally:
        if worker.is_alive():
            executor.close()
            worker.join(timeout=5)

    loaded_node = store.list_node_runs(run.workflow_run_id)[0]
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)
    loaded_process = store.get_workflow_process(process.process_id)
    events = store.list_runtime_events()
    assert exit_codes == [0]
    assert executor.closed.is_set()
    assert loaded_workflow is not None
    assert loaded_workflow.status == "FAILED"
    assert loaded_node.status == "TIMED_OUT"
    assert loaded_node.error is not None
    assert loaded_node.error["timeout_seconds"] == 1
    assert loaded_process is not None
    assert loaded_process.last_heartbeat_at is not None
    assert store.get_latest_succeeded_node_task_result_for_node_run(
        loaded_node.node_run_id
    ) is None
    terminal_event_types = [
        event.event_type
        for event in events
        if event.event_type in {"NODE_TIMEOUT", "WORKFLOW_FAILED"}
    ]
    assert terminal_event_types[-2:] == [
        "NODE_TIMEOUT",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_cancels_running_task_with_cancel_request(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Execution cancel workflow",
        definition=single_node_definition(),
        workflow_id="workflow-cancel",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-cancel",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-cancel",
    )
    assert process is not None
    executor = CloseableBlockingSuccessExecutor()
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0,
                cancel_grace_seconds=0.05,
                executor_factory=lambda _task: executor,
            )
        )
    )
    worker.start()
    try:
        assert executor.started.wait(timeout=5)
        store.request_workflow_process_cancel(run.workflow_run_id)
        worker.join(timeout=5)
    finally:
        if worker.is_alive():
            executor.close()
            worker.join(timeout=5)

    loaded_node = store.list_node_runs(run.workflow_run_id)[0]
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)
    events = store.list_runtime_events()
    assert exit_codes == [0]
    assert executor.cancel_requested.is_set()
    assert executor.cancelled_task_id is not None
    assert executor.cancel_reason == "WORKFLOW_CANCEL_REQUESTED"
    assert executor.closed.is_set()
    assert loaded_workflow is not None
    assert loaded_workflow.status == "CANCELLED"
    assert loaded_node.status == "CANCELLED"
    assert loaded_node.error == {
        "message": "Node task cancelled",
        "reason": "WORKFLOW_CANCEL_GRACE_EXPIRED",
    }
    assert store.get_latest_succeeded_node_task_result_for_node_run(
        loaded_node.node_run_id
    ) is None
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_PROGRESS",
        "WORKFLOW_CANCELLED",
    ]


def test_workflow_process_accepts_cooperative_cancel_before_grace_expires(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Cooperative execution cancel workflow",
        definition=single_node_definition(),
        workflow_id="workflow-cooperative-cancel",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-cooperative-cancel",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-cooperative-cancel",
    )
    assert process is not None
    executor = CooperativeCancelExecutor()
    exit_codes: list[int] = []
    worker = Thread(
        target=lambda: exit_codes.append(
            run_workflow_process(
                store=store,
                workflow_run_id=run.workflow_run_id,
                process_id=process.process_id,
                process_generation=process.process_generation,
                heartbeat_interval_seconds=0,
                cancel_grace_seconds=5,
                executor_factory=lambda _task: executor,
            )
        )
    )
    worker.start()
    try:
        assert executor.started.wait(timeout=5)
        store.request_workflow_process_cancel(run.workflow_run_id)
        worker.join(timeout=5)
    finally:
        if worker.is_alive():
            executor.close()
            worker.join(timeout=5)

    loaded_node = store.list_node_runs(run.workflow_run_id)[0]
    loaded_workflow = store.get_workflow_run(run.workflow_run_id)
    assert exit_codes == [0]
    assert executor.cancel_requested.is_set()
    assert executor.cancelled_task_id is not None
    assert loaded_workflow is not None
    assert loaded_workflow.status == "CANCELLED"
    assert loaded_node.status == "CANCELLED"
    assert loaded_node.error == {
        "message": "Node task cancelled cooperatively",
        "reason": "WORKFLOW_CANCEL_REQUESTED",
    }


def test_workflow_process_cleans_staging_refs_when_task_times_out(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    provider = SQLiteRuntimeTableProvider(tmp_path / "runtime" / "workflow_runs")
    registry = RuntimeDataRegistry(store=store, table_provider=provider)
    workflow = store.create_workflow_definition(
        name="Timeout cleanup workflow",
        definition={
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                    "config": {"timeout_seconds": 1},
                }
            ],
            "connections": [],
        },
        workflow_id="workflow-timeout-cleanup",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-timeout-cleanup",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-timeout-cleanup",
    )
    assert process is not None
    executor = BlockingStagingExecutor(
        registry=registry,
        table_provider=provider,
    )

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
        cleanup_staging_for_node=lambda workflow_run_id, node_run_id: (
            registry.cleanup_staging_for_node(
                workflow_run_id=workflow_run_id,
                node_run_id=node_run_id,
            )
        ),
    )

    assert exit_code == 0
    assert executor.started.is_set()
    assert executor.closed.is_set()
    node_run = store.list_node_runs(run.workflow_run_id)[0]
    assert node_run.status == "TIMED_OUT"
    assert executor.staging_ref_ids
    cleaned_ref = registry.get(executor.staging_ref_ids[0])
    assert cleaned_ref.lifecycle_status == LifecycleStatus.RELEASED
    with pytest.raises(sqlite3.OperationalError):
        provider.count_rows(cleaned_ref)


def test_workflow_process_applies_injected_executor_failure_result(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Injected executor workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: InjectedFailingExecutor(),
    )

    assert exit_code == 0
    assert store.get_workflow_run(run.workflow_run_id).status == "FAILED"
    assert {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    } == {"source": "FAILED", "transform": "WAITING_DEPENDENCY"}
    assert [event.event_type for event in store.list_runtime_events()] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "WORKFLOW_FAILED",
    ]


def test_workflow_process_continue_independent_fails_after_unrelated_ready_node(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    definition_data = multi_upstream_definition() | {
        "failure_policy": {"mode": "CONTINUE_INDEPENDENT"}
    }
    workflow = store.create_workflow_definition(
        name="Continue independent workflow",
        definition=definition_data,
        workflow_id="workflow-continue-independent",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-continue-independent",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-continue-independent",
    )
    assert process is not None
    executor = NodeOutcomeExecutor(failed_nodes={"source_b"})

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: executor,
    )

    events = store.list_runtime_events()
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    node_statuses = {
        node.node_instance_id: node.status
        for node in store.list_node_runs(run.workflow_run_id)
    }
    assert exit_code == 0
    assert executor.executed_nodes == ["source_b", "source_a"]
    assert loaded_run is not None
    assert loaded_run.status == "FAILED"
    assert loaded_run.completion_reason == "PARTIAL_FAILURE"
    assert node_statuses == {
        "source_a": "SUCCEEDED",
        "source_b": "FAILED",
        "merge": "SKIPPED",
    }
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FAILED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "NODE_FINISHED",
        "WORKFLOW_FAILED",
    ]
    assert events[-1].payload["completion_reason"] == "PARTIAL_FAILURE"
    assert events[-1].payload["failed_node_instance_ids"] == ["source_b"]
    assert events[-1].payload["skipped_node_instance_ids"] == ["merge"]


def test_workflow_process_rejects_reserved_skip_dependents_policy(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Reserved failure policy workflow",
        definition=single_node_definition()
        | {"failure_policy": {"mode": "SKIP_DEPENDENTS"}},
        workflow_id="workflow-reserved-failure-policy",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-reserved-failure-policy",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-reserved-failure-policy",
    )
    assert process is not None

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: RecordingSuccessExecutor(),
    )

    loaded_run = store.get_workflow_run(run.workflow_run_id)
    assert exit_code == 1
    assert loaded_run is not None
    assert loaded_run.status == "FAILED"
    assert loaded_run.error is not None
    assert (
        loaded_run.error["message"]
        == "SKIP_DEPENDENTS failure policy is reserved and not available yet"
    )
    assert store.list_node_runs(run.workflow_run_id) == []
    assert store.list_runtime_events() == []


def test_workflow_process_ignores_stale_executor_result_without_failing(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="Rejected executor result workflow",
        definition=definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    sleep_calls = 0

    def stop_after_ignored_result(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        store.request_workflow_process_cancel(run.workflow_run_id)

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        executor_factory=lambda _task: FakeNodeExecutor(
            result_id="stale-generation-result",
            process_generation=0,
        ),
        sleep_func=stop_after_ignored_result,
    )

    events = store.list_runtime_events()
    queued_event = next(event for event in events if event.event_type == "NODE_QUEUED")
    loaded_run = store.get_workflow_run(run.workflow_run_id)
    node_runs = {
        node.node_instance_id: node
        for node in store.list_node_runs(run.workflow_run_id)
    }

    assert exit_code == 0
    assert sleep_calls == 1
    assert loaded_run is not None
    assert loaded_run.status == "CANCELLED"
    assert loaded_run.error is None
    assert node_runs["source"].status == "RUNNING"
    assert node_runs["source"].error is None
    assert node_runs["transform"].status == "WAITING_DEPENDENCY"
    assert store.get_node_task_result(
        task_id=queued_event.payload["task_id"],
        result_id="stale-generation-result",
    ) is None
    assert [event.event_type for event in events] == [
        "WORKFLOW_STARTED",
        "NODE_QUEUED",
        "NODE_STARTED",
        "WORKFLOW_CANCELLED",
    ]


def test_workflow_process_ipc_event_sink_does_not_write_runtime_events(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="IPC event workflow",
        definition=empty_definition(),
        workflow_id="workflow-1",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-1",
    )
    process = store.claim_workflow_process(
        workflow_run_id=run.workflow_run_id,
        process_id="process-1",
    )
    assert process is not None
    event_path = tmp_path / "runtime-events.jsonl"

    exit_code = run_workflow_process(
        store=store,
        workflow_run_id=run.workflow_run_id,
        process_id=process.process_id,
        process_generation=process.process_generation,
        heartbeat_interval_seconds=0,
        event_sink=IPCEventSink(event_path),
    )

    envelopes = [
        IPCEnvelope.model_validate_json(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
    ]
    assert exit_code == 0
    assert store.list_runtime_events() == []
    assert [envelope.message_type for envelope in envelopes] == [
        IPCMessageType.RUNTIME_EVENT,
        IPCMessageType.RUNTIME_EVENT,
    ]
    assert [envelope.payload["event_type"] for envelope in envelopes] == [
        "WORKFLOW_STARTED",
        "WORKFLOW_FINISHED",
    ]
