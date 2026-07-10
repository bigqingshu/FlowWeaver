from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec

_CONTINUE_LOOP_BRANCH = "continue_loop"
_END_LOOP_BRANCH = "end_loop"
_LOOP_BRANCHES = (_CONTINUE_LOOP_BRANCH, _END_LOOP_BRANCH)


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
                default=_CONTINUE_LOOP_BRANCH,
                enum=_LOOP_BRANCHES,
            ),
            "on_fail": NodeConfigFieldSpec(
                type="enum",
                title="On Fail",
                default=_END_LOOP_BRANCH,
                enum=_LOOP_BRANCHES,
            ),
            "result_table_name": NodeConfigFieldSpec(
                type="string",
                title="Result Table Name",
                default="loop_result",
            ),
        }
    )
