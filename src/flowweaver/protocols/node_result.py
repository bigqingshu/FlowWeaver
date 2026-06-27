from __future__ import annotations

from typing import Any

from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus
from flowweaver.protocols.table_ref import TableRefModel


class ErrorModel(StrictModel):
    error_code: str
    message: str
    details: dict[str, Any] = {}
    retryable: bool = False
    origin: ErrorOrigin
    trace_id: str | None = None


class NodeResultModel(StrictModel):
    status: NodeResultStatus
    outputs: list[TableRefModel]
    affected_rows: int = 0
    skipped_rows: int = 0
    warnings: list[str] = []
    errors: list[ErrorModel] = []
    metrics: dict[str, int | float | str] = {}
    diagnostics: dict[str, Any] = {}
    change_set_summary: dict[str, Any] | None = None
    side_effect_summary: dict[str, Any] | None = None
