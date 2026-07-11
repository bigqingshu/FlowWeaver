from __future__ import annotations

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
)
from flowweaver.workflow_process import runtime_options_controller
from flowweaver.workflow_process.runtime_options_controller import (
    ResolvedRuntimeOptionsController,
    WorkflowRunRuntimeOptionsPoller,
)


def configure_runtime_options_event_sink(
    *,
    definition: WorkflowDefinitionModel,
    event_sink: RuntimeEventSink,
    store: RuntimeStore,
    workflow_run_id: str,
    process_id: str,
) -> tuple[
    ResolvedRuntimeOptionsController,
    RuntimeEventSink,
    WorkflowRunRuntimeOptionsPoller,
]:
    versions = store.get_workflow_run_runtime_options_versions(workflow_run_id)
    if versions is None:
        raise ValueError(f"Workflow run not found: {workflow_run_id}")
    initial_load_failure: tuple[int, Exception] | None = None
    try:
        state = store.get_workflow_run_runtime_options(workflow_run_id)
    except ValueError as exc:
        state = None
        initial_load_failure = (versions[0], exc)
    controller = ResolvedRuntimeOptionsController(
        definition=definition,
        overlay=state.overlay if state is not None else None,
        version=state.requested_version if state is not None else 0,
        acknowledged_version=state.applied_version if state is not None else 0,
    )
    configured_event_sink = RuntimeOptionsEventSink(
        event_sink,
        policy_provider=controller,
    )
    poller = WorkflowRunRuntimeOptionsPoller(
        store=store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        controller=controller,
        event_sink=configured_event_sink,
        interval_seconds=(
            runtime_options_controller.RUNTIME_OPTIONS_POLL_INTERVAL_SECONDS
        ),
        initial_load_failure=initial_load_failure,
    )
    return controller, configured_event_sink, poller
