from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    FILL_CELLS_NODE_TYPE,
    FILL_RANGE_NODE_TYPE,
    FILL_SEQUENCE_NODE_TYPE,
)
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
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
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
from flowweaver.nodes.table_ops import find_field, has_field, replace_field_schema
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

DEFAULT_FILL_RANGE_MAX_CELLS = 100_000
_NodeValidationError = BuiltinTableNodeValidationError


class FillCellsNodeHandler:
    node_type = FILL_CELLS_NODE_TYPE

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
        value_source = _fill_cells_value_source_config(task.config)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        direction = _enum_config(
            task.config,
            "direction",
            default="down",
            allowed={"down", "up"},
            node_type=self.node_type,
        )
        count = _optional_positive_int_config(
            task.config,
            "count",
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        if start_row > total_rows and total_rows > 0:
            raise _NodeValidationError("FillCellsNode config.start_row is out of range")
        selected_rows = _fill_cells_selected_rows(
            start_row=start_row,
            direction=direction,
            count=count,
            total_rows=total_rows,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if row_number in selected_rows and (
                        overwrite_rule == "all" or _is_empty_cell(row.get(target_field))
                    ):
                        try:
                            output_rows.append(
                                row | {target_field: value_source.resolve(row)}
                            )
                        except ValueSourceError as exc:
                            raise _NodeValidationError(str(exc)) from exc
                    else:
                        output_rows.append(row)
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=output_batches(),
        )


class FillRangeNodeHandler:
    node_type = FILL_RANGE_NODE_TYPE

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
        start_field = _node_string_config(
            task.config,
            "start_field",
            node_type=self.node_type,
        )
        end_field = _optional_node_string_config(
            task.config,
            "end_field",
            default=start_field,
            node_type=self.node_type,
        )
        target_fields = _field_range(
            input_ref.schema,
            start_field=start_field,
            end_field=end_field,
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        end_row = _optional_positive_int_config(
            task.config,
            "end_row",
            node_type=self.node_type,
        )
        if end_row is None:
            end_row = total_rows
        if total_rows > 0 and (start_row > total_rows or end_row > total_rows):
            raise _NodeValidationError("FillRangeNode row range is out of range")
        if start_row > end_row:
            raise _NodeValidationError("FillRangeNode start_row must be <= end_row")
        max_cells = _positive_int_config(
            task.config,
            "max_cells",
            default=DEFAULT_FILL_RANGE_MAX_CELLS,
            node_type=self.node_type,
        )
        target_row_count = 0 if total_rows <= 0 else end_row - start_row + 1
        target_cell_count = target_row_count * len(target_fields)
        if target_cell_count > max_cells:
            raise _NodeValidationError("FillRangeNode target range exceeds max_cells")
        value_source = _value_source_config(
            task.config,
            "value_source",
            fallback_key="manual_value",
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if start_row <= row_number <= end_row:
                        try:
                            fill_value = value_source.resolve(row)
                        except ValueSourceError as exc:
                            raise _NodeValidationError(str(exc)) from exc
                        output_row = dict(row)
                        for field in target_fields:
                            if overwrite_rule == "all" or _is_empty_cell(
                                output_row.get(field)
                            ):
                                output_row[field] = fill_value
                        output_rows.append(output_row)
                    else:
                        output_rows.append(row)
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=output_batches(),
        )


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


def _field_range(
    schema: list[FieldSchemaModel],
    *,
    start_field: str,
    end_field: str,
    node_type: str,
) -> list[str]:
    start_schema = find_field(schema, start_field)
    if start_schema is None:
        raise _NodeValidationError(f"Field does not exist: {start_field}")
    end_schema = find_field(schema, end_field)
    if end_schema is None:
        raise _NodeValidationError(f"Field does not exist: {end_field}")
    if start_schema.ordinal > end_schema.ordinal:
        raise _NodeValidationError(
            f"{node_type} start_field must not be after end_field"
        )
    return [
        field.name
        for field in schema
        if start_schema.ordinal <= field.ordinal <= end_schema.ordinal
    ]


def _fill_cells_value_source_config(config: dict[str, Any]):
    return _value_source_config(
        config,
        "value_source",
        fallback_key="manual_value",
    )


def _fill_cells_selected_rows(
    *,
    start_row: int,
    direction: str,
    count: int | None,
    total_rows: int,
) -> set[int]:
    if total_rows <= 0:
        return set()
    if direction == "down":
        end_row = (
            total_rows
            if count is None
            else min(total_rows, start_row + count - 1)
        )
        return set(range(start_row, end_row + 1))
    end_row = 1 if count is None else max(1, start_row - count + 1)
    return set(range(end_row, start_row + 1))


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
