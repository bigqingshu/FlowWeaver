from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import SUB_WORKFLOW_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
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
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_subworkflow_control_helpers import (
    subworkflow_loop_node_ids as _subworkflow_loop_node_ids,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class SubWorkflowNodeHandler:
    node_type = SUB_WORKFLOW_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_refs = [context.input_ref(ref_id) for ref_id in task.input_refs]
        group_name = _node_string_config(
            task.config,
            "group_name",
            node_type=self.node_type,
        )
        subworkflow_ref = _optional_string_config(
            task.config,
            "subworkflow_ref",
            node_type=self.node_type,
        ).strip()
        nodes = _optional_object_list_config(
            task.config,
            "nodes",
            node_type=self.node_type,
        )
        input_source_type = _enum_config(
            task.config,
            "input_source_type",
            default="current_table",
            allowed={"current_table", "named_inputs", "none"},
            node_type=self.node_type,
        )
        input_mapping = _optional_object_list_config(
            task.config,
            "input_mapping",
            node_type=self.node_type,
        )
        input_defaults = _object_config(
            task.config,
            "input_defaults",
            node_type=self.node_type,
        )
        missing_input_policy = _enum_config(
            task.config,
            "missing_input_policy",
            default="error",
            allowed={"error", "skip", "use_default"},
            node_type=self.node_type,
        )
        transit_scope = _enum_config(
            task.config,
            "transit_scope",
            default="isolated",
            allowed={"isolated", "inherited"},
            node_type=self.node_type,
        )
        allow_loop_nodes = _bool_config(
            task.config,
            "allow_loop_nodes",
            default=False,
        )
        main_output_mode = _enum_config(
            task.config,
            "main_output_mode",
            default="status_only",
            allowed={"status_only", "passthrough", "named_outputs"},
            node_type=self.node_type,
        )
        save_to_transit = _bool_config(
            task.config,
            "save_to_transit",
            default=False,
        )
        output_transit_name = _optional_string_config(
            task.config,
            "output_transit_name",
            node_type=self.node_type,
        ).strip()
        if save_to_transit and not output_transit_name:
            raise _NodeValidationError(
                "SubWorkflowNode config.output_transit_name is required"
            )
        blocked_loop_nodes = _subworkflow_loop_node_ids(nodes)
        if blocked_loop_nodes and not allow_loop_nodes:
            raise _NodeValidationError(
                "SubWorkflowNode config.nodes contains loop nodes while "
                "allow_loop_nodes is false: "
                + ", ".join(blocked_loop_nodes)
            )
        input_summaries = [
            {
                "table_ref_id": input_ref.table_ref_id,
                "logical_table_id": input_ref.logical_table_id,
                "role": input_ref.role.value,
                "storage_kind": input_ref.storage_kind.value,
                "field_count": len(input_ref.schema),
            }
            for input_ref in input_refs
        ]
        return [
            _publish_control_status(
                context,
                task,
                signal_type="subworkflow_plan",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=group_name,
                action="declare_subworkflow_plan",
                reason="preview only; no child workflow run is created",
                details={
                    "group_name": group_name,
                    "subworkflow_ref": subworkflow_ref,
                    "node_count": len(nodes),
                    "input_source_type": input_source_type,
                    "input_ref_count": len(input_refs),
                    "input_refs": input_summaries,
                    "input_mapping": input_mapping,
                    "input_defaults": input_defaults,
                    "missing_input_policy": missing_input_policy,
                    "transit_scope": transit_scope,
                    "allow_loop_nodes": allow_loop_nodes,
                    "main_output_mode": main_output_mode,
                    "save_to_transit": save_to_transit,
                    "output_transit_name": output_transit_name,
                },
            )
        ]
