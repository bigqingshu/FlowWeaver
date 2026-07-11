from __future__ import annotations

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_feedback_policy import (
    RuntimeFeedbackPolicyProvider,
)
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
    build_static_runtime_feedback_policy_provider,
    resolve_runtime_options_by_node,
    resolve_workflow_runtime_options,
)


def configure_runtime_options_event_sink(
    *,
    definition: WorkflowDefinitionModel,
    event_sink: RuntimeEventSink,
) -> tuple[RuntimeFeedbackPolicyProvider, RuntimeEventSink]:
    runtime_options_by_node = resolve_runtime_options_by_node(definition)
    policy_provider = build_static_runtime_feedback_policy_provider(definition)
    configured_event_sink = RuntimeOptionsEventSink(
        event_sink,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node=runtime_options_by_node,
    )
    return policy_provider, configured_event_sink
