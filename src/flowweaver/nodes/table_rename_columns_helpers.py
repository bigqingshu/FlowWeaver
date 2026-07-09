from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_rename_columns_config import (
    rename_columns_proposed_names as rename_columns_proposed_names,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


def rename_columns_apply_duplicate_policy(
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


def rename_columns_schema(
    schema: list[FieldSchemaModel],
    output_names: list[str],
) -> list[FieldSchemaModel]:
    return [
        field.model_copy(update={"name": output_name, "ordinal": ordinal})
        for ordinal, (field, output_name) in enumerate(
            zip(schema, output_names, strict=True)
        )
    ]


def rename_columns_output_batches(
    context: BuiltinTableNodeContext,
    input_ref: TableRefModel,
    *,
    source_to_output: dict[str, str],
) -> Iterator[list[dict[str, Any]]]:
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
