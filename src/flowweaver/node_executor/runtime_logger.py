from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.runtime_feedback import RuntimeFeedbackLogLevel
from flowweaver.protocols.runtime_logs import (
    MAX_RUNTIME_LOG_MESSAGE_LENGTH,
    MAX_RUNTIME_LOGGER_NAME_LENGTH,
)

EmitNodeTaskLog = Callable[
    [NodeTaskModel, RuntimeFeedbackLogLevel, str, str, dict[str, Any]],
    bool,
]


class NodeTaskLogger:
    def __init__(
        self,
        *,
        task: NodeTaskModel,
        logger_name: str,
        emit_log: EmitNodeTaskLog,
    ) -> None:
        self._task = task
        self._logger_name = logger_name[:MAX_RUNTIME_LOGGER_NAME_LENGTH]
        self._emit_log = emit_log

    def log(
        self,
        level: RuntimeFeedbackLogLevel,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> bool:
        return self._emit_log(
            self._task,
            level,
            str(message)[:MAX_RUNTIME_LOG_MESSAGE_LENGTH],
            self._logger_name,
            dict(context or {}),
        )

    def debug(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("DEBUG", message, context=context)

    def info(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("INFO", message, context=context)

    def warn(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("WARN", message, context=context)

    def error(self, message: str, *, context: dict[str, Any] | None = None) -> bool:
        return self.log("ERROR", message, context=context)


@runtime_checkable
class NodeTaskRuntimeLoggerAware(Protocol):
    def set_runtime_logger(self, logger: NodeTaskLogger | None) -> None:
        ...
