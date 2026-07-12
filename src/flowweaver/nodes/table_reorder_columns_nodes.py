from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import REORDER_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeContext
from flowweaver.nodes.table_node_io import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_reorder_columns_helpers import (
    reorder_columns_output_batches as _reorder_columns_output_batches,
)
from flowweaver.nodes.table_reorder_columns_helpers import (
    reorder_columns_output_plan as _reorder_columns_output_plan,
)
from flowweaver.protocols.node_task import NodeTaskModel


class ReorderColumnsNodeHandler:
    node_type = REORDER_COLUMNS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> BuiltinTableExecutionResult:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        order = _string_list_config(
            task.config,
            "order",
            node_type=self.node_type,
        )
        missing_policy = _enum_config(
            task.config,
            "missing_policy",
            default="error",
            allowed={"error", "skip", "warn"},
            node_type=self.node_type,
        )
        unlisted_policy = _enum_config(
            task.config,
            "unlisted_policy",
            default="append",
            allowed={"append", "drop", "error"},
            node_type=self.node_type,
        )
        schema, output_columns = _reorder_columns_output_plan(
            input_ref.schema,
            order=order,
            missing_policy=missing_policy,
            unlisted_policy=unlisted_policy,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=_reorder_columns_output_batches(
                context,
                input_ref,
                output_columns=output_columns,
            ),
        )
