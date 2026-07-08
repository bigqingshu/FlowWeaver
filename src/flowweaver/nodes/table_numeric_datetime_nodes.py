from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    PARSE_DATETIME_NODE_TYPE,
)
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
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_non_negative_int_config as _optional_non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
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
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class NumericColumnOperationNodeHandler:
    node_type = NUMERIC_COLUMN_OPERATION_NODE_TYPE

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
        operation = _enum_config(
            task.config,
            "operation",
            default="add",
            allowed={
                "add",
                "subtract",
                "multiply",
                "divide",
                "sequence",
                "round",
                "floor",
                "ceil",
            },
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="overwrite",
            allowed={"overwrite", "new_field"},
            node_type=self.node_type,
        )
        output_field = _numeric_output_field(
            task.config,
            input_ref=input_ref,
            target_field=target_field,
            output_mode=output_mode,
        )
        output_schema = _numeric_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        row_selector = _numeric_row_selector(task.config, input_ref=input_ref)
        operand_config = _numeric_operand_config(task.config, input_ref=input_ref)
        decimal_places = _optional_non_negative_int_config(
            task.config,
            "decimal_places",
            node_type=self.node_type,
        )
        non_number_policy = _enum_config(
            task.config,
            "non_number_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )
        divide_zero_policy = _enum_config(
            task.config,
            "divide_zero_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )

        def output_batches():
            row_number = 1
            sequence_index = 0
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if not _numeric_row_selected(
                        row,
                        row_number=row_number,
                        selector=row_selector,
                    ):
                        output_rows.append(
                            dict(row) | {output_field: row.get(target_field)}
                        )
                        row_number += 1
                        continue
                    sequence_index += 1
                    output_value = _numeric_operation_value(
                        row,
                        row_number=row_number,
                        sequence_index=sequence_index,
                        target_field=target_field,
                        operation=operation,
                        operand_config=operand_config,
                        decimal_places=decimal_places,
                        non_number_policy=non_number_policy,
                        divide_zero_policy=divide_zero_policy,
                        config=task.config,
                    )
                    output_rows.append(dict(row) | {output_field: output_value})
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


class AddCurrentDateTimeColumnNodeHandler:
    node_type = ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE

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
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _datetime_output_field(
            task.config,
            input_ref=input_ref,
            output_mode=output_mode,
        )
        output_schema = _datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        time_mode = _enum_config(
            task.config,
            "time_mode",
            default="fixed",
            allowed={"fixed", "per_row"},
            node_type=self.node_type,
        )
        format_mode = _enum_config(
            task.config,
            "format_mode",
            default="iso",
            allowed={"iso", "strftime", "template"},
            node_type=self.node_type,
        )
        fixed_value = (
            _datetime_formatted_value(
                utc_now(),
                config=task.config,
                format_mode=format_mode,
            )
            if time_mode == "fixed"
            else None
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    value = fixed_value
                    if value is None:
                        value = _datetime_formatted_value(
                            utc_now(),
                            config=task.config,
                            format_mode=format_mode,
                        )
                    output_rows.append(dict(row) | {output_field: value})
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


class ParseDateTimeNodeHandler:
    node_type = PARSE_DATETIME_NODE_TYPE

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
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        use_separate_time_field = _bool_config(
            task.config,
            "use_separate_time_field",
            default=False,
        )
        time_source_field = None
        if use_separate_time_field:
            time_source_field = _node_string_config(
                task.config,
                "time_source_field",
                node_type=self.node_type,
            )
            if find_field(input_ref.schema, time_source_field) is None:
                raise _NodeValidationError(f"Field does not exist: {time_source_field}")
        parse_type = _enum_config(
            task.config,
            "parse_type",
            default="datetime",
            allowed={"date", "time", "datetime"},
            node_type=self.node_type,
        )
        input_structure = _enum_config(
            task.config,
            "input_structure",
            default="auto",
            allowed={"auto", "strptime"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite_source", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _parse_datetime_output_field(
            task.config,
            input_ref=input_ref,
            source_field=source_field,
            output_mode=output_mode,
        )
        output_status = _bool_config(task.config, "output_status", default=True)
        status_field = None
        if output_status:
            status_field = _optional_node_string_config(
                task.config,
                "status_field",
                default="parse_status",
                node_type=self.node_type,
            )
        output_schema = _parse_datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
            status_field=status_field,
        )
        unmatched_mode = _enum_config(
            task.config,
            "unmatched_mode",
            default="empty",
            allowed={"empty", "keep_original", "fixed"},
            node_type=self.node_type,
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    raw_value = row.get(source_field)
                    if time_source_field is not None:
                        raw_value = f"{raw_value} {row.get(time_source_field)}"
                    parsed = _parse_datetime_value(
                        raw_value,
                        config=task.config,
                        parse_type=parse_type,
                        input_structure=input_structure,
                    )
                    status = "parsed" if parsed is not None else "failed"
                    output_value = (
                        _format_parsed_datetime(
                            parsed,
                            config=task.config,
                            parse_type=parse_type,
                        )
                        if parsed is not None
                        else _parse_datetime_unmatched_value(
                            raw_value,
                            config=task.config,
                            unmatched_mode=unmatched_mode,
                        )
                    )
                    output_row = dict(row) | {output_field: output_value}
                    if status_field is not None:
                        output_row[status_field] = status
                    output_rows.append(output_row)
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


def _numeric_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    target_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite":
        return target_field
    output_field = _optional_node_string_config(
        config,
        "output_field",
        default=f"{target_field}_result",
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    if has_field(input_ref.schema, output_field):
        raise _NodeValidationError(f"Field already exists: {output_field}")
    return output_field


def _numeric_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
) -> list[FieldSchemaModel]:
    if output_mode == "new_field":
        return append_field(
            input_schema,
            name=output_field,
            data_type="FLOAT",
            nullable=True,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="FLOAT",
        nullable=True,
    )


def _numeric_row_selector(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    range_mode = _enum_config(
        config,
        "range_mode",
        default="all",
        allowed={"all", "row_range", "reference_non_empty"},
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    selector: dict[str, Any] = {"range_mode": range_mode}
    if range_mode == "row_range":
        start_row = _positive_int_config(
            config,
            "start_row",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        end_row = _optional_positive_int_config(
            config,
            "end_row",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if end_row is not None and start_row > end_row:
            raise _NodeValidationError(
                "NumericColumnOperationNode start_row must be <= end_row"
            )
        selector |= {"start_row": start_row, "end_row": end_row}
    elif range_mode == "reference_non_empty":
        reference_field = _node_string_config(
            config,
            "reference_field",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if find_field(input_ref.schema, reference_field) is None:
            raise _NodeValidationError(f"Field does not exist: {reference_field}")
        selector["reference_field"] = reference_field
    return selector


def _numeric_row_selected(
    row: dict[str, Any],
    *,
    row_number: int,
    selector: dict[str, Any],
) -> bool:
    range_mode = selector["range_mode"]
    if range_mode == "all":
        return True
    if range_mode == "row_range":
        end_row = selector.get("end_row")
        if end_row is None:
            return row_number >= selector["start_row"]
        return selector["start_row"] <= row_number <= end_row
    if range_mode == "reference_non_empty":
        return not _is_empty_cell(row.get(selector["reference_field"]))
    return True


def _numeric_operand_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    operand_source = _enum_config(
        config,
        "operand_source",
        default="literal",
        allowed={"literal", "row_field", "row_number", "sequence"},
        node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
    )
    operand_config: dict[str, Any] = {"operand_source": operand_source}
    if operand_source == "literal":
        operand_config["value"] = config.get("operand_value", 0)
    elif operand_source == "row_field":
        operand_field = _node_string_config(
            config,
            "operand_field",
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        if find_field(input_ref.schema, operand_field) is None:
            raise _NodeValidationError(f"Field does not exist: {operand_field}")
        operand_config["field"] = operand_field
    elif operand_source == "sequence":
        operand_config["start"] = _number_config(
            config,
            "sequence_start",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
        operand_config["step"] = _number_config(
            config,
            "sequence_step",
            default=1,
            node_type=NUMERIC_COLUMN_OPERATION_NODE_TYPE,
        )
    return operand_config


def _number_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | float,
    node_type: str,
) -> float:
    value = config.get(key, default)
    number = _parse_number(value)
    if number is None:
        raise _NodeValidationError(f"{node_type} config.{key} must be a number")
    return number


def _numeric_operation_value(
    row: dict[str, Any],
    *,
    row_number: int,
    sequence_index: int,
    target_field: str,
    operation: str,
    operand_config: dict[str, Any],
    decimal_places: int | None,
    non_number_policy: str,
    divide_zero_policy: str,
    config: dict[str, Any],
) -> Any:
    original_value = row.get(target_field)
    if operation == "sequence":
        result = _numeric_operand_value(
            row,
            row_number=row_number,
            sequence_index=sequence_index,
            operand_config=operand_config,
        )
        return _numeric_round_result(result, decimal_places)
    target_number = _parse_number(original_value)
    if target_number is None:
        return _numeric_policy_value(
            config,
            policy=non_number_policy,
            fixed_key="non_number_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode target value is not a number",
        )
    if operation in {"round", "floor", "ceil"}:
        result = _numeric_unary_operation(
            target_number,
            operation=operation,
            decimal_places=decimal_places,
        )
        return _numeric_round_result(result, decimal_places)
    operand_value = _numeric_operand_value(
        row,
        row_number=row_number,
        sequence_index=sequence_index,
        operand_config=operand_config,
    )
    operand_number = _parse_number(operand_value)
    if operand_number is None:
        return _numeric_policy_value(
            config,
            policy=non_number_policy,
            fixed_key="non_number_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode operand is not a number",
        )
    if operation == "divide" and operand_number == 0:
        return _numeric_policy_value(
            config,
            policy=divide_zero_policy,
            fixed_key="divide_zero_fixed",
            original_value=original_value,
            error_message="NumericColumnOperationNode cannot divide by zero",
        )
    result = _numeric_binary_operation(
        target_number,
        operand_number,
        operation=operation,
    )
    return _numeric_round_result(result, decimal_places)


def _numeric_operand_value(
    row: dict[str, Any],
    *,
    row_number: int,
    sequence_index: int,
    operand_config: dict[str, Any],
) -> Any:
    operand_source = operand_config["operand_source"]
    if operand_source == "literal":
        return operand_config["value"]
    if operand_source == "row_field":
        return row.get(operand_config["field"])
    if operand_source == "row_number":
        return row_number
    if operand_source == "sequence":
        return operand_config["start"] + (sequence_index - 1) * operand_config["step"]
    return None


def _numeric_unary_operation(
    value: float,
    *,
    operation: str,
    decimal_places: int | None,
) -> float:
    if operation == "round":
        places = 0 if decimal_places is None else decimal_places
        return float(round(value, places))
    if operation == "floor":
        return float(math.floor(value))
    if operation == "ceil":
        return float(math.ceil(value))
    return value


def _numeric_binary_operation(
    target_number: float,
    operand_number: float,
    *,
    operation: str,
) -> float:
    if operation == "add":
        return target_number + operand_number
    if operation == "subtract":
        return target_number - operand_number
    if operation == "multiply":
        return target_number * operand_number
    if operation == "divide":
        return target_number / operand_number
    raise _NodeValidationError(
        f"Unsupported NumericColumnOperationNode operation: {operation}"
    )


def _numeric_round_result(value: float, decimal_places: int | None) -> float:
    if decimal_places is None:
        return value
    return float(round(value, decimal_places))


def _numeric_policy_value(
    config: dict[str, Any],
    *,
    policy: str,
    fixed_key: str,
    original_value: Any,
    error_message: str,
) -> Any:
    if policy == "empty":
        return None
    if policy == "fixed":
        return config.get(fixed_key)
    if policy == "keep_original":
        return original_value
    raise _NodeValidationError(error_message)


def _parse_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    output_mode: str,
) -> str:
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="current_datetime" if output_mode == "new_field" else "",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def _datetime_output_schema(
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
            nullable=False,
        )
    return replace_field_schema(
        input_schema,
        output_field,
        data_type="TEXT",
        nullable=False,
    )


def _datetime_formatted_value(
    value,
    *,
    config: dict[str, Any],
    format_mode: str,
) -> str:
    if format_mode == "iso":
        return value.isoformat()
    if format_mode == "strftime":
        template = _optional_node_string_config(
            config,
            "strftime_template",
            default="%Y-%m-%d %H:%M:%S",
            node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "template",
        default="{datetime}",
        node_type=ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    )
    replacements = {
        "iso": value.isoformat(),
        "date": value.date().isoformat(),
        "time": value.strftime("%H:%M:%S"),
        "datetime": value.strftime("%Y-%m-%d %H:%M:%S"),
        "year": f"{value.year:04d}",
        "month": f"{value.month:02d}",
        "day": f"{value.day:02d}",
        "hour": f"{value.hour:02d}",
        "minute": f"{value.minute:02d}",
        "second": f"{value.second:02d}",
    }
    try:
        return template.format(**replacements)
    except (KeyError, ValueError) as exc:
        raise _NodeValidationError(str(exc)) from exc


def _parse_datetime_output_field(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    source_field: str,
    output_mode: str,
) -> str:
    if output_mode == "overwrite_source":
        return source_field
    key = "new_field" if output_mode == "new_field" else "target_field"
    output_field = _optional_node_string_config(
        config,
        key,
        default="parsed_datetime" if output_mode == "new_field" else "",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if output_mode == "new_field":
        if has_field(input_ref.schema, output_field):
            raise _NodeValidationError(f"Field already exists: {output_field}")
    elif find_field(input_ref.schema, output_field) is None:
        raise _NodeValidationError(f"Field does not exist: {output_field}")
    return output_field


def _parse_datetime_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    output_field: str,
    output_mode: str,
    status_field: str | None,
) -> list[FieldSchemaModel]:
    schema = (
        append_field(
            input_schema,
            name=output_field,
            data_type="TEXT",
            nullable=True,
        )
        if output_mode == "new_field"
        else replace_field_schema(
            input_schema,
            output_field,
            data_type="TEXT",
            nullable=True,
        )
    )
    if status_field is None:
        return schema
    if has_field(schema, status_field):
        raise _NodeValidationError(f"Field already exists: {status_field}")
    return append_field(
        schema,
        name=status_field,
        data_type="TEXT",
        nullable=False,
    )


def _parse_datetime_value(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
    input_structure: str,
):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if input_structure == "strptime":
        input_format = _node_string_config(
            config,
            "input_format",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        try:
            return datetime.strptime(text, input_format)
        except ValueError:
            return None
    return _parse_datetime_auto(text, parse_type=parse_type, config=config)


def _parse_datetime_auto(text: str, *, parse_type: str, config: dict[str, Any]):
    try:
        if parse_type == "date":
            return datetime.fromisoformat(text).date()
        if parse_type == "time":
            return datetime.strptime(text, "%H:%M:%S").time()
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for input_format in _parse_datetime_auto_formats(parse_type, config=config):
        try:
            parsed = datetime.strptime(text, input_format)
        except ValueError:
            continue
        if parse_type == "date":
            return parsed.date()
        if parse_type == "time":
            return parsed.time()
        return parsed
    return None


def _parse_datetime_auto_formats(
    parse_type: str,
    *,
    config: dict[str, Any],
) -> list[str]:
    date_order = _enum_config(
        config,
        "date_order",
        default="ymd",
        allowed={"ymd", "mdy", "dmy"},
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if parse_type == "time":
        return ["%H:%M:%S", "%H:%M"]
    date_formats_by_order = {
        "ymd": ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%y-%m-%d", "%y/%m/%d"],
        "mdy": ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"],
        "dmy": ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"],
    }
    date_formats = date_formats_by_order[date_order]
    if parse_type == "date":
        return date_formats
    time_formats = ["%H:%M:%S", "%H:%M"]
    return [
        f"{date_format} {time_format}"
        for date_format in date_formats
        for time_format in time_formats
    ]


def _format_parsed_datetime(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
) -> str:
    if parse_type == "date":
        template = _optional_node_string_config(
            config,
            "output_template",
            default="%Y-%m-%d",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    if parse_type == "time":
        template = _optional_node_string_config(
            config,
            "time_output_template",
            default="%H:%M:%S",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "datetime_output_template",
        default="%Y-%m-%d %H:%M:%S",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    return value.strftime(template)


def _parse_datetime_unmatched_value(
    original_value: Any,
    *,
    config: dict[str, Any],
    unmatched_mode: str,
) -> Any:
    if unmatched_mode == "empty":
        return ""
    if unmatched_mode == "keep_original":
        return original_value
    return config.get("unmatched_fixed")
