from __future__ import annotations

import argparse
import time
from typing import NoReturn

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import EventType, NodeRunStatus, WorkflowRunStatus
from flowweaver.protocols.events import EventModel
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow_process.dag import WorkflowDag, build_workflow_dag


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--process-id", required=True)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=2.0)
    args = parser.parse_args(argv)
    store = RuntimeStore(args.database_url)
    try:
        return run_workflow_process(
            store=store,
            workflow_run_id=args.workflow_run_id,
            process_id=args.process_id,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        )
    except Exception as exc:
        store.mark_workflow_process_exited(
            args.process_id,
            exit_code=1,
            error={"message": str(exc)},
        )
        return 1
    finally:
        store.dispose()


def run_workflow_process(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    heartbeat_interval_seconds: float,
) -> int:
    run = store.get_workflow_run(workflow_run_id)
    if run is None or run.revision_id is None:
        return _fail(store, workflow_run_id, process_id, "Workflow run not found")
    revision = store.get_workflow_revision(run.revision_id)
    if revision is None:
        return _fail(store, workflow_run_id, process_id, "Workflow revision not found")

    store.record_workflow_process_heartbeat(process_id)
    current_run = store.get_workflow_run(workflow_run_id)
    if (
        current_run is not None
        and current_run.status == WorkflowRunStatus.PENDING.value
    ):
        store.update_workflow_run_status(
            workflow_run_id,
            WorkflowRunStatus.RUNNING,
            expected_state_version=current_run.state_version,
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
        return _complete_empty_workflow(store, workflow_run_id, process_id)
    _initialize_node_runs(store, workflow_run_id, process_id, dag)

    while True:
        store.record_workflow_process_heartbeat(process_id)
        process = store.get_workflow_process(process_id)
        if process is not None and process.cancel_requested_at is not None:
            store.update_workflow_run_status(
                workflow_run_id,
                WorkflowRunStatus.CANCELLED,
                finished_at=utc_now(),
            )
            store.append_runtime_event(
                EventModel(
                    event_type=EventType.WORKFLOW_CANCELLED,
                    workflow_run_id=workflow_run_id,
                    payload={"process_id": process_id},
                )
            )
            store.mark_workflow_process_exited(process_id, exit_code=0)
            return 0
        time.sleep(heartbeat_interval_seconds)


def _complete_empty_workflow(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
) -> int:
    current = store.get_workflow_run(workflow_run_id)
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.SUCCEEDED,
        finished_at=utc_now(),
        expected_state_version=current.state_version if current is not None else None,
    )
    store.append_runtime_event(
        EventModel(
            event_type=EventType.WORKFLOW_FINISHED,
            workflow_run_id=workflow_run_id,
            payload={"process_id": process_id, "empty_workflow": True},
        )
    )
    store.mark_workflow_process_exited(process_id, exit_code=0)
    return 0


def _initialize_node_runs(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    dag: WorkflowDag,
) -> None:
    ready_node_ids = set(dag.ready_node_ids)
    for node in dag.nodes:
        existing = store.get_node_run_for_instance(
            workflow_run_id=workflow_run_id,
            node_instance_id=node.node_instance_id,
        )
        if existing is not None:
            continue
        status = (
            NodeRunStatus.READY
            if node.node_instance_id in ready_node_ids
            else NodeRunStatus.WAITING_DEPENDENCY
        )
        node_run = store.create_node_run(
            workflow_run_id=workflow_run_id,
            node_instance_id=node.node_instance_id,
            node_type=node.node_type,
            status=status,
        )
        if status == NodeRunStatus.READY:
            store.append_runtime_event(
                EventModel(
                    event_type=EventType.NODE_QUEUED,
                    workflow_run_id=workflow_run_id,
                    node_run_id=node_run.node_run_id,
                    payload={
                        "process_id": process_id,
                        "node_instance_id": node.node_instance_id,
                    },
                )
            )


def _fail(
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
    message: str,
) -> int:
    store.update_workflow_run_status(
        workflow_run_id,
        WorkflowRunStatus.FAILED,
        finished_at=utc_now(),
        error={"message": message},
    )
    store.mark_workflow_process_exited(
        process_id,
        exit_code=1,
        error={"message": message},
    )
    return 1


def _exit() -> NoReturn:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()
