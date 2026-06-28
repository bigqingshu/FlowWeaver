from __future__ import annotations

from threading import Event, Lock


class CancelToken:
    def __init__(self) -> None:
        self._cancelled = Event()
        self._reason_lock = Lock()
        self._reason: str | None = None

    def request_cancel(
        self,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> None:
        with self._reason_lock:
            if self._reason is None:
                self._reason = reason
        self._cancelled.set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def reason(self) -> str | None:
        with self._reason_lock:
            return self._reason


class NodeExecutionCancelled(RuntimeError):
    pass


class NodeExecutionContext:
    def __init__(self, cancel_token: CancelToken) -> None:
        self._cancel_token = cancel_token

    def is_cancelled(self) -> bool:
        return self._cancel_token.is_cancelled()

    def check_cancelled(self) -> None:
        if self.is_cancelled():
            reason = self._cancel_token.reason or "NODE_TASK_CANCEL_REQUEST"
            raise NodeExecutionCancelled(reason)
