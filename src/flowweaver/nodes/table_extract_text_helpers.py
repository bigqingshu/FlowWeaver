from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.builtin_table_node_types import EXTRACT_TEXT_NODE_TYPE
from flowweaver.nodes.table_extract_text_values import SKIP_ROW as SKIP_ROW
from flowweaver.nodes.table_extract_text_values import (
    extract_text_rule_fallback_key as extract_text_rule_fallback_key,
)
from flowweaver.nodes.table_extract_text_values import (
    extract_text_unmatched_value as extract_text_unmatched_value,
)
from flowweaver.nodes.table_extract_text_values import (
    extract_text_value as extract_text_value,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.nodes.value_sources import ValueSource, ValueSourceError
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

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


def extract_text_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    config: dict[str, Any],
    source_field: str,
    output_field: str,
    method: str,
    rule_source: ValueSource,
    strip_result: bool,
    unmatched_mode: str,
    unmatched_source: ValueSource,
) -> Iterator[list[dict[str, Any]]]:
    for rows in context.iter_row_batches(input_ref):
        output_rows: list[dict[str, Any]] = []
        for row in rows:
            try:
                extracted = extract_text_value(
                    row.get(source_field),
                    row=row,
                    config=config,
                    method=method,
                    rule_source=rule_source,
                    strip_result=strip_result,
                )
                if extracted is None:
                    extracted = extract_text_unmatched_value(
                        row,
                        source_value=row.get(source_field),
                        unmatched_mode=unmatched_mode,
                        unmatched_source=unmatched_source,
                    )
                if extracted is SKIP_ROW:
                    continue
            except (ValueSourceError, re.error, IndexError) as exc:
                raise _NodeValidationError(str(exc)) from exc
            output_rows.append(dict(row) | {output_field: extracted})
        yield output_rows
