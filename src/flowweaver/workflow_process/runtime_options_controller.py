from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock
from typing import Protocol

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_models import WorkflowRunRuntimeOptions
from flowweaver.protocols.enums import EventType
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
    RuntimeFeedbackPolicyOverlayModel,
)
from flowweaver.workflow.definition import WorkflowDefinitionModel
from flowweaver.workflow.runtime_feedback_policy import (
    StaticRuntimeFeedbackPolicyProvider,
)
from flowweaver.workflow.runtime_options import (
    build_runtime_feedback_policy_provider,
)

RUNTIME_OPTIONS_POLL_INTERVAL_SECONDS = 2.0


class WorkflowRunRuntimeOptionsStore(Protocol):
    def get_workflow_run_runtime_options_versions(
        self,
        workflow_run_id: str,
    ) -> tuple[int, int] | None:
        ...

    def get_workflow_run_runtime_options(
        self,
        workflow_run_id: str,
    ) -> WorkflowRunRuntimeOptions | None:
        ...

    def mark_workflow_run_runtime_options_applied(
        self,
        workflow_run_id: str,
        *,
        version: int,
    ) -> WorkflowRunRuntimeOptions | None:
        ...


class ResolvedRuntimeOptionsController:
    def __init__(
        self,
        *,
        definition: WorkflowDefinitionModel,
        overlay: RuntimeFeedbackPolicyOverlayModel | None = None,
        version: int = 0,
        acknowledged_version: int = 0,
    ) -> None:
        if version < 0:
            raise ValueError("runtime options version must be non-negative")
        if acknowledged_version < 0 or acknowledged_version > version:
            raise ValueError("acknowledged version must be between zero and version")
        self._definition = definition.model_copy(deep=True)
        initial_overlay = overlay or RuntimeFeedbackPolicyOverlayModel()
        self._provider = self._build_provider(initial_overlay, version)
        self._version = version
        self._acknowledged_version = acknowledged_version
        self._lock = Lock()

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def acknowledged_version(self) -> int:
        with self._lock:
            return self._acknowledged_version

    def workflow_policy(self) -> ResolvedRuntimeFeedbackPolicyModel:
        with self._lock:
            provider = self._provider
        return provider.workflow_policy()

    def policy_for_node(
        self,
        node_instance_id: str,
    ) -> ResolvedRuntimeFeedbackPolicyModel:
        return self.policy_snapshot_for_node(node_instance_id)[1]

    def policy_snapshot_for_node(
        self,
        node_instance_id: str,
    ) -> tuple[int, ResolvedRuntimeFeedbackPolicyModel]:
        with self._lock:
            provider = self._provider
            version = self._version
        return version, provider.policy_for_node(node_instance_id)

    def replace_overlay(
        self,
        *,
        overlay: RuntimeFeedbackPolicyOverlayModel,
        version: int,
    ) -> bool:
        if version < 0:
            raise ValueError("runtime options version must be non-negative")
        with self._lock:
            if version <= self._version:
                return False
        provider = self._build_provider(overlay, version)
        with self._lock:
            if version <= self._version:
                return False
            self._provider = provider
            self._version = version
            return True

    def mark_acknowledged(self, version: int) -> None:
        with self._lock:
            if version > self._version:
                raise ValueError(
                    "cannot acknowledge an unapplied runtime options version"
                )
            if version > self._acknowledged_version:
                self._acknowledged_version = version

    def _build_provider(
        self,
        overlay: RuntimeFeedbackPolicyOverlayModel,
        version: int,
    ) -> StaticRuntimeFeedbackPolicyProvider:
        return build_runtime_feedback_policy_provider(
            self._definition,
            overlay=overlay,
            version=version,
        )


class WorkflowRunRuntimeOptionsPoller:
    def __init__(
        self,
        *,
        store: WorkflowRunRuntimeOptionsStore,
        workflow_run_id: str,
        process_id: str,
        controller: ResolvedRuntimeOptionsController,
        event_sink: RuntimeEventSink,
        interval_seconds: float = RUNTIME_OPTIONS_POLL_INTERVAL_SECONDS,
        monotonic_time: Callable[[], float] | None = None,
        initial_load_failure: tuple[int, Exception] | None = None,
    ) -> None:
        if interval_seconds < 0:
            raise ValueError("runtime options poll interval must be non-negative")
        self._store = store
        self._workflow_run_id = workflow_run_id
        self._process_id = process_id
        self._controller = controller
        self._event_sink = event_sink
        self._interval_seconds = interval_seconds
        self._monotonic_time = monotonic_time or time.monotonic
        self._next_poll_at = self._monotonic_time() + interval_seconds
        self._last_failure_key: tuple[int, str, str] | None = None
        self._initial_load_failure = initial_load_failure

    def acknowledge_loaded_version(self) -> bool:
        if self._initial_load_failure is not None:
            requested_version, exc = self._initial_load_failure
            self._initial_load_failure = None
            self._emit_apply_failed(requested_version, exc)
            return False
        return self._acknowledge_controller_version()

    def poll_if_due(self) -> bool:
        now = self._monotonic_time()
        if now < self._next_poll_at:
            return False
        self._next_poll_at = now + self._interval_seconds
        requested_version = self._controller.version
        try:
            versions = self._store.get_workflow_run_runtime_options_versions(
                self._workflow_run_id
            )
            if versions is None:
                raise ValueError("Workflow run runtime options state not found")
            requested_version = versions[0]
            if requested_version <= self._controller.version:
                return self._acknowledge_controller_version()
            state = self._store.get_workflow_run_runtime_options(
                self._workflow_run_id
            )
            if state is None:
                raise ValueError("Workflow run runtime options state not found")
            previous_version = self._controller.version
            self._controller.replace_overlay(
                overlay=state.overlay,
                version=state.requested_version,
            )
            acknowledged = self._acknowledge_controller_version(
                previous_version=previous_version
            )
            if acknowledged:
                self._last_failure_key = None
            return acknowledged
        except Exception as exc:
            self._emit_apply_failed(requested_version, exc)
            return False

    def _acknowledge_controller_version(
        self,
        *,
        previous_version: int | None = None,
    ) -> bool:
        version = self._controller.version
        acknowledged_version = self._controller.acknowledged_version
        if version <= acknowledged_version:
            return False
        try:
            state = self._store.mark_workflow_run_runtime_options_applied(
                self._workflow_run_id,
                version=version,
            )
            if state is None:
                raise ValueError("Workflow run runtime options state not found")
            self._controller.mark_acknowledged(version)
            self._event_sink.emit(
                EventModel(
                    event_type=EventType.RUNTIME_OPTIONS_APPLIED,
                    workflow_run_id=self._workflow_run_id,
                    payload={
                        "process_id": self._process_id,
                        "previous_version": (
                            acknowledged_version
                            if previous_version is None
                            else previous_version
                        ),
                        "runtime_options_version": version,
                        "requested_version": state.requested_version,
                        "applied_version": version,
                    },
                )
            )
            self._last_failure_key = None
            return True
        except Exception as exc:
            self._emit_apply_failed(version, exc)
            return False

    def _emit_apply_failed(self, requested_version: int, exc: Exception) -> None:
        failure_key = (requested_version, type(exc).__name__, str(exc))
        if failure_key == self._last_failure_key:
            return
        self._last_failure_key = failure_key
        self._event_sink.emit(
            EventModel(
                event_type=EventType.RUNTIME_OPTIONS_APPLY_FAILED,
                workflow_run_id=self._workflow_run_id,
                payload={
                    "process_id": self._process_id,
                    "runtime_options_version": self._controller.version,
                    "requested_version": requested_version,
                    "error": {
                        "message": str(exc),
                        "error_type": type(exc).__name__,
                    },
                },
            )
        )
