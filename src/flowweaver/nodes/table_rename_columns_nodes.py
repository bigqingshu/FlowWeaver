from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import RENAME_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError

class RenameColumnsNodeHandler:
    node_type = RENAME_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        proposed_names = _rename_columns_proposed_names(
            task.config,
            input_ref=input_ref,
        )
        input_names = [field.name for field in input_ref.schema]
        output_names = _rename_columns_apply_duplicate_policy(
            input_names,
            proposed_names,
            duplicate_policy=_enum_config(
                task.config,
                "duplicate_policy",
                default="error",
                allowed={"error", "skip", "append_number"},
                node_type=self.node_type,
            ),
        )
        schema = _rename_columns_schema(input_ref.schema, output_names)
        source_to_output = {
            field.name: output_name
            for field, output_name in zip(input_ref.schema, output_names, strict=True)
        }

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    output_rows.append(
                        {
                            source_to_output[field.name]: row.get(field.name)
                            for field in input_ref.schema
                        }
                    )
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=output_batches(),
        )


def _rename_columns_proposed_names(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> list[str]:
    mode = _enum_config(
        config,
        "mode",
        default="mappings",
        allowed={"mappings", "prefix", "suffix", "replace"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    trim_names = _bool_config(config, "trim_names", default=True)
    input_names = [field.name for field in input_ref.schema]
    missing_policy = _enum_config(
        config,
        "missing_policy",
        default="error",
        allowed={"error", "skip", "warn"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    rename_map: dict[str, str] = {}
    if mode == "mappings":
        rename_map = _rename_columns_mapping_config(
            config,
            input_ref=input_ref,
            missing_policy=missing_policy,
            trim_names=trim_names,
        )
    else:
        scope_fields = _rename_columns_scope_fields(
            config,
            input_ref=input_ref,
            missing_policy=missing_policy,
        )
        if mode == "prefix":
            prefix = _optional_string_config(
                config,
                "prefix",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {field: f"{prefix}{field}" for field in scope_fields}
        elif mode == "suffix":
            suffix = _optional_string_config(
                config,
                "suffix",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {field: f"{field}{suffix}" for field in scope_fields}
        else:
            match = _node_string_config(
                config,
                "replace_match",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            replace_value = _optional_string_config(
                config,
                "replace_value",
                node_type=RENAME_COLUMNS_NODE_TYPE,
            )
            rename_map = {
                field: field.replace(match, replace_value)
                for field in scope_fields
            }
    proposed_names: list[str] = []
    for field_name in input_names:
        proposed = rename_map.get(field_name, field_name)
        if trim_names:
            proposed = proposed.strip()
        if not proposed:
            raise _NodeValidationError("RenameColumnsNode output field name is empty")
        proposed_names.append(proposed)
    return proposed_names


def _rename_columns_mapping_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    missing_policy: str,
    trim_names: bool,
) -> dict[str, str]:
    value = config.get("mappings")
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "RenameColumnsNode config.mappings must be a non-empty list"
        )
    input_names = {field.name for field in input_ref.schema}
    mappings: dict[str, str] = {}
    missing_fields: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            raise _NodeValidationError(
                "RenameColumnsNode config.mappings must contain objects"
            )
        source_field = _rename_mapping_string(
            item,
            keys=("source_field", "old_name", "old_field", "source"),
            message="RenameColumnsNode mappings.source_field is required",
        )
        target_field = _rename_mapping_string(
            item,
            keys=("target_field", "new_name", "new_field", "target"),
            message="RenameColumnsNode mappings.target_field is required",
        )
        if trim_names:
            target_field = target_field.strip()
        if not target_field:
            raise _NodeValidationError(
                "RenameColumnsNode mappings.target_field is required"
            )
        if source_field in mappings:
            raise _NodeValidationError(
                f"RenameColumnsNode duplicate mapping source: {source_field}"
            )
        if source_field not in input_names:
            missing_fields.append(source_field)
            continue
        mappings[source_field] = target_field
    if missing_fields and missing_policy == "error":
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return mappings


def _rename_mapping_string(
    item: dict[str, Any],
    *,
    keys: tuple[str, ...],
    message: str,
) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise _NodeValidationError(message)


def _rename_columns_scope_fields(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    missing_policy: str,
) -> list[str]:
    scope = _enum_config(
        config,
        "scope",
        default="all",
        allowed={"all", "fields"},
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    if scope == "all":
        return [field.name for field in input_ref.schema]
    scope_fields = _string_list_config(
        config,
        "scope_fields",
        node_type=RENAME_COLUMNS_NODE_TYPE,
    )
    input_names = {field.name for field in input_ref.schema}
    missing_fields = [
        field
        for field in scope_fields
        if field not in input_names
    ]
    if missing_fields and missing_policy == "error":
        raise _NodeValidationError(
            f"Fields do not exist: {', '.join(missing_fields)}"
        )
    return [
        field
        for field in scope_fields
        if field in input_names
    ]


def _rename_columns_apply_duplicate_policy(
    input_names: list[str],
    proposed_names: list[str],
    *,
    duplicate_policy: str,
) -> list[str]:
    duplicates = {
        name
        for name in proposed_names
        if proposed_names.count(name) > 1
    }
    if not duplicates:
        return proposed_names
    if duplicate_policy == "error":
        raise _NodeValidationError(
            f"RenameColumnsNode output fields are duplicated: "
            f"{', '.join(sorted(duplicates))}"
        )
    if duplicate_policy == "skip":
        return [
            input_name if proposed_name in duplicates and proposed_name != input_name
            else proposed_name
            for input_name, proposed_name in zip(
                input_names,
                proposed_names,
                strict=True,
            )
        ]
    output_names: list[str] = []
    used_names: set[str] = set()
    for proposed_name in proposed_names:
        candidate = proposed_name
        suffix_index = 2
        while candidate in used_names:
            candidate = f"{proposed_name}_{suffix_index}"
            suffix_index += 1
        output_names.append(candidate)
        used_names.add(candidate)
    return output_names


def _rename_columns_schema(
    schema: list[FieldSchemaModel],
    output_names: list[str],
) -> list[FieldSchemaModel]:
    return [
        field.model_copy(update={"name": output_name, "ordinal": ordinal})
        for ordinal, (field, output_name) in enumerate(
            zip(schema, output_names, strict=True)
        )
    ]

