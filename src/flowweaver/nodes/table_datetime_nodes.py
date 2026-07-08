from __future__ import annotations

from datetime import datetime
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
    PARSE_DATETIME_NODE_TYPE,
)
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
