from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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
