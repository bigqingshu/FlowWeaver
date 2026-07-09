from __future__ import annotations

from datetime import datetime
from typing import Any

from flowweaver.nodes.builtin_table_node_types import PARSE_DATETIME_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)


def parse_datetime_value(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
    input_structure: str,
):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if input_structure == "strptime":
        input_format = _node_string_config(
            config,
            "input_format",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        try:
            return datetime.strptime(text, input_format)
        except ValueError:
            return None
    return _parse_datetime_auto(text, parse_type=parse_type, config=config)


def _parse_datetime_auto(text: str, *, parse_type: str, config: dict[str, Any]):
    try:
        if parse_type == "date":
            return datetime.fromisoformat(text).date()
        if parse_type == "time":
            return datetime.strptime(text, "%H:%M:%S").time()
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for input_format in _parse_datetime_auto_formats(parse_type, config=config):
        try:
            parsed = datetime.strptime(text, input_format)
        except ValueError:
            continue
        if parse_type == "date":
            return parsed.date()
        if parse_type == "time":
            return parsed.time()
        return parsed
    return None


def _parse_datetime_auto_formats(
    parse_type: str,
    *,
    config: dict[str, Any],
) -> list[str]:
    date_order = _enum_config(
        config,
        "date_order",
        default="ymd",
        allowed={"ymd", "mdy", "dmy"},
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    if parse_type == "time":
        return ["%H:%M:%S", "%H:%M"]
    date_formats_by_order = {
        "ymd": ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%y-%m-%d", "%y/%m/%d"],
        "mdy": ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"],
        "dmy": ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"],
    }
    date_formats = date_formats_by_order[date_order]
    if parse_type == "date":
        return date_formats
    time_formats = ["%H:%M:%S", "%H:%M"]
    return [
        f"{date_format} {time_format}"
        for date_format in date_formats
        for time_format in time_formats
    ]


def format_parsed_datetime(
    value: Any,
    *,
    config: dict[str, Any],
    parse_type: str,
) -> str:
    if parse_type == "date":
        template = _optional_node_string_config(
            config,
            "output_template",
            default="%Y-%m-%d",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    if parse_type == "time":
        template = _optional_node_string_config(
            config,
            "time_output_template",
            default="%H:%M:%S",
            node_type=PARSE_DATETIME_NODE_TYPE,
        )
        return value.strftime(template)
    template = _optional_node_string_config(
        config,
        "datetime_output_template",
        default="%Y-%m-%d %H:%M:%S",
        node_type=PARSE_DATETIME_NODE_TYPE,
    )
    return value.strftime(template)


def parse_datetime_unmatched_value(
    original_value: Any,
    *,
    config: dict[str, Any],
    unmatched_mode: str,
) -> Any:
    if unmatched_mode == "empty":
        return ""
    if unmatched_mode == "keep_original":
        return original_value
    return config.get("unmatched_fixed")
