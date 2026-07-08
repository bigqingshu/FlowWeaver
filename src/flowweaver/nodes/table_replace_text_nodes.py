from __future__ import annotations

import re
from typing import Any

from flowweaver.nodes.builtin_table_node_types import REPLACE_TEXT_NODE_TYPE
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    non_negative_int_config as _non_negative_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import has_field
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ReplaceTextNodeHandler:
    node_type = REPLACE_TEXT_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if not has_field(input_ref.schema, target_field):
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="contains",
            allowed={
                "contains",
                "equals",
                "starts_with",
                "ends_with",
                "regex",
                "is_empty",
                "is_not_empty",
            },
            node_type=self.node_type,
        )
        replace_mode = _enum_config(
            task.config,
            "replace_mode",
            default="partial",
            allowed={"partial", "whole_cell"},
            node_type=self.node_type,
        )
        case_sensitive = _bool_config(
            task.config,
            "case_sensitive",
            default=True,
        )
        replace_count = _non_negative_int_config(
            task.config,
            "replace_count",
            default=0,
            node_type=self.node_type,
        )
        skip_empty_match_value = _bool_config(
            task.config,
            "skip_empty_match_value",
            default=True,
        )
        match_source = _value_source_config(
            task.config,
            "match_value_source",
            fallback_key="match_value",
        )
        replace_source = _value_source_config(
            task.config,
            "replace_value_source",
            fallback_key="replace_value",
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        output_rows.append(
                            row | {
                                target_field: _replace_text_value(
                                    row.get(target_field),
                                    row=row,
                                    match_mode=match_mode,
                                    match_source=match_source,
                                    replace_source=replace_source,
                                    replace_mode=replace_mode,
                                    case_sensitive=case_sensitive,
                                    replace_count=replace_count,
                                    skip_empty_match_value=skip_empty_match_value,
                                )
                            }
                        )
                    except (ValueSourceError, re.error) as exc:
                        raise _NodeValidationError(str(exc)) from exc
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=output_batches(),
        )


def _replace_text_value(
    cell_value: Any,
    *,
    row: dict[str, Any],
    match_mode: str,
    match_source,
    replace_source,
    replace_mode: str,
    case_sensitive: bool,
    replace_count: int,
    skip_empty_match_value: bool,
) -> Any:
    match_value = match_source.resolve(row)
    replace_value = replace_source.resolve(row)
    if match_mode not in {"is_empty", "is_not_empty"}:
        match_text = "" if match_value is None else str(match_value)
        if skip_empty_match_value and match_text == "":
            return cell_value
    else:
        match_text = ""
    if not _text_cell_matches(
        cell_value,
        match_mode=match_mode,
        match_text=match_text,
        case_sensitive=case_sensitive,
    ):
        return cell_value
    if replace_mode == "whole_cell" or match_mode in {"is_empty", "is_not_empty"}:
        return replace_value
    cell_text = "" if cell_value is None else str(cell_value)
    replacement = "" if replace_value is None else str(replace_value)
    if match_mode == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        count = 0 if replace_count == 0 else replace_count
        return re.sub(match_text, replacement, cell_text, count=count, flags=flags)
    if case_sensitive:
        count = -1 if replace_count == 0 else replace_count
        return cell_text.replace(match_text, replacement, count)
    count = 0 if replace_count == 0 else replace_count
    return re.sub(
        re.escape(match_text),
        replacement,
        cell_text,
        count=count,
        flags=re.IGNORECASE,
    )


def _text_cell_matches(
    cell_value: Any,
    *,
    match_mode: str,
    match_text: str,
    case_sensitive: bool,
) -> bool:
    if match_mode == "is_empty":
        return _is_empty_cell(cell_value)
    if match_mode == "is_not_empty":
        return not _is_empty_cell(cell_value)
    cell_text = "" if cell_value is None else str(cell_value)
    candidate = cell_text if case_sensitive else cell_text.lower()
    expected = match_text if case_sensitive else match_text.lower()
    if match_mode == "contains":
        return expected in candidate
    if match_mode == "equals":
        return candidate == expected
    if match_mode == "starts_with":
        return candidate.startswith(expected)
    if match_mode == "ends_with":
        return candidate.endswith(expected)
    if match_mode == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.search(match_text, cell_text, flags=flags) is not None
    return False
