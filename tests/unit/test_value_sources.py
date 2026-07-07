from __future__ import annotations

import pytest

from flowweaver.nodes.value_sources import (
    VALUE_SOURCE_LITERAL,
    VALUE_SOURCE_ROW_FIELD,
    ValueSourceError,
    parse_value_source,
    resolve_value_source,
)


def test_parse_value_source_treats_plain_values_as_literals() -> None:
    source = parse_value_source("fixed")

    assert source.mode == VALUE_SOURCE_LITERAL
    assert source.resolve({"name": "current"}) == "fixed"


def test_parse_value_source_supports_explicit_literal_objects() -> None:
    source = parse_value_source(
        {
            "mode": VALUE_SOURCE_LITERAL,
            "value": {"nested": 1},
        }
    )

    assert source.mode == VALUE_SOURCE_LITERAL
    assert source.resolve({}) == {"nested": 1}


def test_resolve_value_source_reads_same_row_field() -> None:
    value = resolve_value_source(
        {
            "mode": VALUE_SOURCE_ROW_FIELD,
            "field": "amount",
        },
        {
            "amount": 12,
            "other": 99,
        },
    )

    assert value == 12


def test_row_field_value_source_rejects_missing_field_name() -> None:
    with pytest.raises(ValueSourceError, match="requires field"):
        parse_value_source({"mode": VALUE_SOURCE_ROW_FIELD, "field": " "})


def test_row_field_value_source_rejects_missing_row_field() -> None:
    source = parse_value_source(
        {
            "mode": VALUE_SOURCE_ROW_FIELD,
            "field": "amount",
        }
    )

    with pytest.raises(ValueSourceError, match="row field does not exist"):
        source.resolve({"other": 99})


def test_parse_value_source_rejects_unknown_mode() -> None:
    with pytest.raises(ValueSourceError, match="unsupported value source mode"):
        parse_value_source({"mode": "computed"})
