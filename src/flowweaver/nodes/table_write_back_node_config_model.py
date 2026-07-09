from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WriteBackNodeConfig:
    direction: str
    source_table: str
    target_table: str
    target_type: str
    write_mode: str
    use_match_rules: bool
    match_rule_count: int
    match_fields: str
    field_mappings: list[dict[str, str]]
    mapped_fields: str
    overwrite_policy: str
    source_empty_policy: str
    no_match_policy: str
    multi_match_policy: str
    duplicate_target_policy: str
    enable_write: bool
    backup_before_write: bool
    output_preview_table: bool
