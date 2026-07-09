from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.builtin_table_node_types import ADVANCED_FILTER_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field, has_field
from flowweaver.nodes.table_row_condition_helpers import (
    condition_cell_matches as _condition_cell_matches,
)
from flowweaver.nodes.table_row_condition_helpers import (
    normalize_condition_operator as _normalize_condition_operator,
)
from flowweaver.nodes.table_row_condition_helpers import (
    value_source_from_mapping as _value_source_from_mapping,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def advanced_filter_conditions(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[dict[str, Any]]:
    raw_conditions = config.get("conditions", [])
    if raw_conditions is None:
        raw_conditions = []
    if not isinstance(raw_conditions, list):
        raise _NodeValidationError(
            "AdvancedFilterRowsNode config.conditions must be a list"
        )
    conditions: list[dict[str, Any]] = []
    for index, item in enumerate(raw_conditions):
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode config.conditions must contain objects"
            )
        field = item.get("field")
        if not isinstance(field, str) or not field.strip():
            raise _NodeValidationError(
                f"AdvancedFilterRowsNode conditions[{index}].field is required"
            )
        field = field.strip()
        if find_field(input_ref.schema, field) is None:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_condition_operator(
            item.get("operator", item.get("op")),
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
            key=f"conditions[{index}].operator",
        )
        value_source = _value_source_from_mapping(
            item,
            value_key="value",
            value_source_key="value_source",
            value_field_key="value_field",
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
        )
        if (
            value_source.field is not None
            and find_field(input_ref.schema, value_source.field) is None
        ):
            raise _NodeValidationError(f"Field does not exist: {value_source.field}")
        case_sensitive = item.get("case_sensitive", True)
        if not isinstance(case_sensitive, bool):
            raise _NodeValidationError(
                "AdvancedFilterRowsNode condition.case_sensitive must be a boolean"
            )
        conditions.append(
            {
                "field": field,
                "operator": operator,
                "value_source": value_source,
                "case_sensitive": case_sensitive,
            }
        )
    return conditions


def advanced_filter_output_fields(
    config: dict[str, Any],
    input_ref: TableRefModel,
) -> list[str]:
    raw_output_fields = config.get("output_fields")
    if raw_output_fields is None or raw_output_fields == []:
        return [field.name for field in input_ref.schema]
    output_fields = _string_list_config(
        config,
        "output_fields",
        node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
    )
    missing_fields = [
        field_name
        for field_name in output_fields
        if not has_field(input_ref.schema, field_name)
    ]
    if missing_fields:
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return output_fields


def advanced_filter_row_matches(
    row: dict[str, Any],
    *,
    conditions: list[dict[str, Any]],
    logic: str,
) -> bool:
    if not conditions:
        return True
    if logic == "and":
        for condition in conditions:
            if not _advanced_filter_condition_matches(row, condition):
                return False
        return True
    for condition in conditions:
        if _advanced_filter_condition_matches(row, condition):
            return True
    return False


def advanced_filter_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    conditions: list[dict[str, Any]],
    logic: str,
    output_fields: list[str],
    result_limit: int | None,
    max_intermediate: int | None,
    remove_duplicates: bool,
) -> Iterator[list[dict[str, Any]]]:
    output_count = 0
    matched_count = 0
    seen_rows: set[tuple[Any, ...]] = set()
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                if not advanced_filter_row_matches(
                    row,
                    conditions=conditions,
                    logic=logic,
                ):
                    continue
            except ValueSourceError as exc:
                raise _NodeValidationError(str(exc)) from exc
            output_row = {
                field_name: row.get(field_name)
                for field_name in output_fields
            }
            if remove_duplicates:
                output_key = tuple(
                    output_row.get(field)
                    for field in output_fields
                )
                if output_key in seen_rows:
                    continue
                seen_rows.add(output_key)
            matched_count += 1
            if max_intermediate is not None and matched_count > max_intermediate:
                raise _NodeValidationError(
                    "AdvancedFilterRowsNode matched rows exceed max_intermediate"
                )
            if result_limit is not None and output_count >= result_limit:
                if output_rows:
                    yield output_rows
                return
            output_rows.append(output_row)
            output_count += 1
        if output_rows:
            yield output_rows


def _advanced_filter_condition_matches(
    row: dict[str, Any],
    condition: dict[str, Any],
) -> bool:
    value = condition["value_source"].resolve(row)
    return _condition_cell_matches(
        row.get(condition["field"]),
        operator=condition["operator"],
        value=value,
        case_sensitive=condition["case_sensitive"],
    )
