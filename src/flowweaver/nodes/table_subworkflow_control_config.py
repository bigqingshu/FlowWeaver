from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import object_config as _object_config
from flowweaver.nodes.table_node_config import (
    optional_object_list_config as _optional_object_list_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeValidationError

_NodeValidationError = BuiltinTableNodeValidationError


@dataclass(frozen=True)
class SubWorkflowNodeConfig:
    group_name: str
    subworkflow_ref: str
    nodes: list[dict[str, Any]]
    input_source_type: str
    input_mapping: list[dict[str, Any]]
    input_defaults: dict[str, Any]
    missing_input_policy: str
    transit_scope: str
    allow_loop_nodes: bool
    main_output_mode: str
    save_to_transit: bool
    output_transit_name: str


def subworkflow_node_config(
    config: dict[str, Any],
    *,
    node_type: str,
) -> SubWorkflowNodeConfig:
    group_name = _node_string_config(
        config,
        "group_name",
        node_type=node_type,
    )
    subworkflow_ref = _optional_string_config(
        config,
        "subworkflow_ref",
        node_type=node_type,
    ).strip()
    nodes = _optional_object_list_config(
        config,
        "nodes",
        node_type=node_type,
    )
    input_source_type = _enum_config(
        config,
        "input_source_type",
        default="current_table",
        allowed={"current_table", "named_inputs", "none"},
        node_type=node_type,
    )
    input_mapping = _optional_object_list_config(
        config,
        "input_mapping",
        node_type=node_type,
    )
    input_defaults = _object_config(
        config,
        "input_defaults",
        node_type=node_type,
    )
    missing_input_policy = _enum_config(
        config,
        "missing_input_policy",
        default="error",
        allowed={"error", "skip", "use_default"},
        node_type=node_type,
    )
    transit_scope = _enum_config(
        config,
        "transit_scope",
        default="isolated",
        allowed={"isolated", "inherited"},
        node_type=node_type,
    )
    allow_loop_nodes = _bool_config(
        config,
        "allow_loop_nodes",
        default=False,
    )
    main_output_mode = _enum_config(
        config,
        "main_output_mode",
        default="status_only",
        allowed={"status_only", "passthrough", "named_outputs"},
        node_type=node_type,
    )
    save_to_transit = _bool_config(
        config,
        "save_to_transit",
        default=False,
    )
    output_transit_name = _optional_string_config(
        config,
        "output_transit_name",
        node_type=node_type,
    ).strip()
    if save_to_transit and not output_transit_name:
        raise _NodeValidationError(
            "SubWorkflowNode config.output_transit_name is required"
        )
    return SubWorkflowNodeConfig(
        group_name=group_name,
        subworkflow_ref=subworkflow_ref,
        nodes=nodes,
        input_source_type=input_source_type,
        input_mapping=input_mapping,
        input_defaults=input_defaults,
        missing_input_policy=missing_input_policy,
        transit_scope=transit_scope,
        allow_loop_nodes=allow_loop_nodes,
        main_output_mode=main_output_mode,
        save_to_transit=save_to_transit,
        output_transit_name=output_transit_name,
    )
