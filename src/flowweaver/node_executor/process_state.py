from __future__ import annotations

from threading import Lock

from flowweaver.node_executor.cancel_token import CancelToken, NodeExecutionContext


class NodeExecutorProcessState:
    def __init__(self) -> None:
        self._active_task_ids: set[str] = set()
        self._active_task_correlations: dict[str, str] = {}
        self._cancel_tokens: dict[str, CancelToken] = {}
        self._execution_contexts: dict[str, NodeExecutionContext] = {}
        self._lock = Lock()

    def active_task_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._active_task_ids)

    def begin_task(self, *, task_id: str, correlation_id: str) -> None:
        cancel_token = CancelToken()
        with self._lock:
            self._active_task_ids.add(task_id)
            self._active_task_correlations[task_id] = correlation_id
            self._cancel_tokens[task_id] = cancel_token
            self._execution_contexts[task_id] = NodeExecutionContext(cancel_token)

    def finish_task(self, task_id: str) -> None:
        with self._lock:
            self._active_task_ids.discard(task_id)
            self._active_task_correlations.pop(task_id, None)
            self._cancel_tokens.pop(task_id, None)
            self._execution_contexts.pop(task_id, None)

    def task_correlation_id(self, task_id: str) -> str | None:
        with self._lock:
            return self._active_task_correlations.get(task_id)

    def task_context(self, task_id: str) -> NodeExecutionContext | None:
        with self._lock:
            return self._execution_contexts.get(task_id)

    def request_cancel(self, *, task_id: str, reason: str) -> None:
        with self._lock:
            token = self._cancel_tokens.get(task_id)
        if token is not None:
            token.request_cancel(reason=reason)
