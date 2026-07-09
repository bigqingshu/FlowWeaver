from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_extract_text_pattern_methods import (
    extract_text_between as _extract_text_between,
)
from flowweaver.nodes.table_extract_text_pattern_methods import (
    extract_text_delimiter as _extract_text_delimiter,
)
from flowweaver.nodes.table_extract_text_pattern_methods import (
    extract_text_regex as _extract_text_regex,
)
from flowweaver.nodes.table_extract_text_position_methods import (
    extract_text_left as _extract_text_left,
)
from flowweaver.nodes.table_extract_text_position_methods import (
    extract_text_position as _extract_text_position,
)
from flowweaver.nodes.table_extract_text_position_methods import (
    extract_text_right as _extract_text_right,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


def extract_text_rule_fallback_key(method: str) -> str:
    if method == "regex":
        return "regex_pattern"
    if method == "delimiter":
        return "delimiter"
    return "rule_value"


def extract_text_by_method(
    source_text: str,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    method: str,
    rule_source,
) -> str | None:
    if method == "regex":
        return _extract_text_regex(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    if method == "position":
        return _extract_text_position(source_text, config=config)
    if method == "left":
        return _extract_text_left(source_text, config=config)
    if method == "right":
        return _extract_text_right(source_text, config=config)
    if method == "delimiter":
        return _extract_text_delimiter(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    if method == "between":
        return _extract_text_between(source_text, config=config)
    raise _NodeValidationError(f"Unsupported ExtractTextNode method: {method}")
