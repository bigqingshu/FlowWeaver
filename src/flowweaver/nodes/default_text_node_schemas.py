from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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
