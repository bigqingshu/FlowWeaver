from __future__ import annotations

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


def _replace_text_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
                required=True,
            ),
            "match_mode": NodeConfigFieldSpec(
                type="enum",
                title="Match Mode",
                required=True,
                default="contains",
                enum=(
                    "contains",
                    "equals",
                    "starts_with",
                    "ends_with",
                    "regex",
                    "is_empty",
                    "is_not_empty",
                ),
            ),
            "match_value": NodeConfigFieldSpec(
                type="object",
                title="Match Value",
            ),
            "replace_value": NodeConfigFieldSpec(
                type="object",
                title="Replace Value",
            ),
            "match_value_source": NodeConfigFieldSpec(
                type="object",
                title="Match Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "replace_value_source": NodeConfigFieldSpec(
                type="object",
                title="Replace Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "replace_mode": NodeConfigFieldSpec(
                type="enum",
                title="Replace Mode",
                default="partial",
                enum=("partial", "whole_cell"),
            ),
            "case_sensitive": NodeConfigFieldSpec(
                type="boolean",
                title="Case Sensitive",
                default=True,
            ),
            "replace_count": NodeConfigFieldSpec(
                type="integer",
                title="Replace Count",
                default=0,
                minimum=0,
            ),
            "skip_empty_match_value": NodeConfigFieldSpec(
                type="boolean",
                title="Skip Empty Match Value",
                default=True,
            ),
        }
    )


def _extract_text_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_field": NodeConfigFieldSpec(
                type="string",
                title="Source Field",
                required=True,
            ),
            "method": NodeConfigFieldSpec(
                type="enum",
                title="Method",
                required=True,
                default="regex",
                enum=("regex", "position", "left", "right", "delimiter", "between"),
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                required=True,
                default="new_field",
                enum=("new_field", "overwrite_source", "overwrite"),
            ),
            "new_field": NodeConfigFieldSpec(
                type="string",
                title="New Field",
                default="extracted",
            ),
            "target_field": NodeConfigFieldSpec(
                type="string",
                title="Target Field",
            ),
            "unmatched_mode": NodeConfigFieldSpec(
                type="enum",
                title="Unmatched Mode",
                default="empty",
                enum=("empty", "keep_original", "fixed", "skip_row"),
            ),
            "regex_pattern": NodeConfigFieldSpec(
                type="string",
                title="Regex Pattern",
            ),
            "regex_group": NodeConfigFieldSpec(
                type="integer",
                title="Regex Group",
                default=0,
                minimum=0,
            ),
            "start_pos": NodeConfigFieldSpec(
                type="integer",
                title="Start Position",
                default=1,
                minimum=0,
            ),
            "extract_len": NodeConfigFieldSpec(
                type="integer",
                title="Extract Length",
                minimum=1,
            ),
            "position_base": NodeConfigFieldSpec(
                type="enum",
                title="Position Base",
                default="one",
                enum=("zero", "one"),
            ),
            "delimiter": NodeConfigFieldSpec(
                type="string",
                title="Delimiter",
            ),
            "part_index": NodeConfigFieldSpec(
                type="integer",
                title="Part Index",
                default=1,
                minimum=0,
            ),
            "before_key": NodeConfigFieldSpec(
                type="string",
                title="Before Key",
            ),
            "after_key": NodeConfigFieldSpec(
                type="string",
                title="After Key",
            ),
            "strip_result": NodeConfigFieldSpec(
                type="boolean",
                title="Strip Result",
                default=False,
            ),
            "rule_value_source": NodeConfigFieldSpec(
                type="object",
                title="Rule Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "unmatched_value_source": NodeConfigFieldSpec(
                type="object",
                title="Unmatched Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "unmatched_value": NodeConfigFieldSpec(
                type="object",
                title="Unmatched Value",
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


def _condition_flag_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "flag_name": NodeConfigFieldSpec(
                type="string",
                title="Flag Name",
                required=True,
                default="condition",
            ),
            "condition_type": NodeConfigFieldSpec(
                type="enum",
                title="Condition Type",
                required=True,
                default="row_count",
                enum=("row_count", "field_exists", "field_value"),
            ),
            "field": NodeConfigFieldSpec(
                type="string",
                title="Field",
            ),
            "operator": NodeConfigFieldSpec(
                type="enum",
                title="Operator",
                default="GE",
                enum=(
                    "EQ",
                    "NE",
                    "GT",
                    "GE",
                    "LT",
                    "LE",
                    "CONTAINS",
                    "IS_NULL",
                    "IS_EMPTY",
                ),
            ),
            "value": NodeConfigFieldSpec(
                type="object",
                title="Value",
                default=1,
            ),
            "value_source": NodeConfigFieldSpec(
                type="object",
                title="Value Source",
                description=(
                    "Literal values or same-row field objects are supported by "
                    "runtime."
                ),
            ),
            "value_field": NodeConfigFieldSpec(
                type="string",
                title="Value Field",
                description="Shortcut for same-row field comparison.",
            ),
            "aggregation": NodeConfigFieldSpec(
                type="enum",
                title="Aggregation",
                default="any",
                enum=("any", "all", "first", "count"),
            ),
            "case_sensitive": NodeConfigFieldSpec(
                type="boolean",
                title="Case Sensitive",
                default=True,
            ),
            "true_value": NodeConfigFieldSpec(
                type="object",
                title="True Value",
                default=True,
            ),
            "false_value": NodeConfigFieldSpec(
                type="object",
                title="False Value",
                default=False,
            ),
        }
    )


def _jump_anchor_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "anchor_name": NodeConfigFieldSpec(
                type="string",
                title="Anchor Name",
                required=True,
                default="anchor",
            ),
            "description": NodeConfigFieldSpec(
                type="string",
                title="Description",
                default="",
            ),
            "allow_multiple_hits": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Multiple Hits",
                default=False,
                description=(
                    "Recorded for future real scheduling; preview execution only "
                    "publishes a control status table."
                ),
            ),
        }
    )


def _unconditional_jump_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "target_mode": NodeConfigFieldSpec(
                type="enum",
                title="Target Mode",
                required=True,
                default="anchor",
                enum=("anchor", "node"),
            ),
            "target_anchor": NodeConfigFieldSpec(
                type="string",
                title="Target Anchor",
                description="Required when target_mode is anchor.",
            ),
            "target_node_id": NodeConfigFieldSpec(
                type="string",
                title="Target Node ID",
                description="Required when target_mode is node.",
            ),
            "reason": NodeConfigFieldSpec(
                type="string",
                title="Reason",
                default="",
            ),
        }
    )


def _conditional_jump_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "condition_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Field",
                required=True,
                default="result",
            ),
            "true_target_mode": NodeConfigFieldSpec(
                type="enum",
                title="True Target Mode",
                default="anchor",
                enum=("anchor", "node"),
            ),
            "true_target_anchor": NodeConfigFieldSpec(
                type="string",
                title="True Target Anchor",
                description="Required when the true branch targets an anchor.",
            ),
            "true_target_node_id": NodeConfigFieldSpec(
                type="string",
                title="True Target Node ID",
                description="Required when the true branch targets a node.",
            ),
            "false_target_mode": NodeConfigFieldSpec(
                type="enum",
                title="False Target Mode",
                default="anchor",
                enum=("anchor", "node"),
            ),
            "false_target_anchor": NodeConfigFieldSpec(
                type="string",
                title="False Target Anchor",
                description="Required when the false branch targets an anchor.",
            ),
            "false_target_node_id": NodeConfigFieldSpec(
                type="string",
                title="False Target Node ID",
                description="Required when the false branch targets a node.",
            ),
            "default_branch": NodeConfigFieldSpec(
                type="enum",
                title="Default Branch",
                default="false",
                enum=("true", "false"),
                description=(
                    "Branch used when the condition value is missing or cannot "
                    "be parsed as true/false."
                ),
            ),
        }
    )


def _loop_start_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "loop_id": NodeConfigFieldSpec(
                type="string",
                title="Loop ID",
                required=True,
                default="loop",
            ),
            "source_type": NodeConfigFieldSpec(
                type="enum",
                title="Source Type",
                default="current_table",
                enum=("current_table", "named_table", "sqlite"),
            ),
            "fields": NodeConfigFieldSpec(
                type="array",
                title="Fields",
                item_type="string",
            ),
            "max_loop_count": NodeConfigFieldSpec(
                type="integer",
                title="Max Loop Count",
                default=1,
                minimum=1,
            ),
            "output_current_as_table": NodeConfigFieldSpec(
                type="boolean",
                title="Output Current As Table",
                default=True,
            ),
            "current_table_name": NodeConfigFieldSpec(
                type="string",
                title="Current Table Name",
                default="current_loop_item",
            ),
        }
    )


def _loop_judge_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "loop_id": NodeConfigFieldSpec(
                type="string",
                title="Loop ID",
                required=True,
                default="loop",
            ),
            "condition_mode": NodeConfigFieldSpec(
                type="enum",
                title="Condition Mode",
                default="always_success",
                enum=("always_success", "row_count", "field_value"),
            ),
            "condition_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Field",
            ),
            "condition_op": NodeConfigFieldSpec(
                type="enum",
                title="Condition Operator",
                default="EQ",
                enum=(
                    "EQ",
                    "NE",
                    "GT",
                    "GE",
                    "LT",
                    "LE",
                    "CONTAINS",
                    "IS_NULL",
                    "IS_EMPTY",
                ),
            ),
            "condition_value": NodeConfigFieldSpec(
                type="object",
                title="Condition Value",
            ),
            "condition_value_source": NodeConfigFieldSpec(
                type="object",
                title="Condition Value Source",
            ),
            "condition_value_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Value Field",
            ),
            "on_success": NodeConfigFieldSpec(
                type="enum",
                title="On Success",
                default="continue_loop",
                enum=("continue_loop", "end_loop"),
            ),
            "on_fail": NodeConfigFieldSpec(
                type="enum",
                title="On Fail",
                default="end_loop",
                enum=("continue_loop", "end_loop"),
            ),
            "result_table_name": NodeConfigFieldSpec(
                type="string",
                title="Result Table Name",
                default="loop_result",
            ),
        }
    )


def _subworkflow_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "group_name": NodeConfigFieldSpec(
                type="string",
                title="Group Name",
                required=True,
                default="subworkflow",
            ),
            "subworkflow_ref": NodeConfigFieldSpec(
                type="string",
                title="Subworkflow Ref",
                description=(
                    "Optional workflow/template identifier recorded by the "
                    "preview plan."
                ),
            ),
            "nodes": NodeConfigFieldSpec(
                type="array",
                title="Nodes",
                item_type="object",
                description="Embedded child-node definitions for preview metadata.",
            ),
            "input_source_type": NodeConfigFieldSpec(
                type="enum",
                title="Input Source Type",
                default="current_table",
                enum=("current_table", "named_inputs", "none"),
            ),
            "input_mapping": NodeConfigFieldSpec(
                type="array",
                title="Input Mapping",
                item_type="object",
                description="Objects describing parent input to child input mapping.",
            ),
            "input_defaults": NodeConfigFieldSpec(
                type="object",
                title="Input Defaults",
            ),
            "missing_input_policy": NodeConfigFieldSpec(
                type="enum",
                title="Missing Input Policy",
                default="error",
                enum=("error", "skip", "use_default"),
            ),
            "transit_scope": NodeConfigFieldSpec(
                type="enum",
                title="Transit Scope",
                default="isolated",
                enum=("isolated", "inherited"),
            ),
            "allow_loop_nodes": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Loop Nodes",
                default=False,
            ),
            "main_output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Main Output Mode",
                default="status_only",
                enum=("status_only", "passthrough", "named_outputs"),
            ),
            "save_to_transit": NodeConfigFieldSpec(
                type="boolean",
                title="Save To Transit",
                default=False,
            ),
            "output_transit_name": NodeConfigFieldSpec(
                type="string",
                title="Output Transit Name",
                description="Required when save_to_transit is true.",
            ),
        }
    )


def _list_files_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "directory": NodeConfigFieldSpec(
                type="string",
                title="Directory",
                required=True,
            ),
            "recursive": NodeConfigFieldSpec(
                type="boolean",
                title="Recursive",
                default=False,
            ),
            "include_files": NodeConfigFieldSpec(
                type="boolean",
                title="Include Files",
                default=True,
            ),
            "include_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Include Directories",
                default=False,
            ),
            "include_hidden": NodeConfigFieldSpec(
                type="boolean",
                title="Include Hidden",
                default=False,
            ),
            "extensions": NodeConfigFieldSpec(
                type="array",
                title="Extensions",
                item_type="string",
                description="Optional file extensions, with or without leading dots.",
            ),
            "name_contains": NodeConfigFieldSpec(
                type="string",
                title="Name Contains",
                default="",
            ),
            "glob_pattern": NodeConfigFieldSpec(
                type="string",
                title="Glob Pattern",
                default="*",
            ),
            "max_files": NodeConfigFieldSpec(
                type="integer",
                title="Max Files",
                default=10000,
                minimum=1,
            ),
        }
    )


def _batch_rename_files_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "path_field": NodeConfigFieldSpec(
                type="string",
                title="Path Field",
                required=True,
            ),
            "new_name_field": NodeConfigFieldSpec(
                type="string",
                title="New Name Field",
                required=True,
            ),
            "name_value_type": NodeConfigFieldSpec(
                type="enum",
                title="Name Value Type",
                default="file_name",
                enum=("file_name", "full_path"),
            ),
            "new_path_field": NodeConfigFieldSpec(
                type="string",
                title="New Path Field",
                default="new_path",
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="rename_status",
            ),
            "auto_append_ext": NodeConfigFieldSpec(
                type="boolean",
                title="Auto Append Extension",
                default=True,
            ),
            "allow_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Directories",
                default=False,
            ),
            "create_target_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Create Target Directories",
                default=False,
            ),
            "conflict_mode": NodeConfigFieldSpec(
                type="enum",
                title="Conflict Mode",
                default="error",
                enum=("error", "skip", "overwrite", "append_number"),
            ),
            "actual_rename": NodeConfigFieldSpec(
                type="boolean",
                title="Actual Rename",
                default=False,
            ),
            "write_log": NodeConfigFieldSpec(
                type="boolean",
                title="Write Log",
                default=False,
            ),
            "log_path": NodeConfigFieldSpec(
                type="string",
                title="Log Path",
            ),
        }
    )


def _plugin_node_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "plugin_id": NodeConfigFieldSpec(
                type="string",
                title="Plugin ID",
                required=True,
            ),
            "plugin_version": NodeConfigFieldSpec(
                type="string",
                title="Plugin Version",
            ),
            "params": NodeConfigFieldSpec(
                type="object",
                title="Params",
                description="Plugin parameter object.",
            ),
            "input_bindings": NodeConfigFieldSpec(
                type="object",
                title="Input Bindings",
                description="Plugin input binding object.",
            ),
            "output_bindings": NodeConfigFieldSpec(
                type="object",
                title="Output Bindings",
                description="Plugin output binding object.",
            ),
            "plugin_manifest": NodeConfigFieldSpec(
                type="object",
                title="Plugin Manifest",
                description="Plugin manifest object used for preflight validation.",
            ),
            "execution_mode": NodeConfigFieldSpec(
                type="enum",
                title="Execution Mode",
                default="external_process",
                enum=("in_process", "external_process"),
            ),
            "allow_external_actions": NodeConfigFieldSpec(
                type="boolean",
                title="Allow External Actions",
                default=False,
            ),
            "enable_execute": NodeConfigFieldSpec(
                type="boolean",
                title="Enable Execute",
                default=False,
            ),
        }
    )


def _sql_mapping_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "database_path": NodeConfigFieldSpec(
                type="string",
                title="Database Path",
                required=True,
            ),
            "table_name": NodeConfigFieldSpec(
                type="string",
                title="Table Name",
                description="Use table_name or query, not both.",
            ),
            "query": NodeConfigFieldSpec(
                type="string",
                title="Query",
                description=(
                    "Read-only SELECT query. Use query or table_name, not both."
                ),
            ),
            "logical_table_id": NodeConfigFieldSpec(
                type="string",
                title="Logical Table",
                description="Optional workflow-facing table name.",
            ),
            "schema": NodeConfigFieldSpec(
                type="array",
                title="Schema",
                item_type="object",
                description=(
                    "Optional list of field objects. When omitted, runtime infers "
                    "table schema where possible."
                ),
            ),
        }
    )


def _publish_shared_tables_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "share_name": NodeConfigFieldSpec(
                type="string",
                title="Share Name",
                required=True,
            ),
            "export_names": NodeConfigFieldSpec(
                type="array",
                title="Export Names",
                required=True,
                item_type="string",
            ),
            "retention_seconds": NodeConfigFieldSpec(
                type="integer",
                title="Retention Seconds",
                minimum=1,
            ),
        }
    )


def _read_shared_tables_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "share_name": NodeConfigFieldSpec(
                type="string",
                title="Share Name",
                required=True,
            ),
            "version_policy": NodeConfigFieldSpec(
                type="enum",
                title="Version Policy",
                required=True,
                enum=("LATEST", "EXACT_VERSION"),
            ),
            "exact_version": NodeConfigFieldSpec(
                type="integer",
                title="Exact Version",
                minimum=1,
            ),
            "selected_members": NodeConfigFieldSpec(
                type="array",
                title="Selected Members",
                item_type="string",
            ),
        }
    )
