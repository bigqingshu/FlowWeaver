from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _batch_rename_files_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "path_field": NodeConfigFieldSpec(
                type="string",
                title="Path Field",
                required=True,
            ),
            "new_name_field": NodeConfigFieldSpec(
                type="string",
                title="New Name Field",
                required=True,
            ),
            "name_value_type": NodeConfigFieldSpec(
                type="enum",
                title="Name Value Type",
                default="file_name",
                enum=("file_name", "full_path"),
            ),
            "new_path_field": NodeConfigFieldSpec(
                type="string",
                title="New Path Field",
                default="new_path",
            ),
            "status_field": NodeConfigFieldSpec(
                type="string",
                title="Status Field",
                default="rename_status",
            ),
            "auto_append_ext": NodeConfigFieldSpec(
                type="boolean",
                title="Auto Append Extension",
                default=True,
            ),
            "allow_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Allow Directories",
                default=False,
            ),
            "create_target_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Create Target Directories",
                default=False,
            ),
            "conflict_mode": NodeConfigFieldSpec(
                type="enum",
                title="Conflict Mode",
                default="error",
                enum=("error", "skip", "overwrite", "append_number"),
            ),
            "actual_rename": NodeConfigFieldSpec(
                type="boolean",
                title="Actual Rename",
                default=False,
            ),
            "write_log": NodeConfigFieldSpec(
                type="boolean",
                title="Write Log",
                default=False,
            ),
            "log_path": NodeConfigFieldSpec(
                type="string",
                title="Log Path",
            ),
        }
    )
