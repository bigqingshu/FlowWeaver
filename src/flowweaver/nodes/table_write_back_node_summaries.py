from __future__ import annotations

from typing import Any

from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_write_back_config import (
    writeback_field_mappings_config as _writeback_field_mappings_config,
)
from flowweaver.nodes.table_write_back_config import (
    writeback_match_rules_config as _writeback_match_rules_config,
)
from flowweaver.protocols.table_ref import TableRefModel


def writeback_match_summary_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> tuple[bool, int, str]:
    use_match_rules = _bool_config(
        config,
        "use_match_rules",
        default=True,
    )
    if not use_match_rules:
        return False, 0, ""
    match_rules = _writeback_match_rules_config(
        config,
        input_ref=input_ref,
    )
    match_fields = ",".join(
        f"{rule['source_field']}->{rule['target_field']}"
        for rule in match_rules
    )
    return True, len(match_rules), match_fields


def writeback_field_mapping_summary_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
) -> tuple[list[dict[str, str]], str]:
    field_mappings = _writeback_field_mappings_config(
        config,
        input_ref=input_ref,
    )
    mapped_fields = ",".join(
        f"{mapping['source_field']}->{mapping['target_field']}"
        for mapping in field_mappings
    )
    return field_mappings, mapped_fields
