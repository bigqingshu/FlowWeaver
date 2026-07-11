from __future__ import annotations

import pytest
from pydantic import ValidationError

from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.runtime_feedback import (
    RuntimeFeedbackPolicyOverrideModel,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
    resolve_runtime_options_by_node,
    resolve_runtime_options_for_node,
    resolve_workflow_runtime_options,
    runtime_feedback_policy_from_options,
)
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.node_tasks import NodeTaskManager


class CollectingEventSink:
    def __init__(self) -> None:
        self.events: list[EventModel] = []

    def emit(self, event: EventModel) -> None:
        self.events.append(event)


def test_resolve_runtime_options_uses_current_compatible_defaults() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
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
    )

    resolved = resolve_runtime_options_for_node(definition, "source")

    assert resolved.profile == "normal"
    assert resolved.telemetry.log_level == "INFO"
    assert resolved.telemetry.event_level == "progress"
    assert resolved.telemetry.progress_enabled is True
    assert resolved.diagnostics.include_metrics is True


def test_resolve_runtime_options_applies_profile_presets() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "diagnose",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "profile": "background_fast",
                },
                "node_overrides": {
                    "diagnose": {
                        "profile": "diagnostic",
                        "telemetry": {
                            "event_rate_limit_per_second": 2,
                        },
                    }
                },
            },
        }
    )

    workflow = resolve_workflow_runtime_options(definition)
    source = resolve_runtime_options_for_node(definition, "source")
    diagnose = resolve_runtime_options_for_node(definition, "diagnose")

    assert workflow.profile == "background_fast"
    assert workflow.telemetry.log_level == "WARN"
    assert workflow.telemetry.event_level == "basic"
    assert workflow.telemetry.event_rate_limit_per_second == 10
    assert workflow.telemetry.progress_enabled is False
    assert workflow.telemetry.progress_interval_seconds == 5
    assert workflow.diagnostics.include_metrics is False
    assert workflow.diagnostics.payload_byte_limit == 65536
    assert workflow.diagnostics.ttl_seconds == 604800
    assert workflow.diagnostics.mask_policy == "partial"
    assert source == workflow
    assert diagnose.profile == "diagnostic"
    assert diagnose.telemetry.log_level == "DEBUG"
    assert diagnose.telemetry.event_level == "verbose"
    assert diagnose.telemetry.event_rate_limit_per_second == 2
    assert diagnose.telemetry.progress_enabled is True
    assert diagnose.diagnostics.include_metrics is True
    assert diagnose.diagnostics.payload_byte_limit == 262144
    assert diagnose.diagnostics.ttl_seconds == 86400


def test_resolve_runtime_options_merges_workflow_and_node_override() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "filter",
                    "node_type": "core.filter",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "version": "1.0",
                "workflow": {
                    "profile": "custom",
                    "telemetry": {
                        "log_level": "WARN",
                        "event_level": "basic",
                        "progress_enabled": False,
                    },
                    "diagnostics": {
                        "include_metrics": False,
                        "redact_columns": ["password"],
                        "mask_policy": "partial",
                    },
                },
                "node_overrides": {
                    "filter": {
                        "telemetry": {
                            "log_level": "DEBUG",
                            "event_level": "verbose",
                        },
                        "diagnostics": {
                            "include_metrics": True,
                        },
                    }
                },
            },
        }
    )

    source = resolve_runtime_options_for_node(definition, "source")
    filter_node = resolve_runtime_options_for_node(definition, "filter")

    assert source.profile == "custom"
    assert source.telemetry.log_level == "WARN"
    assert source.telemetry.event_level == "basic"
    assert source.telemetry.progress_enabled is False
    assert source.diagnostics.include_metrics is False
    assert source.diagnostics.redact_columns == ["password"]
    assert source.diagnostics.mask_policy == "partial"
    assert filter_node.profile == "custom"
    assert filter_node.telemetry.log_level == "DEBUG"
    assert filter_node.telemetry.event_level == "verbose"
    assert filter_node.telemetry.progress_enabled is False
    assert filter_node.diagnostics.include_metrics is True
    assert filter_node.diagnostics.redact_columns == ["password"]


def test_runtime_feedback_policy_maps_only_closed_feedback_fields() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "profile": "custom",
                    "strict_validation": False,
                    "telemetry": {
                        "log_level": "WARN",
                        "event_level": "basic",
                        "event_rate_limit_per_second": 3,
                        "progress_enabled": False,
                        "progress_interval_seconds": 2.5,
                    },
                    "diagnostics": {
                        "capture_error_context": False,
                        "include_metrics": False,
                        "payload_byte_limit": 512,
                        "ttl_seconds": 120,
                        "redact_columns": ["password"],
                        "mask_policy": "full",
                    },
                }
            },
        }
    )

    policy = runtime_feedback_policy_from_options(
        resolve_workflow_runtime_options(definition)
    )

    assert policy.model_dump(mode="json") == {
        "telemetry": {
            "log_level": "WARN",
            "event_level": "basic",
            "event_rate_limit_per_second": 3,
            "progress_enabled": False,
            "progress_interval_seconds": 2.5,
        },
        "diagnostics": {
            "capture_error_context": False,
            "include_metrics": False,
            "payload_byte_limit": 512,
            "redact_columns": ["password"],
            "mask_policy": "full",
        },
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"profile": "diagnostic"},
        {"strict_validation": False},
        {"diagnostics": {"ttl_seconds": 30}},
        {"extra": {"plugin": True}},
    ],
)
def test_runtime_feedback_policy_override_rejects_unmanaged_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        RuntimeFeedbackPolicyOverrideModel.model_validate(payload)


def test_resolver_does_not_mutate_node_config_or_task_protocol() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                    "config": {"rows": 3},
                }
            ],
            "connections": [],
            "runtime_options": {
                "node_overrides": {
                    "source": {
                        "telemetry": {
                            "event_level": "verbose",
                        }
                    }
                }
            },
        }
    )

    resolved_by_node = resolve_runtime_options_by_node(definition)
    manager = NodeTaskManager(
        store=object(),
        event_sink=object(),
        dag=build_workflow_dag(definition),
        runtime_options_by_node=resolved_by_node,
    )

    assert definition.nodes[0].config == {"rows": 3}
    assert "__runtime" not in definition.nodes[0].config
    assert "runtime_options" not in definition.nodes[0].config
    assert manager.runtime_options_for_node("source") is resolved_by_node["source"]
    assert manager.runtime_options_for_node("missing") is None


def test_runtime_options_event_sink_filters_node_progress_when_disabled() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                }
            ],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {
                        "event_level": "verbose",
                        "progress_enabled": True,
                    }
                },
                "node_overrides": {
                    "source": {
                        "telemetry": {
                            "progress_enabled": False,
                        }
                    }
                },
            },
        }
    )
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node=resolve_runtime_options_by_node(definition),
    )

    sink.emit(
        EventModel(
            event_type=EventType.NODE_PROGRESS,
            workflow_run_id="run-1",
            node_run_id="node-run-1",
            payload={"node_instance_id": "source", "progress": 0.5},
        )
    )
    sink.emit(
        EventModel(
            event_type=EventType.NODE_FINISHED,
            workflow_run_id="run-1",
            node_run_id="node-run-1",
            payload={"node_instance_id": "source"},
        )
    )

    assert [event.event_type for event in collector.events] == [
        EventType.NODE_FINISHED
    ]


def test_runtime_options_event_sink_keeps_nonprogress_events_by_default() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
        }
    )
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node={},
    )

    sink.emit(
        EventModel(
            event_type=EventType.DATA_STAGED,
            workflow_run_id="run-1",
            payload={"node_instance_id": "source"},
        )
    )

    assert [event.event_type for event in collector.events] == [EventType.DATA_STAGED]


def test_runtime_options_event_sink_sanitizes_metrics_and_redacted_columns() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {
                        "event_level": "verbose",
                    },
                    "diagnostics": {
                        "include_metrics": False,
                        "redact_columns": ["password"],
                        "mask_policy": "full",
                    },
                }
            },
        }
    )
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node={},
    )

    sink.emit(
        EventModel(
            event_type=EventType.NODE_PROGRESS,
            workflow_run_id="run-1",
            payload={
                "node_instance_id": "source",
                "metrics": {"rows": 10},
                "row": {"password": "secret", "amount": 12},
            },
        )
    )

    assert collector.events[0].payload == {
        "node_instance_id": "source",
        "row": {"password": "***", "amount": 12},
    }


def test_runtime_options_event_sink_limits_payload_size() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {
                        "event_level": "verbose",
                    },
                    "diagnostics": {
                        "payload_byte_limit": 80,
                    },
                }
            },
        }
    )
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node={},
    )

    sink.emit(
        EventModel(
            event_type=EventType.NODE_PROGRESS,
            workflow_run_id="run-1",
            payload={
                "node_instance_id": "source",
                "task_id": "task-1",
                "details": "x" * 500,
            },
        )
    )

    assert collector.events[0].payload["node_instance_id"] == "source"
    assert collector.events[0].payload["task_id"] == "task-1"
    assert collector.events[0].payload["_runtime_options_payload_truncated"] is True
    assert "details" not in collector.events[0].payload


def test_runtime_options_event_sink_rate_limits_noncritical_events() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {
                        "event_level": "verbose",
                        "event_rate_limit_per_second": 1,
                    }
                }
            },
        }
    )
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node={},
        monotonic_time=lambda: 10.2,
    )

    event = EventModel(
        event_type=EventType.DATA_STAGED,
        workflow_run_id="run-1",
        payload={"node_instance_id": "source"},
    )
    sink.emit(event)
    sink.emit(event)
    sink.emit(
        EventModel(
            event_type=EventType.NODE_FAILED,
            workflow_run_id="run-1",
            payload={"node_instance_id": "source"},
        )
    )

    assert [event.event_type for event in collector.events] == [
        EventType.DATA_STAGED,
        EventType.NODE_FAILED,
    ]
