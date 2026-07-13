from __future__ import annotations

from flowweaver.nodes.builtin_sql import (
    SQL_MAPPING_NODE_TYPE,
    SqlMappingTaskConfig,
)
from flowweaver.nodes.builtin_table_execution_result import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class SqlMappingNodeHandler:
    node_type = SQL_MAPPING_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult:
        if task.input_refs:
            raise _NodeValidationError("SqlMappingNode does not accept inputs")
        if context.sql_mapping_runner is None:
            raise _NodeValidationError("SqlMappingNode runner is not configured")
        try:
            table_refs = context.sql_mapping_runner.execute(
                SqlMappingTaskConfig(
                    workflow_run_id=task.workflow_run_id,
                    node_run_id=task.node_run_id,
                    node_instance_id=task.node_instance_id,
                    config=task.config,
                )
            )
        except ValueError as exc:
            raise _NodeValidationError(str(exc)) from exc
        bindings = (
            {"out": table_refs[0].table_ref_id}
            if len(table_refs) == 1
            else {
                table_ref.logical_table_id: table_ref.table_ref_id
                for table_ref in table_refs
            }
        )
        return BuiltinTableExecutionResult(
            output_refs=tuple(table_refs),
            output_slot_bindings=bindings,
        )
