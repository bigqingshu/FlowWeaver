from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from flowweaver.engine.runtime_models import WorkflowRunRuntimeOptions
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.runtime_feedback import (
    RuntimeFeedbackPolicyOverlayModel,
    RuntimeFeedbackPolicyOverrideModel,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_options import (
    RuntimeOptionsEventSink,
    build_runtime_feedback_policy_provider,
    build_static_runtime_feedback_policy_provider,
    resolve_runtime_options_by_node,
    resolve_runtime_options_for_node,
    resolve_workflow_runtime_options,
    runtime_feedback_policy_from_options,
)
from flowweaver.workflow_process.dag import build_workflow_dag
from flowweaver.workflow_process.node_tasks import NodeTaskManager
from flowweaver.workflow_process.runtime_logger import WorkflowRuntimeLogger
from flowweaver.workflow_process.runtime_options_controller import (
    ResolvedRuntimeOptionsController,
    WorkflowRunRuntimeOptionsPoller,
)


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


def test_run_overlay_applies_workflow_then_node_feedback_override() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "other",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "workflow": {"telemetry": {"log_level": "INFO"}},
                "node_overrides": {
                    "source": {"telemetry": {"log_level": "ERROR"}}
                },
            },
        }
    )
    overlay = RuntimeFeedbackPolicyOverlayModel.model_validate(
        {
            "workflow": {"telemetry": {"log_level": "WARN"}},
            "node_overrides": {
                "source": {"telemetry": {"log_level": "DEBUG"}}
            },
        }
    )

    provider = build_runtime_feedback_policy_provider(
        definition,
        overlay=overlay,
        version=4,
    )

    assert provider.version == 4
    assert provider.workflow_policy().telemetry.log_level == "WARN"
    assert provider.policy_for_node("source").telemetry.log_level == "DEBUG"
    assert provider.policy_for_node("other").telemetry.log_level == "WARN"


def test_runtime_options_controller_updates_event_sink_and_logger_atomically() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "other",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {"log_level": "WARN", "event_level": "none"}
                }
            },
        }
    )
    controller = ResolvedRuntimeOptionsController(definition=definition)
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(collector, policy_provider=controller)
    logger = WorkflowRuntimeLogger(
        workflow_run_id="run-controller",
        process_id="process-controller",
        logger_name="flowweaver.workflow_process.test",
        policy_provider=controller,
        event_sink=sink,
    )
    source_debug = _node_log_event(
        node_instance_id="source",
        level="DEBUG",
        message="source debug",
    )

    sink.emit(source_debug)
    assert logger.debug("hidden workflow debug") is False
    assert collector.events == []

    assert controller.replace_overlay(
        overlay=RuntimeFeedbackPolicyOverlayModel.model_validate(
            {
                "node_overrides": {
                    "source": {"telemetry": {"log_level": "DEBUG"}}
                }
            }
        ),
        version=1,
    )
    sink.emit(source_debug)
    sink.emit(
        _node_log_event(
            node_instance_id="other",
            level="INFO",
            message="hidden other info",
        )
    )
    assert controller.version == 1
    assert [event.payload["message"] for event in collector.events] == [
        "source debug"
    ]

    assert controller.replace_overlay(
        overlay=RuntimeFeedbackPolicyOverlayModel.model_validate(
            {"workflow": {"telemetry": {"log_level": "DEBUG"}}}
        ),
        version=2,
    )
    assert logger.debug("visible workflow debug") is True
    assert controller.replace_overlay(
        overlay=RuntimeFeedbackPolicyOverlayModel(),
        version=1,
    ) is False
    assert controller.version == 2


def test_runtime_options_poller_only_loads_changed_versions_and_keeps_last_valid(
) -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {"nodes": [], "connections": []}
    )
    controller = ResolvedRuntimeOptionsController(definition=definition)
    collector = CollectingEventSink()
    sink = RuntimeOptionsEventSink(collector, policy_provider=controller)
    now = [0.0]

    class FakeRuntimeOptionsStore:
        def __init__(self) -> None:
            self.state = WorkflowRunRuntimeOptions(
                workflow_run_id="run-poller",
                requested_version=0,
                applied_version=0,
                overlay=RuntimeFeedbackPolicyOverlayModel(),
                requested_at=None,
                applied_at=None,
            )
            self.version_reads = 0
            self.full_reads = 0
            self.raise_on_full_read = False

        def get_workflow_run_runtime_options_versions(
            self,
            _workflow_run_id: str,
        ) -> tuple[int, int]:
            self.version_reads += 1
            return self.state.requested_version, self.state.applied_version

        def get_workflow_run_runtime_options(
            self,
            _workflow_run_id: str,
        ) -> WorkflowRunRuntimeOptions:
            self.full_reads += 1
            if self.raise_on_full_read:
                raise ValueError("corrupt overlay")
            return self.state

        def mark_workflow_run_runtime_options_applied(
            self,
            _workflow_run_id: str,
            *,
            version: int,
        ) -> WorkflowRunRuntimeOptions:
            self.state = replace(self.state, applied_version=version)
            return self.state

    store = FakeRuntimeOptionsStore()
    poller = WorkflowRunRuntimeOptionsPoller(
        store=store,
        workflow_run_id="run-poller",
        process_id="process-poller",
        controller=controller,
        event_sink=sink,
        interval_seconds=2,
        monotonic_time=lambda: now[0],
    )

    now[0] = 1
    assert poller.poll_if_due() is False
    assert store.version_reads == 0
    now[0] = 2
    assert poller.poll_if_due() is False
    assert store.version_reads == 1
    assert store.full_reads == 0

    store.state = replace(
        store.state,
        requested_version=1,
        overlay=RuntimeFeedbackPolicyOverlayModel.model_validate(
            {"workflow": {"telemetry": {"log_level": "WARN"}}}
        ),
    )
    now[0] = 4
    assert poller.poll_if_due() is True
    assert controller.version == 1
    assert controller.acknowledged_version == 1
    assert store.full_reads == 1
    assert [event.event_type for event in collector.events] == [
        EventType.RUNTIME_OPTIONS_APPLIED
    ]

    now[0] = 6
    assert poller.poll_if_due() is False
    assert store.full_reads == 1
    store.state = replace(store.state, requested_version=2)
    store.raise_on_full_read = True
    now[0] = 8
    assert poller.poll_if_due() is False
    assert controller.version == 1
    assert collector.events[-1].event_type == EventType.RUNTIME_OPTIONS_APPLY_FAILED
    event_count = len(collector.events)
    now[0] = 10
    assert poller.poll_if_due() is False
    assert len(collector.events) == event_count


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
    provider = build_static_runtime_feedback_policy_provider(definition)
    manager = NodeTaskManager(
        store=object(),
        event_sink=object(),
        dag=build_workflow_dag(definition),
        runtime_feedback_policy_provider=provider,
    )

    assert definition.nodes[0].config == {"rows": 3}
    assert "__runtime" not in definition.nodes[0].config
    assert "runtime_options" not in definition.nodes[0].config
    source_policy = manager.runtime_feedback_policy_for_node("source")
    missing_policy = manager.runtime_feedback_policy_for_node("missing")
    assert source_policy == runtime_feedback_policy_from_options(
        resolved_by_node["source"]
    )
    assert missing_policy == provider.workflow_policy()


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


def test_runtime_options_event_sink_filters_workflow_and_node_log_levels() -> None:
    definition = WorkflowDefinitionModel.model_validate(
        {
            "nodes": [
                {
                    "node_instance_id": "source",
                    "node_type": "core.source",
                    "node_version": "1.0",
                },
                {
                    "node_instance_id": "other",
                    "node_type": "core.transform",
                    "node_version": "1.0",
                },
            ],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {
                        "log_level": "WARN",
                        "event_level": "none",
                    }
                },
                "node_overrides": {
                    "source": {"telemetry": {"log_level": "DEBUG"}}
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

    sink.emit(_workflow_log_event(level="INFO", message="hidden workflow info"))
    sink.emit(_workflow_log_event(level="WARN", message="visible workflow warning"))
    sink.emit(
        _node_log_event(
            node_instance_id="source",
            level="DEBUG",
            message="visible source debug",
        )
    )
    sink.emit(
        _node_log_event(
            node_instance_id="other",
            level="INFO",
            message="hidden other info",
        )
    )
    sink.emit(
        _node_log_event(
            node_instance_id="other",
            level="ERROR",
            message="visible other error",
        )
    )

    assert [event.payload["message"] for event in collector.events] == [
        "visible workflow warning",
        "visible source debug",
        "visible other error",
    ]


def test_runtime_options_event_sink_sanitizes_logs_and_keeps_error() -> None:
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
                        "log_level": "DEBUG",
                        "event_level": "none",
                        "event_rate_limit_per_second": 1,
                    },
                    "diagnostics": {
                        "include_metrics": False,
                        "payload_byte_limit": 120,
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
        runtime_options_by_node=resolve_runtime_options_by_node(definition),
        monotonic_time=lambda: 12.4,
    )

    sink.emit(
        _node_log_event(
            node_instance_id="source",
            level="INFO",
            message="large context",
            context={
                "rows": [{"password": "secret"}] * 20,
                "binary": b"raw-data",
                "metrics": {"row_count": 20},
                "password": "secret",
                "details": "x" * 500,
            },
        )
    )
    sink.emit(
        _node_log_event(
            node_instance_id="source",
            level="WARN",
            message="rate limited warning",
        )
    )
    sink.emit(
        _node_log_event(
            node_instance_id="source",
            level="ERROR",
            message="retained error",
            context={"error_code": "E_LOG", "rows": [{"secret": "value"}]},
        )
    )

    assert [event.payload["level"] for event in collector.events] == [
        "INFO",
        "ERROR",
    ]
    info_context = collector.events[0].payload["context"]
    assert info_context["_runtime_options_payload_truncated"] is True
    assert "rows" not in info_context
    assert "binary" not in info_context
    assert "metrics" not in info_context
    assert collector.events[1].payload == {
        "level": "ERROR",
        "message": "retained error",
        "logger_name": "flowweaver.nodes.test",
        "context": {"error_code": "E_LOG"},
        "node_instance_id": "source",
        "task_id": "task-source",
    }


def test_workflow_runtime_loggers_keep_run_levels_isolated() -> None:
    warn_definition = _definition_with_workflow_log_level("WARN")
    debug_definition = _definition_with_workflow_log_level("DEBUG")
    warn_collector = CollectingEventSink()
    debug_collector = CollectingEventSink()
    warn_logger = _workflow_runtime_logger(
        definition=warn_definition,
        workflow_run_id="run-warn",
        collector=warn_collector,
    )
    debug_logger = _workflow_runtime_logger(
        definition=debug_definition,
        workflow_run_id="run-debug",
        collector=debug_collector,
    )

    assert warn_logger.debug("hidden debug") is False
    assert debug_logger.debug("visible debug") is True
    assert warn_logger.error("visible error") is True

    assert [event.workflow_run_id for event in warn_collector.events] == ["run-warn"]
    assert [event.payload["level"] for event in warn_collector.events] == ["ERROR"]
    assert [event.workflow_run_id for event in debug_collector.events] == [
        "run-debug"
    ]
    assert [event.payload["level"] for event in debug_collector.events] == [
        "DEBUG"
    ]


def _workflow_log_event(*, level: str, message: str) -> EventModel:
    return EventModel(
        event_type=EventType.WORKFLOW_LOG,
        workflow_run_id="run-1",
        payload={
            "level": level,
            "message": message,
            "logger_name": "flowweaver.workflow_process",
            "process_id": "process-1",
            "context": {},
        },
    )


def _node_log_event(
    *,
    node_instance_id: str,
    level: str,
    message: str,
    context: dict[str, object] | None = None,
) -> EventModel:
    return EventModel(
        event_type=EventType.NODE_LOG,
        workflow_run_id="run-1",
        node_run_id=f"node-run-{node_instance_id}",
        payload={
            "level": level,
            "message": message,
            "logger_name": "flowweaver.nodes.test",
            "node_instance_id": node_instance_id,
            "task_id": f"task-{node_instance_id}",
            "context": context or {},
        },
    )


def _definition_with_workflow_log_level(level: str) -> WorkflowDefinitionModel:
    return WorkflowDefinitionModel.model_validate(
        {
            "nodes": [],
            "connections": [],
            "runtime_options": {
                "workflow": {
                    "telemetry": {"log_level": level, "event_level": "none"}
                }
            },
        }
    )


def _workflow_runtime_logger(
    *,
    definition: WorkflowDefinitionModel,
    workflow_run_id: str,
    collector: CollectingEventSink,
) -> WorkflowRuntimeLogger:
    sink = RuntimeOptionsEventSink(
        collector,
        workflow_options=resolve_workflow_runtime_options(definition),
        runtime_options_by_node={},
    )
    return WorkflowRuntimeLogger(
        workflow_run_id=workflow_run_id,
        process_id=f"process-{workflow_run_id}",
        logger_name="flowweaver.workflow_process.test",
        policy_provider=build_static_runtime_feedback_policy_provider(definition),
        event_sink=sink,
    )
