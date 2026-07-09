from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import WRITE_BACK_TABLE_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_write_back_node_config_model import (
    WriteBackNodeConfig,
)
from flowweaver.nodes.table_write_back_node_summaries import (
    writeback_field_mapping_summary_config as _writeback_field_mapping_summary_config,
)
from flowweaver.nodes.table_write_back_node_summaries import (
    writeback_match_summary_config as _writeback_match_summary_config,
)
from flowweaver.protocols.table_ref import TableRefModel


def writeback_node_config(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    node_type: str = WRITE_BACK_TABLE_NODE_TYPE,
) -> WriteBackNodeConfig:
    direction = _enum_config(
        config,
        "writeback_direction",
        default="source_to_target",
        allowed={"source_to_target", "target_to_source"},
        node_type=node_type,
    )
    source_table = _optional_string_config(
        config,
        "source_table",
        default=input_ref.logical_table_id,
        node_type=node_type,
    ).strip()
    if not source_table:
        source_table = input_ref.logical_table_id
    target_table = _named_output_config(
        config,
        node_type=node_type,
        keys=("target_table",),
    )
    target_type = _enum_config(
        config,
        "target_type",
        default="sqlite",
        allowed={"run_table", "memory_table", "sqlite"},
        node_type=node_type,
    )
    write_mode = _enum_config(
        config,
        "write_mode",
        default="overwrite",
        allowed={"create", "overwrite", "append"},
        node_type=node_type,
    )
    use_match_rules, match_rule_count, match_fields = _writeback_match_summary_config(
        config,
        input_ref=input_ref,
    )
    field_mappings, mapped_fields = _writeback_field_mapping_summary_config(
        config,
        input_ref=input_ref,
    )
    overwrite_policy = _enum_config(
        config,
        "overwrite_policy",
        default="overwrite",
        allowed={"overwrite", "empty_only", "skip_existing"},
        node_type=node_type,
    )
    source_empty_policy = _enum_config(
        config,
        "source_empty_policy",
        default="skip",
        allowed={"skip", "write_empty", "clear_target"},
        node_type=node_type,
    )
    no_match_policy = _enum_config(
        config,
        "no_match_policy",
        default="skip",
        allowed={"skip", "insert", "error"},
        node_type=node_type,
    )
    multi_match_policy = _enum_config(
        config,
        "multi_match_policy",
        default="error",
        allowed={"first", "skip", "error"},
        node_type=node_type,
    )
    duplicate_target_policy = _enum_config(
        config,
        "duplicate_target_policy",
        default="error",
        allowed={"first", "skip", "error"},
        node_type=node_type,
    )
    enable_write = _bool_config(config, "enable_write", default=False)
    backup_before_write = _bool_config(
        config,
        "backup_before_write",
        default=False,
    )
    output_preview_table = _bool_config(
        config,
        "output_preview_table",
        default=True,
    )
    return WriteBackNodeConfig(
        direction=direction,
        source_table=source_table,
        target_table=target_table,
        target_type=target_type,
        write_mode=write_mode,
        use_match_rules=use_match_rules,
        match_rule_count=match_rule_count,
        match_fields=match_fields,
        field_mappings=field_mappings,
        mapped_fields=mapped_fields,
        overwrite_policy=overwrite_policy,
        source_empty_policy=source_empty_policy,
        no_match_policy=no_match_policy,
        multi_match_policy=multi_match_policy,
        duplicate_target_policy=duplicate_target_policy,
        enable_write=enable_write,
        backup_before_write=backup_before_write,
        output_preview_table=output_preview_table,
    )
