from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import FILL_SEQUENCE_NODE_TYPE
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    non_negative_int_config as _non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
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
from flowweaver.nodes.table_numeric_datetime_nodes import _number_config
from flowweaver.nodes.table_ops import find_field, replace_field_schema
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class FillSequenceNodeHandler:
    node_type = FILL_SEQUENCE_NODE_TYPE

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
        if find_field(input_ref.schema, target_field) is None:
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        total_rows = context.count_rows(input_ref)
        selector = _fill_sequence_selector(
            task.config,
            input_ref=input_ref,
            total_rows=total_rows,
        )
        start_value = _number_config(
            task.config,
            "start_value",
            default=1,
            node_type=self.node_type,
        )
        step = _number_config(
            task.config,
            "step",
            default=1,
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )
        zero_pad = _non_negative_int_config(
            task.config,
            "zero_pad",
            default=0,
            node_type=self.node_type,
        )
        prefix = _optional_string_config(
            task.config,
            "prefix",
            node_type=self.node_type,
        )
        suffix = _optional_string_config(
            task.config,
            "suffix",
            node_type=self.node_type,
        )
        output_schema = _fill_sequence_output_schema(
            input_ref.schema,
            target_field=target_field,
            formatted=bool(prefix or suffix or zero_pad),
        )

        def output_batches():
            row_number = 1
            sequence_index = 0
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    selected_index = _fill_sequence_selected_index(
                        row,
                        row_number=row_number,
                        selector=selector,
                    )
                    should_fill = selected_index is not None and (
                        overwrite_rule == "all"
                        or _is_empty_cell(row.get(target_field))
                    )
                    if should_fill:
                        assert selected_index is not None
                        if selected_index <= 0:
                            sequence_index += 1
                            selected_index = sequence_index
                        output_rows.append(
                            dict(row) | {
                                target_field: _format_sequence_value(
                                    start_value + (selected_index - 1) * step,
                                    zero_pad=zero_pad,
                                    prefix=prefix,
                                    suffix=suffix,
                                )
                            }
                        )
                    else:
                        output_rows.append(dict(row))
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


def _fill_sequence_selector(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    total_rows: int,
) -> dict[str, Any]:
    start_row = _positive_int_config(
        config,
        "start_row",
        default=1,
        node_type=FILL_SEQUENCE_NODE_TYPE,
    )
    if total_rows > 0 and start_row > total_rows:
        raise _NodeValidationError("FillSequenceNode config.start_row is out of range")
    direction = _enum_config(
        config,
        "direction",
        default="down",
        allowed={"down", "up"},
        node_type=FILL_SEQUENCE_NODE_TYPE,
    )
    end_mode = _enum_config(
        config,
        "end_mode",
        default="to_end",
        allowed={"to_end", "count", "end_row", "reference_non_empty"},
        node_type=FILL_SEQUENCE_NODE_TYPE,
    )
    selected_rows = _fill_sequence_selected_rows(
        config,
        total_rows=total_rows,
        start_row=start_row,
        direction=direction,
        end_mode=end_mode,
    )
    reference_field = None
    if end_mode == "reference_non_empty":
        reference_field = _node_string_config(
            config,
            "reference_field",
            node_type=FILL_SEQUENCE_NODE_TYPE,
        )
        if find_field(input_ref.schema, reference_field) is None:
            raise _NodeValidationError(f"Field does not exist: {reference_field}")
    return {
        "selected_index_by_row": {
            row_number: index + 1
            for index, row_number in enumerate(selected_rows)
        },
        "reference_field": reference_field,
    }


def _fill_sequence_selected_rows(
    config: dict[str, Any],
    *,
    total_rows: int,
    start_row: int,
    direction: str,
    end_mode: str,
) -> list[int]:
    if total_rows <= 0:
        return []
    if end_mode == "count":
        count = _positive_int_config(
            config,
            "count",
            default=1,
            node_type=FILL_SEQUENCE_NODE_TYPE,
        )
        if direction == "down":
            end_row = min(total_rows, start_row + count - 1)
            return list(range(start_row, end_row + 1))
        end_row = max(1, start_row - count + 1)
        return list(range(start_row, end_row - 1, -1))
    if end_mode == "end_row":
        end_row = _positive_int_config(
            config,
            "end_row",
            default=total_rows if direction == "down" else 1,
            node_type=FILL_SEQUENCE_NODE_TYPE,
        )
        if end_row > total_rows:
            raise _NodeValidationError(
                "FillSequenceNode config.end_row is out of range"
            )
        if direction == "down":
            if start_row > end_row:
                raise _NodeValidationError(
                    "FillSequenceNode start_row must be <= end_row"
                )
            return list(range(start_row, end_row + 1))
        if end_row > start_row:
            raise _NodeValidationError(
                "FillSequenceNode end_row must be <= start_row when direction is up"
            )
        return list(range(start_row, end_row - 1, -1))
    if direction == "down":
        return list(range(start_row, total_rows + 1))
    return list(range(start_row, 0, -1))


def _fill_sequence_selected_index(
    row: dict[str, Any],
    *,
    row_number: int,
    selector: dict[str, Any],
) -> int | None:
    selected_index = selector["selected_index_by_row"].get(row_number)
    if selected_index is None:
        return None
    reference_field = selector.get("reference_field")
    if reference_field is not None and _is_empty_cell(row.get(reference_field)):
        return None
    return selected_index


def _fill_sequence_output_schema(
    schema: list[FieldSchemaModel],
    *,
    target_field: str,
    formatted: bool,
) -> list[FieldSchemaModel]:
    if not formatted:
        return schema
    return replace_field_schema(
        schema,
        target_field,
        data_type="TEXT",
        nullable=True,
    )


def _format_sequence_value(
    value: float,
    *,
    zero_pad: int,
    prefix: str,
    suffix: str,
) -> Any:
    normalized = _normalize_sequence_number(value)
    if not prefix and not suffix and zero_pad <= 0:
        return normalized
    text = str(normalized)
    if zero_pad > 0:
        text = text.zfill(zero_pad)
    return f"{prefix}{text}{suffix}"


def _normalize_sequence_number(value: float) -> int | float:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
