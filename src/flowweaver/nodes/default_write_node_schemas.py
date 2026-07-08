from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


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


def _save_run_table_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "transit_name": NodeConfigFieldSpec(
                type="string",
                title="Transit Name",
                default="run_table",
                description="Workflow-run local name for this intermediate table.",
            ),
            "save_memory": NodeConfigFieldSpec(
                type="boolean",
                title="Save Memory",
                default=True,
                description=(
                    "When false, runtime only passes the current input table through."
                ),
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
