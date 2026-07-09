from __future__ import annotations


def timeout_seconds_from_node_config(config: dict[str, object]) -> int:
    value = config.get("timeout_seconds")
    if isinstance(value, bool) or not isinstance(value, int):
        return 60
    return max(0, value)
