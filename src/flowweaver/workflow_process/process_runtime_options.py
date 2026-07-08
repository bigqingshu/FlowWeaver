from __future__ import annotations

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.workflow.definition import (
    RuntimeOptionsWorkflowModel,
    WorkflowDefinitionModel,
)
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
    resolve_runtime_options_by_node,
    resolve_workflow_runtime_options,
)


def configure_runtime_options_event_sink(
    *,
    definition: WorkflowDefinitionModel,
    event_sink: RuntimeEventSink,
) -> tuple[dict[str, RuntimeOptionsWorkflowModel], RuntimeEventSink]:
    runtime_options_by_node = resolve_runtime_options_by_node(definition)
    return runtime_options_by_node, RuntimeOptionsEventSink(
        event_sink,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node=runtime_options_by_node,
    )
