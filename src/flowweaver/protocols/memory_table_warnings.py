from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from flowweaver.protocols.base import StrictModel

MemoryTableSoftLimitWarningCode = Literal[
    "MEMORY_TABLE_ROW_SOFT_LIMIT_EXCEEDED"
]
MEMORY_TABLE_SOFT_LIMIT_WARNING_CODE: MemoryTableSoftLimitWarningCode = (
    "MEMORY_TABLE_ROW_SOFT_LIMIT_EXCEEDED"
)
MEMORY_TABLE_SOFT_LIMIT_WARNINGS_SUMMARY_KEY = (
    "memory_table_soft_limit_warnings"
)


class MemoryTableSoftLimitWarningModel(StrictModel):
    warning_code: MemoryTableSoftLimitWarningCode = (
        MEMORY_TABLE_SOFT_LIMIT_WARNING_CODE
    )
    table_ref_id: str = Field(min_length=1)
    logical_table_id: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    soft_row_limit: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_limit_exceeded(self) -> Self:
        if self.row_count <= self.soft_row_limit:
            raise ValueError("memory table row count must exceed soft row limit")
        return self


def memory_table_soft_limit_warnings_from_summary(
    summary: Mapping[str, Any],
) -> tuple[MemoryTableSoftLimitWarningModel, ...]:
    raw_warnings = summary.get(MEMORY_TABLE_SOFT_LIMIT_WARNINGS_SUMMARY_KEY)
    if not isinstance(raw_warnings, list):
        return ()
    warnings: list[MemoryTableSoftLimitWarningModel] = []
    for raw_warning in raw_warnings:
        if not isinstance(raw_warning, Mapping):
            continue
        try:
            warnings.append(
                MemoryTableSoftLimitWarningModel.model_validate(dict(raw_warning))
            )
        except ValueError:
            continue
    return tuple(warnings)
