from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import SUB_WORKFLOW_NODE_TYPE
from flowweaver.nodes.table_control_status import (
    publish_control_status as _publish_control_status,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_subworkflow_control_config import (
    subworkflow_node_config as _subworkflow_node_config,
)
from flowweaver.nodes.table_subworkflow_control_helpers import (
    subworkflow_loop_node_ids as _subworkflow_loop_node_ids,
)
from flowweaver.nodes.table_subworkflow_control_plan import (
    subworkflow_plan_details as _subworkflow_plan_details,
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
        config = _subworkflow_node_config(task.config, node_type=self.node_type)
        blocked_loop_nodes = _subworkflow_loop_node_ids(config.nodes)
        if blocked_loop_nodes and not config.allow_loop_nodes:
            raise _NodeValidationError(
                "SubWorkflowNode config.nodes contains loop nodes while "
                "allow_loop_nodes is false: "
                + ", ".join(blocked_loop_nodes)
            )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="subworkflow_plan",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=config.group_name,
                action="declare_subworkflow_plan",
                reason="preview only; no child workflow run is created",
                details=_subworkflow_plan_details(
                    group_name=config.group_name,
                    subworkflow_ref=config.subworkflow_ref,
                    node_count=len(config.nodes),
                    input_source_type=config.input_source_type,
                    input_refs=input_refs,
                    input_mapping=config.input_mapping,
                    input_defaults=config.input_defaults,
                    missing_input_policy=config.missing_input_policy,
                    transit_scope=config.transit_scope,
                    allow_loop_nodes=config.allow_loop_nodes,
                    main_output_mode=config.main_output_mode,
                    save_to_transit=config.save_to_transit,
                    output_transit_name=config.output_transit_name,
                ),
            )
        ]
