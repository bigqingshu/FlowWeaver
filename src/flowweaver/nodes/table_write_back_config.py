from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_BACK_TABLE_NODE_TYPE
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def writeback_match_rules_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[dict[str, str]]:
    value = config.get("match_rules")
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "WriteBackTableNode config.match_rules must be a non-empty list"
        )
    rules: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteBackTableNode config.match_rules must contain objects"
            )
        source_field = _mapping_string(
            item,
            "source_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        target_field = _mapping_string(
            item,
            "target_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        operator = item.get("operator", "equals")
        if not isinstance(operator, str) or not operator.strip():
            raise _NodeValidationError(
                "WriteBackTableNode match rule operator is required"
            )
        normalized_operator = operator.strip().lower()
        if normalized_operator not in {
            "equals",
            "contains",
            "starts_with",
            "ends_with",
        }:
            raise _NodeValidationError(
                f"Unsupported WriteBackTableNode match rule operator: {operator}"
            )
        rules.append(
            {
                "source_field": source_field,
                "target_field": target_field,
                "operator": normalized_operator,
            }
        )
    return rules


def writeback_field_mappings_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[dict[str, str]]:
    value = config.get("field_mappings")
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "WriteBackTableNode config.field_mappings must be a non-empty list"
        )
    mappings: list[dict[str, str]] = []
    source_fields: set[str] = set()
    target_fields: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "WriteBackTableNode config.field_mappings must contain objects"
            )
        source_field = _mapping_string(
            item,
            "source_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        target_field = _mapping_string(
            item,
            "target_field",
            node_type=WRITE_BACK_TABLE_NODE_TYPE,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        if source_field in source_fields:
            raise _NodeValidationError(
                f"WriteBackTableNode duplicate mapping source: {source_field}"
            )
        if target_field in target_fields:
            raise _NodeValidationError(
                f"WriteBackTableNode duplicate mapping target: {target_field}"
            )
        source_fields.add(source_field)
        target_fields.add(target_field)
        mappings.append(
            {
                "source_field": source_field,
                "target_field": target_field,
            }
        )
    return mappings


def _mapping_string(
    config: dict[str, Any],
    key: str,
    *,
    node_type: str,
) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError(f"{node_type} {key} is required")
    return value.strip()
