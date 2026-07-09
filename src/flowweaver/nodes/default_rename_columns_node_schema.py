from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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
