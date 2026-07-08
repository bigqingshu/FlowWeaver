from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import UNPIVOT_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_common import require_fields as _require_fields
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_list_config as _optional_string_list_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_config import string_list_config as _string_list_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import append_field
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class UnpivotRowsNodeHandler:
    node_type = UNPIVOT_ROWS_NODE_TYPE

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
        config = _unpivot_rows_config(task.config, input_ref=input_ref)
        output_schema = _unpivot_rows_output_schema(
            input_ref.schema,
            keep_fields=config["keep_fields"],
            output_value_field=config["output_value_field"],
            source_field_name=config["source_field_name"],
            original_row_field=config["original_row_field"],
            status_field=config["status_field"],
        )
        row_selector = _unpivot_row_selector(
            task.config,
            total_rows=context.count_rows(input_ref),
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if _unpivot_row_selected(row_number, row_selector):
                        output_rows.extend(
                            _unpivot_output_rows(
                                row,
                                row_number=row_number,
                                config=config,
                            )
                        )
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


def _unpivot_rows_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> dict[str, Any]:
    value_fields = _string_list_config(
        config,
        "value_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    keep_fields = _optional_string_list_config(
        config,
        "keep_fields",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    _require_fields(input_ref.schema, value_fields + keep_fields)
    output_value_field = _optional_node_string_config(
        config,
        "output_value_field",
        default="value",
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    output_source_field = _bool_config(
        config,
        "output_source_field",
        default=True,
    )
    source_field_name = (
        _optional_node_string_config(
            config,
            "source_field_name",
            default="source_field",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_source_field
        else None
    )
    output_original_row = _bool_config(
        config,
        "output_original_row",
        default=False,
    )
    original_row_field = (
        _optional_node_string_config(
            config,
            "original_row_field",
            default="original_row",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_original_row
        else None
    )
    output_status = _bool_config(config, "output_status", default=False)
    status_field = (
        _optional_node_string_config(
            config,
            "status_field",
            default="mapping_status",
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if output_status
        else None
    )
    output_field_names = [
        field
        for field in [
            output_value_field,
            source_field_name,
            original_row_field,
            status_field,
        ]
        if field is not None
    ]
    conflicts = sorted(set(keep_fields) & set(output_field_names))
    if conflicts:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields conflict with keep_fields: "
            f"{', '.join(conflicts)}"
        )
    duplicates = sorted(
        field
        for field in set(output_field_names)
        if output_field_names.count(field) > 1
    )
    if duplicates:
        raise _NodeValidationError(
            f"UnpivotRowsNode output fields are duplicated: {', '.join(duplicates)}"
        )
    return {
        "value_fields": value_fields,
        "keep_fields": keep_fields,
        "output_value_field": output_value_field,
        "source_field_name": source_field_name,
        "original_row_field": original_row_field,
        "status_field": status_field,
        "empty_mode": _enum_config(
            config,
            "empty_mode",
            default="skip",
            allowed={"skip", "empty", "fixed"},
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        ),
        "empty_fixed": config.get("empty_fixed"),
        "trim_value": _bool_config(config, "trim_value", default=False),
    }


def _unpivot_rows_output_schema(
    input_schema: list[FieldSchemaModel],
    *,
    keep_fields: list[str],
    output_value_field: str,
    source_field_name: str | None,
    original_row_field: str | None,
    status_field: str | None,
) -> list[FieldSchemaModel]:
    schema: list[FieldSchemaModel] = []
    fields_by_name = {field.name: field for field in input_schema}
    for field_name in keep_fields:
        field = fields_by_name[field_name]
        schema.append(field.model_copy(update={"ordinal": len(schema)}))
    schema = append_field(
        schema,
        name=output_value_field,
        data_type="TEXT",
        nullable=True,
    )
    if source_field_name is not None:
        schema = append_field(
            schema,
            name=source_field_name,
            data_type="TEXT",
            nullable=False,
        )
    if original_row_field is not None:
        schema = append_field(
            schema,
            name=original_row_field,
            data_type="INTEGER",
            nullable=False,
        )
    if status_field is not None:
        schema = append_field(
            schema,
            name=status_field,
            data_type="TEXT",
            nullable=False,
        )
    return schema


def _unpivot_row_selector(
    config: dict[str, Any],
    *,
    total_rows: int,
) -> dict[str, int]:
    start_row = _positive_int_config(
        config,
        "start_row",
        default=1,
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    if total_rows > 0 and start_row > total_rows:
        raise _NodeValidationError("UnpivotRowsNode config.start_row is out of range")
    end_mode = _enum_config(
        config,
        "end_mode",
        default="to_end",
        allowed={"to_end", "count", "end_row"},
        node_type=UNPIVOT_ROWS_NODE_TYPE,
    )
    if total_rows <= 0:
        return {"start_row": 1, "end_row": 0}
    if end_mode == "count":
        count = _positive_int_config(
            config,
            "count",
            default=1,
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        end_row = min(total_rows, start_row + count - 1)
    elif end_mode == "end_row":
        end_row = _positive_int_config(
            config,
            "end_row",
            default=total_rows,
            node_type=UNPIVOT_ROWS_NODE_TYPE,
        )
        if end_row > total_rows:
            raise _NodeValidationError("UnpivotRowsNode config.end_row is out of range")
        if start_row > end_row:
            raise _NodeValidationError("UnpivotRowsNode start_row must be <= end_row")
    else:
        end_row = total_rows
    return {"start_row": start_row, "end_row": end_row}


def _unpivot_row_selected(
    row_number: int,
    row_selector: dict[str, int],
) -> bool:
    return row_selector["start_row"] <= row_number <= row_selector["end_row"]


def _unpivot_output_rows(
    row: dict[str, Any],
    *,
    row_number: int,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    output_rows: list[dict[str, Any]] = []
    base_row = {
        field: row.get(field)
        for field in config["keep_fields"]
    }
    for value_field in config["value_fields"]:
        value = row.get(value_field)
        if config["trim_value"] and isinstance(value, str):
            value = value.strip()
        status = "mapped"
        if _is_empty_cell(value):
            if config["empty_mode"] == "skip":
                continue
            if config["empty_mode"] == "fixed":
                value = config["empty_fixed"]
                status = "empty_fixed"
            else:
                status = "empty"
        output_row = dict(base_row)
        output_row[config["output_value_field"]] = value
        if config["source_field_name"] is not None:
            output_row[config["source_field_name"]] = value_field
        if config["original_row_field"] is not None:
            output_row[config["original_row_field"]] = row_number
        if config["status_field"] is not None:
            output_row[config["status_field"]] = status
        output_rows.append(output_row)
    return output_rows
