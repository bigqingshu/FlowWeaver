from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _write_back_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "writeback_direction": NodeConfigFieldSpec(
                type="enum",
                title="Writeback Direction",
                default="source_to_target",
                enum=("source_to_target", "target_to_source"),
            ),
            "target_table": NodeConfigFieldSpec(
                type="string",
                title="Target Table",
                required=True,
            ),
            "source_table": NodeConfigFieldSpec(
                type="string",
                title="Source Table",
                description="Defaults to the input table logical name.",
            ),
            "target_type": NodeConfigFieldSpec(
                type="enum",
                title="Target Type",
                default="sqlite",
                enum=("run_table", "memory_table", "sqlite"),
            ),
            "write_mode": NodeConfigFieldSpec(
                type="enum",
                title="Write Mode",
                default="overwrite",
                enum=("create", "overwrite", "append"),
            ),
            "use_match_rules": NodeConfigFieldSpec(
                type="boolean",
                title="Use Match Rules",
                default=True,
            ),
            "match_rules": NodeConfigFieldSpec(
                type="array",
                title="Match Rules",
                item_type="object",
                description="Objects with source_field, target_field, and operator.",
            ),
            "field_mappings": NodeConfigFieldSpec(
                type="array",
                title="Field Mappings",
                required=True,
                item_type="object",
                description="Objects with source_field and target_field.",
            ),
            "overwrite_policy": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Policy",
                default="overwrite",
                enum=("overwrite", "empty_only", "skip_existing"),
            ),
            "source_empty_policy": NodeConfigFieldSpec(
                type="enum",
                title="Source Empty Policy",
                default="skip",
                enum=("skip", "write_empty", "clear_target"),
            ),
            "no_match_policy": NodeConfigFieldSpec(
                type="enum",
                title="No Match Policy",
                default="skip",
                enum=("skip", "insert", "error"),
            ),
            "multi_match_policy": NodeConfigFieldSpec(
                type="enum",
                title="Multi Match Policy",
                default="error",
                enum=("first", "skip", "error"),
            ),
            "duplicate_target_policy": NodeConfigFieldSpec(
                type="enum",
                title="Duplicate Target Policy",
                default="error",
                enum=("first", "skip", "error"),
            ),
            "enable_write": NodeConfigFieldSpec(
                type="boolean",
                title="Enable Write",
                default=False,
            ),
            "backup_before_write": NodeConfigFieldSpec(
                type="boolean",
                title="Backup Before Write",
                default=False,
            ),
            "output_preview_table": NodeConfigFieldSpec(
                type="boolean",
                title="Output Preview Table",
                default=True,
            ),
        }
    )
