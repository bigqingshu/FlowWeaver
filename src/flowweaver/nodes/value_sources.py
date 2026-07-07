from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

VALUE_SOURCE_LITERAL = "literal"
VALUE_SOURCE_ROW_FIELD = "row_field"


class ValueSourceError(ValueError):
    pass


@dataclass(frozen=True)
class ValueSource:
    mode: str
    value: Any = None
    field: str | None = None

    def resolve(self, row: Mapping[str, Any]) -> Any:
        if self.mode == VALUE_SOURCE_LITERAL:
            return self.value
        if self.mode == VALUE_SOURCE_ROW_FIELD:
            if self.field is None:
                raise ValueSourceError("row_field value source requires field")
            if self.field not in row:
                raise ValueSourceError(f"row field does not exist: {self.field}")
            return row[self.field]
        raise ValueSourceError(f"unsupported value source mode: {self.mode}")


def parse_value_source(raw: Any) -> ValueSource:
    if not isinstance(raw, Mapping) or "mode" not in raw:
        return ValueSource(mode=VALUE_SOURCE_LITERAL, value=raw)
    mode = raw.get("mode")
    if mode == VALUE_SOURCE_LITERAL:
        return ValueSource(mode=VALUE_SOURCE_LITERAL, value=raw.get("value"))
    if mode == VALUE_SOURCE_ROW_FIELD:
        field = raw.get("field")
        if not isinstance(field, str) or not field.strip():
            raise ValueSourceError("row_field value source requires field")
        return ValueSource(mode=VALUE_SOURCE_ROW_FIELD, field=field.strip())
    raise ValueSourceError(f"unsupported value source mode: {mode}")


def resolve_value_source(raw: Any, row: Mapping[str, Any]) -> Any:
    return parse_value_source(raw).resolve(row)
