from __future__ import annotations

import re
from typing import Any

from flowweaver.nodes.builtin_table_node_types import EXTRACT_TEXT_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import int_config as _int_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    non_negative_int_config as _non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

SKIP_ROW = object()
_NodeValidationError = BuiltinTableNodeValidationError


def extract_text_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _node_string_config(
        config,
        key,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def extract_text_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=True,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=True,
    )


def extract_text_rule_fallback_key(method: str) -> str:
    if method == "regex":
        return "regex_pattern"
    if method == "delimiter":
        return "delimiter"
    return "rule_value"


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
    if method == "regex":
        result = _extract_text_regex(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    elif method == "position":
        result = _extract_text_position(source_text, config=config)
    elif method == "left":
        result = _extract_text_left(source_text, config=config)
    elif method == "right":
        result = _extract_text_right(source_text, config=config)
    elif method == "delimiter":
        result = _extract_text_delimiter(
            source_text,
            row=row,
            config=config,
            rule_source=rule_source,
        )
    elif method == "between":
        result = _extract_text_between(source_text, config=config)
    else:
        raise _NodeValidationError(f"Unsupported ExtractTextNode method: {method}")
    if result is not None and strip_result:
        return result.strip()
    return result


def _extract_text_regex(
    source_text: str,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    rule_source,
) -> str | None:
    pattern = rule_source.resolve(row)
    if pattern is None or str(pattern) == "":
        raise _NodeValidationError("ExtractTextNode regex pattern is required")
    match = re.search(str(pattern), source_text)
    if match is None:
        return None
    regex_group = _non_negative_int_config(
        config,
        "regex_group",
        default=0,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    try:
        return match.group(regex_group)
    except IndexError:
        return None


def _extract_text_position(source_text: str, *, config: dict[str, Any]) -> str | None:
    start_pos = _non_negative_int_config(
        config,
        "start_pos",
        default=1,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    position_base = _enum_config(
        config,
        "position_base",
        default="one",
        allowed={"zero", "one"},
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    start_index = start_pos if position_base == "zero" else start_pos - 1
    if start_index < 0 or start_index >= len(source_text):
        return None
    extract_len = _optional_positive_int_config(
        config,
        "extract_len",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    if extract_len is None:
        return source_text[start_index:]
    return source_text[start_index : start_index + extract_len]


def _extract_text_left(source_text: str, *, config: dict[str, Any]) -> str:
    n_chars = _extract_text_n_chars(config)
    return source_text[:n_chars]


def _extract_text_right(source_text: str, *, config: dict[str, Any]) -> str:
    n_chars = _extract_text_n_chars(config)
    return source_text[-n_chars:] if n_chars > 0 else ""


def _extract_text_n_chars(config: dict[str, Any]) -> int:
    if config.get("n_chars") is not None:
        return _positive_int_config(
            config,
            "n_chars",
            default=1,
            node_type=EXTRACT_TEXT_NODE_TYPE,
        )
    return _positive_int_config(
        config,
        "extract_len",
        default=1,
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )


def _extract_text_delimiter(
    source_text: str,
    *,
    row: dict[str, Any],
    config: dict[str, Any],
    rule_source,
) -> str | None:
    delimiter = rule_source.resolve(row)
    if delimiter is None or str(delimiter) == "":
        raise _NodeValidationError("ExtractTextNode delimiter is required")
    parts = source_text.split(str(delimiter))
    part_index = _int_config(config, "part_index", default=1)
    position_base = _enum_config(
        config,
        "position_base",
        default="one",
        allowed={"zero", "one"},
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    selected_index = part_index if position_base == "zero" else part_index - 1
    if selected_index < 0 or selected_index >= len(parts):
        return None
    return parts[selected_index]


def _extract_text_between(source_text: str, *, config: dict[str, Any]) -> str | None:
    before_key = _node_string_config(
        config,
        "before_key",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    after_key = _node_string_config(
        config,
        "after_key",
        node_type=EXTRACT_TEXT_NODE_TYPE,
    )
    start_index = source_text.find(before_key)
    if start_index < 0:
        return None
    content_start = start_index + len(before_key)
    end_index = source_text.find(after_key, content_start)
    if end_index < 0:
        return None
    return source_text[content_start:end_index]


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
