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
