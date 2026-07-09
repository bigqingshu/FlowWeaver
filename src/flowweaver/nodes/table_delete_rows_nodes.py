from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import DELETE_ROWS_NODE_TYPE
from flowweaver.nodes.table_delete_rows_helpers import (
    delete_rows_output_batches as _delete_rows_output_batches,
)
from flowweaver.nodes.table_delete_rows_helpers import (
    delete_rows_predicate as _delete_rows_predicate,
)
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel


class DeleteRowsNodeHandler:
    node_type = DELETE_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        delete_mode = _enum_config(
            task.config,
            "delete_mode",
            default="row_numbers",
            allowed={"row_numbers", "row_range", "condition", "empty"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        should_delete = _delete_rows_predicate(
            task.config,
            input_ref=input_ref,
            delete_mode=delete_mode,
            total_rows=total_rows,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=_delete_rows_output_batches(
                context,
                input_ref,
                should_delete=should_delete,
            ),
        )
