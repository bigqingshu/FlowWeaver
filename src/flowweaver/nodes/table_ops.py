from __future__ import annotations

from collections.abc import Sequence

from flowweaver.protocols.table_ref import FieldSchemaModel


def field_names(schema: Sequence[FieldSchemaModel]) -> set[str]:
    return {field.name for field in schema}


def find_field(
    schema: Sequence[FieldSchemaModel],
    field_name: str,
) -> FieldSchemaModel | None:
    for field in schema:
        if field.name == field_name:
            return field
    return None


def has_field(
    schema: Sequence[FieldSchemaModel],
    field_name: str,
) -> bool:
    return find_field(schema, field_name) is not None


def append_field(
    schema: Sequence[FieldSchemaModel],
    *,
    name: str,
    data_type: str,
    nullable: bool,
    field_id: str | None = None,
) -> list[FieldSchemaModel]:
    return [
        *schema,
        FieldSchemaModel(
            field_id=field_id or name,
            name=name,
            data_type=data_type,
            nullable=nullable,
            ordinal=len(schema),
        ),
    ]


def remove_fields(
    schema: Sequence[FieldSchemaModel],
    field_names_to_remove: Sequence[str],
) -> list[FieldSchemaModel]:
    removed_names = set(field_names_to_remove)
    return [
        field.model_copy(update={"ordinal": ordinal})
        for ordinal, field in enumerate(
            field
            for field in schema
            if field.name not in removed_names
        )
    ]


def replace_field_schema(
    schema: Sequence[FieldSchemaModel],
    field_name: str,
    *,
    data_type: str,
    nullable: bool,
) -> list[FieldSchemaModel]:
    return [
        field.model_copy(update={"data_type": data_type, "nullable": nullable})
        if field.name == field_name
        else field
        for field in schema
    ]
