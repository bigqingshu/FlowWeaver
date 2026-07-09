from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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
