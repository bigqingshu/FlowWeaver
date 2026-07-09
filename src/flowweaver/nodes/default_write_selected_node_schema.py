from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _write_selected_columns_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "source_type": NodeConfigFieldSpec(
                type="enum",
                title="Source Type",
                default="current_table",
                enum=("current_table", "run_table", "sqlite"),
            ),
            "selected_fields": NodeConfigFieldSpec(
                type="array",
                title="Selected Fields",
                required=True,
                item_type="string",
            ),
            "target_type": NodeConfigFieldSpec(
                type="enum",
                title="Target Type",
                default="run_table",
                enum=("run_table", "memory_table", "sqlite"),
            ),
            "target_table": NodeConfigFieldSpec(
                type="string",
                title="Target Table",
                description=(
                    "Required for sqlite targets; also accepted for run tables."
                ),
            ),
            "target_transit_table": NodeConfigFieldSpec(
                type="string",
                title="Target Transit Table",
                description="Workflow-run local target name.",
            ),
            "write_mode": NodeConfigFieldSpec(
                type="enum",
                title="Write Mode",
                default="overwrite",
                enum=("create", "overwrite", "append", "upsert"),
            ),
            "field_name_mode": NodeConfigFieldSpec(
                type="enum",
                title="Field Name Mode",
                default="keep",
                enum=("keep", "prefix", "suffix", "mapping"),
            ),
            "field_prefix": NodeConfigFieldSpec(
                type="string",
                title="Field Prefix",
                default="",
            ),
            "field_suffix": NodeConfigFieldSpec(
                type="string",
                title="Field Suffix",
                default="",
            ),
            "field_mappings": NodeConfigFieldSpec(
                type="array",
                title="Field Mappings",
                item_type="object",
                description="Objects with source_field and target_field.",
            ),
            "overwrite_rule": NodeConfigFieldSpec(
                type="enum",
                title="Overwrite Rule",
                default="all",
                enum=("all", "empty_only", "skip_existing"),
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
        }
    )
