from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_extract_text_methods import (
    extract_text_by_method as _extract_text_by_method,
)
from flowweaver.nodes.table_extract_text_methods import (
    extract_text_rule_fallback_key as extract_text_rule_fallback_key,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

SKIP_ROW = object()
_NodeValidationError = BuiltinTableNodeValidationError


def extract_text_value(
    source_value: Any,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    method: str,
    rule_source,
    strip_result: bool,
) -> str | None:
    source_text = "" if source_value is None else str(source_value)
    result = _extract_text_by_method(
        source_text,
        row=row,
        config=config,
        method=method,
        rule_source=rule_source,
    )
    if result is not None and strip_result:
        return result.strip()
    return result


def extract_text_unmatched_value(
    row: dict[str, Any],
    *,
    source_value: Any,
    unmatched_mode: str,
    unmatched_source,
) -> Any:
    if unmatched_mode == "empty":
        return ""
    if unmatched_mode == "keep_original":
        return source_value
    if unmatched_mode == "fixed":
        return unmatched_source.resolve(row)
    if unmatched_mode == "skip_row":
        return SKIP_ROW
    raise _NodeValidationError(
        f"Unsupported ExtractTextNode unmatched_mode: {unmatched_mode}"
    )
