from __future__ import annotations

from flowweaver.nodes.default_control_node_schemas import (
    _condition_flag_schema as _condition_flag_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _conditional_jump_schema as _conditional_jump_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _jump_anchor_schema as _jump_anchor_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _loop_judge_schema as _loop_judge_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _loop_start_schema as _loop_start_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _subworkflow_schema as _subworkflow_schema,
)
from flowweaver.nodes.default_control_node_schemas import (
    _unconditional_jump_schema as _unconditional_jump_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _batch_rename_files_schema as _batch_rename_files_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _list_files_schema as _list_files_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _plugin_node_schema as _plugin_node_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _publish_shared_tables_schema as _publish_shared_tables_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _read_shared_tables_schema as _read_shared_tables_schema,
)
from flowweaver.nodes.default_resource_node_schemas import (
    _sql_mapping_schema as _sql_mapping_schema,
)
from flowweaver.nodes.default_row_node_schemas import (
    _advanced_filter_rows_schema as _advanced_filter_rows_schema,
)
from flowweaver.nodes.default_row_node_schemas import (
    _copy_rows_schema as _copy_rows_schema,
)
from flowweaver.nodes.default_row_node_schemas import (
    _deduplicate_rows_schema as _deduplicate_rows_schema,
)
from flowweaver.nodes.default_row_node_schemas import (
    _delete_rows_schema as _delete_rows_schema,
)
from flowweaver.nodes.default_row_node_schemas import (
    _unpivot_rows_schema as _unpivot_rows_schema,
)
from flowweaver.nodes.default_text_node_schemas import (
    _extract_text_schema as _extract_text_schema,
)
from flowweaver.nodes.default_text_node_schemas import (
    _replace_text_schema as _replace_text_schema,
)
from flowweaver.nodes.default_write_node_schemas import (
    _save_memory_table_schema as _save_memory_table_schema,
)
from flowweaver.nodes.default_write_node_schemas import (
    _save_run_table_schema as _save_run_table_schema,
)
from flowweaver.nodes.default_write_node_schemas import (
    _write_back_table_schema as _write_back_table_schema,
)
from flowweaver.nodes.default_write_node_schemas import (
    _write_selected_columns_schema as _write_selected_columns_schema,
)
from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _generate_test_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "rows": NodeConfigFieldSpec(
                type="integer",
                title="Rows",
                required=True,
                default=3,
                minimum=0,
            ),
            "seed": NodeConfigFieldSpec(
                type="integer",
                title="Seed",
                default=0,
                minimum=0,
            ),
            "columns": NodeConfigFieldSpec(
                type="array",
                title="Columns",
                default=["row_id", "amount"],
                item_type="string",
                description=(
                    "Runtime also accepts column objects; first UI schema phase "
                    "treats this as a string list."
                ),
            ),
        }
    )


def _filter_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "field": NodeConfigFieldSpec(
                type="string",
                title="Field",
                required=True,
            ),
            "operator": NodeConfigFieldSpec(
                type="enum",
                title="Operator",
                required=True,
                enum=("EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"),
            ),
            "value": NodeConfigFieldSpec(
                type="object",
                title="Value",
                description=(
                    "Optional comparison value; runtime accepts JSON scalar values."
                ),
            ),
        }
    )


def _add_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "column_name": NodeConfigFieldSpec(
                type="string",
                title="Column Name",
                required=True,
                default="new_column",
            ),
            "default_value": NodeConfigFieldSpec(
                type="string",
                title="Default Value",
                default="",
                description=(
                    "Runtime parses this value according to data_type for "
                    "INTEGER, FLOAT, and BOOLEAN columns."
                ),
            ),
            "data_type": NodeConfigFieldSpec(
                type="enum",
                title="Data Type",
                required=True,
                default="TEXT",
                enum=("TEXT", "INTEGER", "FLOAT", "BOOLEAN"),
            ),
        }
    )


def _delete_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "columns": NodeConfigFieldSpec(
                type="array",
                title="Columns",
                required=True,
                item_type="string",
                description="Column names to remove from the output table.",
            ),
        }
    )


def _copy_column_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                required=True,
                default="new_field",
                enum=("new_field", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="copied_column",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                description="Required when output_mode is overwrite.",
            ),
            "trim_value": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Value",
                default=False,
            ),
            "empty_default": NodeConfigFieldSpec(
                type="object",
                title="Empty Default",
                description="Value used when the source value is null or empty.",
            ),
        }
    )


def _reorder_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "order": NodeConfigFieldSpec(
                type="array",
                title="Order",
                required=True,
                item_type="string",
                description="Target column order.",
            ),
            "missing_policy": NodeConfigFieldSpec(
                type="enum",
                title="Missing Policy",
                default="error",
                enum=("error", "skip", "warn"),
            ),
            "unlisted_policy": NodeConfigFieldSpec(
                type="enum",
                title="Unlisted Policy",
                default="append",
                enum=("append", "drop", "error"),
            ),
        }
    )


def _rename_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "mode": NodeConfigFieldSpec(
                type="enum",
                title="Mode",
                required=True,
                default="mappings",
                enum=("mappings", "prefix", "suffix", "replace"),
            ),
            "mappings": NodeConfigFieldSpec(
                type="array",
                title="Mappings",
                item_type="object",
                description=(
                    "Objects with source_field and target_field; old_name/new_name "
                    "aliases are also accepted."
                ),
            ),
            "prefix": NodeConfigFieldSpec(
                type="string",
                title="Prefix",
                default="",
            ),
            "suffix": NodeConfigFieldSpec(
                type="string",
                title="Suffix",
                default="",
            ),
            "replace_match": NodeConfigFieldSpec(
                type="string",
                title="Replace Match",
            ),
            "replace_value": NodeConfigFieldSpec(
                type="string",
                title="Replace Value",
                default="",
            ),
            "scope": NodeConfigFieldSpec(
                type="enum",
                title="Scope",
                default="all",
                enum=("all", "fields"),
            ),
            "scope_fields": NodeConfigFieldSpec(
                type="array",
                title="Scope Fields",
                item_type="string",
            ),
            "duplicate_policy": NodeConfigFieldSpec(
                type="enum",
                title="Duplicate Policy",
                default="error",
                enum=("error", "skip", "append_number"),
            ),
            "missing_policy": NodeConfigFieldSpec(
                type="enum",
                title="Missing Policy",
                default="error",
                enum=("error", "skip", "warn"),
            ),
            "trim_names": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Names",
                default=True,
            ),
        }
    )


def _fill_cells_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "manual_value": NodeConfigFieldSpec(
                type="object",
                title="Manual Value",
                description="Fallback literal value when value_source is omitted.",
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "direction": NodeConfigFieldSpec(
                type="enum",
                title="Direction",
                default="down",
                enum=("down", "up"),
            ),
            "count": NodeConfigFieldSpec(
                type="integer",
                title="Count",
                minimum=1,
            ),
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only"),
            ),
        }
    )


def _fill_range_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "start_field": NodeConfigFieldSpec(
                type="string",
                title="Start Field",
                required=True,
            ),
            "end_field": NodeConfigFieldSpec(
                type="string",
                title="End Field",
                description="Defaults to start_field when omitted.",
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "end_row": NodeConfigFieldSpec(
                type="integer",
                title="End Row",
                minimum=1,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "manual_value": NodeConfigFieldSpec(
                type="object",
                title="Manual Value",
                description="Fallback literal value when value_source is omitted.",
            ),
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only"),
            ),
            "max_cells": NodeConfigFieldSpec(
                type="integer",
                title="Max Cells",
                default=100000,
                minimum=1,
            ),
        }
    )


def _fill_sequence_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "direction": NodeConfigFieldSpec(
                type="enum",
                title="Direction",
                default="down",
                enum=("down", "up"),
            ),
            "start_value": NodeConfigFieldSpec(
                type="object",
                title="Start Value",
                default=1,
            ),
            "step": NodeConfigFieldSpec(
                type="object",
                title="Step",
                default=1,
            ),
            "end_mode": NodeConfigFieldSpec(
                type="enum",
                title="End Mode",
                default="to_end",
                enum=("to_end", "count", "end_row", "reference_non_empty"),
            ),
            "count": NodeConfigFieldSpec(
                type="integer",
                title="Count",
                minimum=1,
            ),
            "end_row": NodeConfigFieldSpec(
                type="integer",
                title="End Row",
                minimum=1,
            ),
            "reference_field": NodeConfigFieldSpec(
                type="string",
                title="Reference Field",
            ),
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only"),
            ),
            "zero_pad": NodeConfigFieldSpec(
                type="integer",
                title="Zero Pad",
                default=0,
                minimum=0,
            ),
            "prefix": NodeConfigFieldSpec(
                type="string",
                title="Prefix",
                default="",
            ),
            "suffix": NodeConfigFieldSpec(
                type="string",
                title="Suffix",
                default="",
            ),
        }
    )


def _lookup_matched_field_name_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "lookup_fields": NodeConfigFieldSpec(
                type="array",
                title="Lookup Fields",
                required=True,
                item_type="string",
            ),
            "match_mode": NodeConfigFieldSpec(
                type="enum",
                title="Match Mode",
                default="equals",
                enum=("equals",),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
                default="matched_field",
            ),
            "output_match_value": NodeConfigFieldSpec(
                type="boolean",
                title="Output Match Value",
                default=False,
            ),
            "match_value_field": NodeConfigFieldSpec(
                type="string",
                title="Match Value Field",
                default="matched_value",
            ),
            "output_match_row": NodeConfigFieldSpec(
                type="boolean",
                title="Output Match Row",
                default=False,
            ),
            "match_row_field": NodeConfigFieldSpec(
                type="string",
                title="Match Row Field",
                default="matched_row",
            ),
            "output_status": NodeConfigFieldSpec(
                type="boolean",
                title="Output Status",
                default=True,
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="match_status",
            ),
            "multi_match_policy": NodeConfigFieldSpec(
                type="enum",
                title="Multi Match Policy",
                default="first",
                enum=("first", "last", "error"),
            ),
            "no_match_value": NodeConfigFieldSpec(
                type="object",
                title="No Match Value",
                default="",
            ),
        }
    )


def _merge_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "fields": NodeConfigFieldSpec(
                type="array",
                title="Fields",
                required=True,
                item_type="string",
            ),
            "separators": NodeConfigFieldSpec(
                type="array",
                title="Separators",
                item_type="string",
                description=(
                    "One separator is repeated between all fields; field_count - 1 "
                    "separators are also supported."
                ),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
                default="merged",
            ),
            "skip_empty": NodeConfigFieldSpec(
                type="boolean",
                title="Skip Empty",
                default=False,
            ),
            "trim_value": NodeConfigFieldSpec(
                type="boolean",
                title="Trim Value",
                default=False,
            ),
            "empty_placeholder": NodeConfigFieldSpec(
                type="object",
                title="Empty Placeholder",
                default="",
            ),
            "conflict_mode": NodeConfigFieldSpec(
                type="enum",
                title="Conflict Mode",
                default="error",
                enum=("error", "overwrite"),
            ),
        }
    )


def _numeric_column_operation_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "operation": NodeConfigFieldSpec(
                type="enum",
                title="Operation",
                required=True,
                default="add",
                enum=(
                    "add",
                    "subtract",
                    "multiply",
                    "divide",
                    "sequence",
                    "round",
                    "floor",
                    "ceil",
                ),
            ),
            "operand_source": NodeConfigFieldSpec(
                type="enum",
                title="Operand Source",
                default="literal",
                enum=("literal", "row_field", "row_number", "sequence"),
            ),
            "operand_value": NodeConfigFieldSpec(
                type="object",
                title="Operand Value",
                default=0,
            ),
            "operand_field": NodeConfigFieldSpec(
                type="string",
                title="Operand Field",
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="overwrite",
                enum=("overwrite", "new_field"),
            ),
            "output_field": NodeConfigFieldSpec(
                type="string",
                title="Output Field",
            ),
            "non_number_policy": NodeConfigFieldSpec(
                type="enum",
                title="Non Number Policy",
                default="error",
                enum=("error", "empty", "fixed", "keep_original"),
            ),
            "non_number_fixed": NodeConfigFieldSpec(
                type="object",
                title="Non Number Fixed",
            ),
            "divide_zero_policy": NodeConfigFieldSpec(
                type="enum",
                title="Divide Zero Policy",
                default="error",
                enum=("error", "empty", "fixed", "keep_original"),
            ),
            "divide_zero_fixed": NodeConfigFieldSpec(
                type="object",
                title="Divide Zero Fixed",
            ),
            "decimal_places": NodeConfigFieldSpec(
                type="integer",
                title="Decimal Places",
                minimum=0,
            ),
            "range_mode": NodeConfigFieldSpec(
                type="enum",
                title="Range Mode",
                default="all",
                enum=("all", "row_range", "reference_non_empty"),
            ),
            "start_row": NodeConfigFieldSpec(
                type="integer",
                title="Start Row",
                default=1,
                minimum=1,
            ),
            "end_row": NodeConfigFieldSpec(
                type="integer",
                title="End Row",
                minimum=1,
            ),
            "reference_field": NodeConfigFieldSpec(
                type="string",
                title="Reference Field",
            ),
            "sequence_start": NodeConfigFieldSpec(
                type="object",
                title="Sequence Start",
                default=1,
            ),
            "sequence_step": NodeConfigFieldSpec(
                type="object",
                title="Sequence Step",
                default=1,
            ),
        }
    )


def _add_current_datetime_column_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                required=True,
                default="new_field",
                enum=("new_field", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="current_datetime",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "time_mode": NodeConfigFieldSpec(
                type="enum",
                title="Time Mode",
                default="fixed",
                enum=("fixed", "per_row"),
            ),
            "format_mode": NodeConfigFieldSpec(
                type="enum",
                title="Format Mode",
                default="iso",
                enum=("iso", "strftime", "template"),
            ),
            "template": NodeConfigFieldSpec(
                type="string",
                title="Template",
                default="{datetime}",
            ),
            "strftime_template": NodeConfigFieldSpec(
                type="string",
                title="Strftime Template",
                default="%Y-%m-%d %H:%M:%S",
            ),
        }
    )


def _parse_datetime_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "time_source_field": NodeConfigFieldSpec(
                type="string",
                title="Time Source Field",
            ),
            "use_separate_time_field": NodeConfigFieldSpec(
                type="boolean",
                title="Use Separate Time Field",
                default=False,
            ),
            "parse_type": NodeConfigFieldSpec(
                type="enum",
                title="Parse Type",
                default="datetime",
                enum=("date", "time", "datetime"),
            ),
            "input_structure": NodeConfigFieldSpec(
                type="enum",
                title="Input Structure",
                default="auto",
                enum=("auto", "strptime"),
            ),
            "input_format": NodeConfigFieldSpec(
                type="string",
                title="Input Format",
            ),
            "date_order": NodeConfigFieldSpec(
                type="enum",
                title="Date Order",
                default="ymd",
                enum=("ymd", "mdy", "dmy"),
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="new_field",
                enum=("new_field", "overwrite_source", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="parsed_datetime",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "output_template": NodeConfigFieldSpec(
                type="string",
                title="Output Template",
                default="%Y-%m-%d",
            ),
            "time_output_template": NodeConfigFieldSpec(
                type="string",
                title="Time Output Template",
                default="%H:%M:%S",
            ),
            "datetime_output_template": NodeConfigFieldSpec(
                type="string",
                title="DateTime Output Template",
                default="%Y-%m-%d %H:%M:%S",
            ),
            "output_status": NodeConfigFieldSpec(
                type="boolean",
                title="Output Status",
                default=True,
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="parse_status",
            ),
            "unmatched_mode": NodeConfigFieldSpec(
                type="enum",
                title="Unmatched Mode",
                default="empty",
                enum=("empty", "keep_original", "fixed"),
            ),
            "unmatched_fixed": NodeConfigFieldSpec(
                type="object",
                title="Unmatched Fixed",
            ),
        }
    )
