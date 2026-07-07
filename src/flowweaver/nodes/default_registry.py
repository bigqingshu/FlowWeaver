from __future__ import annotations

from flowweaver.node_executor.builtin_fault import (
    DELAY_TEST_NODE_TYPE,
    FAULT_TEST_NODE_TYPE,
)
from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.builtin_sql import SQL_MAPPING_NODE_TYPE
from flowweaver.nodes.builtin_table import (
    ADD_COLUMNS_NODE_TYPE,
    ADVANCED_FILTER_ROWS_NODE_TYPE,
    COPY_COLUMN_NODE_TYPE,
    COPY_ROWS_NODE_TYPE,
    DEDUPLICATE_ROWS_NODE_TYPE,
    DELETE_COLUMNS_NODE_TYPE,
    DELETE_ROWS_NODE_TYPE,
    EXTRACT_TEXT_NODE_TYPE,
    FILL_CELLS_NODE_TYPE,
    FILL_RANGE_NODE_TYPE,
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
    REORDER_COLUMNS_NODE_TYPE,
    REPLACE_TEXT_NODE_TYPE,
    SAVE_MEMORY_TABLE_NODE_TYPE,
)
from flowweaver.nodes.registry import (
    NodeConfigFieldSpec,
    NodeConfigSchemaSpec,
    NodeDefinitionSpec,
    NodePortSpec,
    NodeRegistry,
)


def create_default_node_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for definition in default_node_definitions():
        registry.register(definition)
    return registry


def default_node_definitions() -> tuple[NodeDefinitionSpec, ...]:
    return (
        NodeDefinitionSpec(
            node_type=GENERATE_TEST_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Generate Test Table",
            output_ports=(NodePortSpec("out"),),
            config_schema=_generate_test_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILTER_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Filter Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_filter_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADD_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Add Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_add_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELETE_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Delete Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_delete_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=COPY_COLUMN_NODE_TYPE,
            node_version="1.0",
            display_name="Copy Column",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_copy_column_schema(),
        ),
        NodeDefinitionSpec(
            node_type=REORDER_COLUMNS_NODE_TYPE,
            node_version="1.0",
            display_name="Reorder Columns",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_reorder_columns_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILL_CELLS_NODE_TYPE,
            node_version="1.0",
            display_name="Fill Cells",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_fill_cells_schema(),
        ),
        NodeDefinitionSpec(
            node_type=FILL_RANGE_NODE_TYPE,
            node_version="1.0",
            display_name="Fill Range",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_fill_range_schema(),
        ),
        NodeDefinitionSpec(
            node_type=REPLACE_TEXT_NODE_TYPE,
            node_version="1.0",
            display_name="Replace Text",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_replace_text_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELETE_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Delete Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_delete_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=COPY_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Copy Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_copy_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DEDUPLICATE_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Deduplicate Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_deduplicate_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=ADVANCED_FILTER_ROWS_NODE_TYPE,
            node_version="1.0",
            display_name="Advanced Filter Rows",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_advanced_filter_rows_schema(),
        ),
        NodeDefinitionSpec(
            node_type=EXTRACT_TEXT_NODE_TYPE,
            node_version="1.0",
            display_name="Extract Text",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_extract_text_schema(),
        ),
        NodeDefinitionSpec(
            node_type=LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
            node_version="1.0",
            display_name="Lookup Matched Field Name",
            input_ports=(
                NodePortSpec("in", required=True),
                NodePortSpec("lookup", required=True),
            ),
            output_ports=(NodePortSpec("out"),),
            config_schema=_lookup_matched_field_name_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SAVE_MEMORY_TABLE_NODE_TYPE,
            node_version="1.0",
            display_name="Save Memory Table",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"), NodePortSpec("memory")),
            config_schema=_save_memory_table_schema(),
        ),
        NodeDefinitionSpec(
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_version="1.0",
            display_name="Publish Shared Tables",
            input_ports=(NodePortSpec("in", required=True),),
            output_ports=(NodePortSpec("out"),),
            config_schema=_publish_shared_tables_schema(),
        ),
        NodeDefinitionSpec(
            node_type=READ_SHARED_TABLES_NODE_TYPE,
            node_version="1.0",
            display_name="Read Shared Tables",
            output_ports=(NodePortSpec("out"),),
            config_schema=_read_shared_tables_schema(),
        ),
        NodeDefinitionSpec(
            node_type=SQL_MAPPING_NODE_TYPE,
            node_version="1.0",
            display_name="SQL Mapping",
            output_ports=(NodePortSpec("out"),),
            config_schema=_sql_mapping_schema(),
        ),
        NodeDefinitionSpec(
            node_type=DELAY_TEST_NODE_TYPE,
            node_version="1.0",
            display_name="Delay Test",
            output_ports=(NodePortSpec("out"),),
        ),
        NodeDefinitionSpec(
            node_type=FAULT_TEST_NODE_TYPE,
            node_version="1.0",
            display_name="Fault Test",
            output_ports=(NodePortSpec("out"),),
        ),
    )


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


def _delete_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "delete_mode": NodeConfigFieldSpec(
                type="enum",
                title="Delete Mode",
                required=True,
                default="row_numbers",
                enum=("row_numbers", "row_range", "condition", "empty"),
            ),
            "row_spec": NodeConfigFieldSpec(
                type="array",
                title="Row Spec",
                item_type="integer",
                description="1-based row numbers to delete when mode is row_numbers.",
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
            "condition_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Field",
            ),
            "condition_op": NodeConfigFieldSpec(
                type="enum",
                title="Condition Operator",
                default="EQ",
                enum=("EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"),
            ),
            "condition_value": NodeConfigFieldSpec(
                type="object",
                title="Condition Value",
            ),
            "condition_value_source": NodeConfigFieldSpec(
                type="object",
                title="Condition Value Source",
                description=(
                    "Literal values or row_field objects are supported by runtime."
                ),
            ),
            "condition_value_field": NodeConfigFieldSpec(
                type="string",
                title="Condition Value Field",
                description="Shortcut for same-row field comparison.",
            ),
            "case_sensitive": NodeConfigFieldSpec(
                type="boolean",
                title="Case Sensitive",
                default=True,
            ),
            "empty_mode": NodeConfigFieldSpec(
                type="enum",
                title="Empty Mode",
                default="all_fields",
                enum=("all_fields", "field"),
            ),
            "empty_field": NodeConfigFieldSpec(
                type="string",
                title="Empty Field",
            ),
        }
    )


def _copy_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_row": NodeConfigFieldSpec(
                type="integer",
                title="Source Row",
                required=True,
                default=1,
                minimum=1,
            ),
            "copy_count": NodeConfigFieldSpec(
                type="integer",
                title="Copy Count",
                required=True,
                default=1,
                minimum=0,
            ),
            "insert_mode": NodeConfigFieldSpec(
                type="enum",
                title="Insert Mode",
                required=True,
                default="append",
                enum=("append", "prepend", "before_row", "after_row"),
            ),
            "insert_row": NodeConfigFieldSpec(
                type="integer",
                title="Insert Row",
                default=1,
                minimum=1,
            ),
            "max_output_rows": NodeConfigFieldSpec(
                type="integer",
                title="Max Output Rows",
                default=100000,
                minimum=1,
            ),
        }
    )


def _deduplicate_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "dedupe_mode": NodeConfigFieldSpec(
                type="enum",
                title="Dedupe Mode",
                required=True,
                default="key_fields",
                enum=("key_fields", "entire_row"),
            ),
            "key_fields": NodeConfigFieldSpec(
                type="array",
                title="Key Fields",
                item_type="string",
                description="Field names used as the duplicate key.",
            ),
            "trim": NodeConfigFieldSpec(
                type="boolean",
                title="Trim",
                default=False,
            ),
            "ignore_case": NodeConfigFieldSpec(
                type="boolean",
                title="Ignore Case",
                default=False,
            ),
            "empty_key_policy": NodeConfigFieldSpec(
                type="enum",
                title="Empty Key Policy",
                default="include",
                enum=("include", "skip"),
            ),
            "keep_policy": NodeConfigFieldSpec(
                type="enum",
                title="Keep Policy",
                default="first",
                enum=("first", "last", "all"),
            ),
            "output_mode": NodeConfigFieldSpec(
                type="enum",
                title="Output Mode",
                default="dedupe",
                enum=("dedupe", "mark"),
            ),
            "add_marker_columns": NodeConfigFieldSpec(
                type="boolean",
                title="Add Marker Columns",
                default=False,
            ),
            "duplicate_group_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Group Field",
                default="_duplicate_group",
            ),
            "duplicate_status_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Status Field",
                default="_duplicate_status",
            ),
            "duplicate_index_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Index Field",
                default="_duplicate_index",
            ),
            "duplicate_count_field": NodeConfigFieldSpec(
                type="string",
                title="Duplicate Count Field",
                default="_duplicate_count",
            ),
            "keep_flag_field": NodeConfigFieldSpec(
                type="string",
                title="Keep Flag Field",
                default="_keep_row",
            ),
        }
    )


def _advanced_filter_rows_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "logic": NodeConfigFieldSpec(
                type="enum",
                title="Logic",
                default="and",
                enum=("and", "or"),
            ),
            "conditions": NodeConfigFieldSpec(
                type="array",
                title="Conditions",
                item_type="object",
                description=(
                    "Each condition supports field, operator, value, "
                    "value_source, value_field, and case_sensitive."
                ),
            ),
            "output_fields": NodeConfigFieldSpec(
                type="array",
                title="Output Fields",
                item_type="string",
            ),
            "result_limit": NodeConfigFieldSpec(
                type="integer",
                title="Result Limit",
                minimum=0,
            ),
            "max_intermediate": NodeConfigFieldSpec(
                type="integer",
                title="Max Intermediate",
                minimum=1,
            ),
            "remove_duplicates": NodeConfigFieldSpec(
                type="boolean",
                title="Remove Duplicates",
                default=False,
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


def _save_memory_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "table_name": NodeConfigFieldSpec(
                type="string",
                title="Table Name",
                required=True,
                default="memory_table",
            ),
            "mode": NodeConfigFieldSpec(
                type="enum",
                title="Mode",
                required=True,
                default="overwrite",
                enum=("overwrite",),
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
