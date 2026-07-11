from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel
from flowweaver.protocols.runtime_logs import (
    MAX_RUNTIME_LOG_MESSAGE_LENGTH,
    MAX_RUNTIME_LOGGER_NAME_LENGTH,
    WorkflowRuntimeLogPayloadModel,
    runtime_log_level_is_enabled,
)
from flowweaver.workflow.runtime_feedback_policy import (
    RuntimeFeedbackPolicyProvider,
)


class WorkflowRuntimeLogger:
    def __init__(
        self,
        *,
        workflow_run_id: str,
        process_id: str,
        logger_name: str,
        policy_provider: RuntimeFeedbackPolicyProvider,
        event_sink: RuntimeEventSink,
    ) -> None:
        self._workflow_run_id = workflow_run_id
        self._process_id = process_id
        self._logger_name = logger_name[:MAX_RUNTIME_LOGGER_NAME_LENGTH]
        self._policy_provider = policy_provider
        self._event_sink = event_sink

    def log(
        self,
        level: RuntimeFeedbackLogLevel,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> bool:
        policy = self._policy_provider.workflow_policy()
        if not runtime_log_level_is_enabled(
            configured_level=policy.telemetry.log_level,
            message_level=level,
        ):
            return False
        payload = WorkflowRuntimeLogPayloadModel(
            level=level,
            message=str(message)[:MAX_RUNTIME_LOG_MESSAGE_LENGTH],
            logger_name=self._logger_name,
            process_id=self._process_id,
            context=dict(context or {}),
        )
        self._event_sink.emit(
            EventModel(
                event_type=EventType.WORKFLOW_LOG,
                workflow_run_id=self._workflow_run_id,
                payload=payload.model_dump(mode="json"),
            )
        )
        return True

    def debug(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("DEBUG", message, context=context)

    def info(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("INFO", message, context=context)

    def warn(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("WARN", message, context=context)

    def error(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("ERROR", message, context=context)
