from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def rename_columns_mapping_config(
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
