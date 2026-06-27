from __future__ import annotations

import argparse
import time
import traceback
from collections.abc import Callable
from typing import NoReturn

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.controller import (
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import build_workflow_dag

_TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowRunStatus.SUCCEEDED.value,
        WorkflowRunStatus.FAILED.value,
        WorkflowRunStatus.CANCELLED.value,
        WorkflowRunStatus.ABORTED.value,
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--process-id", required=True)
    parser.add_argument("--process-generation", type=int, required=True)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=2.0)
    args = parser.parse_args(argv)
    store = RuntimeStore(args.database_url)
    try:
        return run_workflow_process(
            store=store,
            workflow_run_id=args.workflow_run_id,
            process_id=args.process_id,
            process_generation=args.process_generation,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        )
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        store.dispose()


def run_workflow_process(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    heartbeat_interval_seconds: float,
    process_generation: int | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
) -> int:
    if (
        process_generation is not None
        and not store.workflow_run_is_owned_by(
            workflow_run_id=workflow_run_id,
            process_id=process_id,
            process_generation=process_generation,
        )
    ):
        return 1
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.revision_id is None:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            "Workflow run not found",
            process_generation=process_generation,
        )
    revision = store.get_workflow_revision(run.revision_id)
    if revision is None:
        return _fail(
            store,
            workflow_run_id,
            process_id,
            "Workflow revision not found",
            process_generation=process_generation,
        )

    store.record_workflow_process_heartbeat(
        process_id,
        process_generation=process_generation,
    )
    current_run = store.get_workflow_run(workflow_run_id)
    if (
        current_run is not None
        and current_run.status == WorkflowRunStatus.PENDING.value
    ):
        store.update_workflow_run_status(
            workflow_run_id,
            WorkflowRunStatus.RUNNING,
            expected_state_version=current_run.state_version,
            allowed_source_statuses=[WorkflowRunStatus.PENDING],
            owner_process_id=process_id if process_generation is not None else None,
            process_generation=process_generation,
        )
    store.append_runtime_event(
        EventModel(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id},
        )
    )

    definition = WorkflowDefinitionModel.model_validate(revision.definition)
    dag = build_workflow_dag(definition)
    if not dag.nodes:
        return _complete_empty_workflow(
            store,
            workflow_run_id,
            process_id,
            process_generation=process_generation,
        )
    initialize_node_runs(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    recover_ready_nodes(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )

    while True:
        heartbeat = store.record_workflow_process_heartbeat(
            process_id,
            process_generation=process_generation,
        )
        if heartbeat is None:
            return 1
        process = store.get_workflow_process(process_id)
        if process is not None and process.cancel_requested_at is not None:
            store.update_workflow_run_status(
                workflow_run_id,
                WorkflowRunStatus.CANCELLED,
                finished_at=utc_now(),
                allowed_source_statuses=[WorkflowRunStatus.RUNNING],
                owner_process_id=process_id if process_generation is not None else None,
                process_generation=process_generation,
            )
            store.append_runtime_event(
                EventModel(
                    event_type=EventType.WORKFLOW_CANCELLED,
                    workflow_run_id=workflow_run_id,
                    payload={"process_id": process_id},
                )
            )
            return 0
        if _workflow_run_is_terminal(store, workflow_run_id):
            return 0
        sleep_func(heartbeat_interval_seconds)


def _workflow_run_is_terminal(
    store: RuntimeStore,
    workflow_run_id: str,
) -> bool:
    current = store.get_workflow_run(workflow_run_id)
    return current is not None and current.status in _TERMINAL_WORKFLOW_STATUSES


def _complete_empty_workflow(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None = None,
) -> int:
    current = store.get_workflow_run(workflow_run_id)
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=current.state_version if current is not None else None,
        allowed_source_statuses=[WorkflowRunStatus.RUNNING],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    store.append_runtime_event(
        EventModel(
            event_type=EventType.WORKFLOW_FINISHED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id, "empty_workflow": True},
        )
    )
    return 0


def _fail(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    message: str,
    process_generation: int | None = None,
) -> int:
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        error={"message": message},
        allowed_source_statuses=[
            WorkflowRunStatus.PENDING,
            WorkflowRunStatus.RUNNING,
        ],
        owner_process_id=process_id if process_generation is not None else None,
        process_generation=process_generation,
    )
    return 1


def _exit() -> NoReturn:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
