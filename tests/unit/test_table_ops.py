from __future__ import annotations

from flowweaver.nodes.table_ops import (
    append_field,
    field_names,
    find_field,
    has_field,
    remove_fields,
    replace_field_schema,
)
from flowweaver.protocols.table_ref import FieldSchemaModel


def test_table_ops_find_and_list_fields() -> None:
    schema = [
        _field("row_id", "INTEGER", 0),
        _field("amount", "FLOAT", 1),
    ]

    assert field_names(schema) == {"row_id", "amount"}
    assert find_field(schema, "amount") == schema[1]
    assert find_field(schema, "missing") is None
    assert has_field(schema, "row_id")
    assert not has_field(schema, "missing")


def test_append_field_returns_schema_with_next_ordinal() -> None:
    schema = [
        _field("row_id", "INTEGER", 0),
    ]

    next_schema = append_field(
        schema,
        name="status",
        data_type="TEXT",
        nullable=True,
    )

    assert [field.name for field in next_schema] == ["row_id", "status"]
    assert next_schema[1].field_id == "status"
    assert next_schema[1].data_type == "TEXT"
    assert next_schema[1].nullable is True
    assert next_schema[1].ordinal == 1
    assert [field.name for field in schema] == ["row_id"]


def test_remove_fields_returns_schema_with_rebased_ordinals() -> None:
    schema = [
        _field("row_id", "INTEGER", 0),
        _field("amount", "FLOAT", 1),
        _field("status", "TEXT", 2),
    ]

    next_schema = remove_fields(schema, ["amount"])

    assert [field.name for field in next_schema] == ["row_id", "status"]
    assert [field.ordinal for field in next_schema] == [0, 1]
    assert [field.ordinal for field in schema] == [0, 1, 2]


def test_replace_field_schema_updates_type_without_reordering() -> None:
    schema = [
        _field("row_id", "INTEGER", 0),
        _field("label", "TEXT", 1),
    ]

    next_schema = replace_field_schema(
        schema,
        "label",
        data_type="INTEGER",
        nullable=True,
    )

    assert [field.name for field in next_schema] == ["row_id", "label"]
    assert [field.ordinal for field in next_schema] == [0, 1]
    assert next_schema[1].data_type == "INTEGER"
    assert next_schema[1].nullable is True
    assert schema[1].data_type == "TEXT"


def _field(name: str, data_type: str, ordinal: int) -> FieldSchemaModel:
    return FieldSchemaModel(
        field_id=name,
        name=name,
        data_type=data_type,
        nullable=False,
        ordinal=ordinal,
    )
