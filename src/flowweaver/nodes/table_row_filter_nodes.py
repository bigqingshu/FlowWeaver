from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import ADVANCED_FILTER_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    optional_non_negative_int_config as _optional_non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import reorder_fields
from flowweaver.nodes.table_row_filter_helpers import (
    advanced_filter_conditions as _advanced_filter_conditions,
)
from flowweaver.nodes.table_row_filter_helpers import (
    advanced_filter_output_batches as _advanced_filter_output_batches,
)
from flowweaver.nodes.table_row_filter_helpers import (
    advanced_filter_output_fields as _advanced_filter_output_fields,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class AdvancedFilterRowsNodeHandler:
    node_type = ADVANCED_FILTER_ROWS_NODE_TYPE

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
        logic = _enum_config(
            task.config,
            "logic",
            default="and",
            allowed={"and", "or"},
            node_type=self.node_type,
        )
        conditions = _advanced_filter_conditions(task.config, input_ref)
        output_fields = _advanced_filter_output_fields(task.config, input_ref)
        output_schema = reorder_fields(
            input_ref.schema,
            output_fields,
            include_unlisted=False,
        )
        result_limit = _optional_non_negative_int_config(
            task.config,
            "result_limit",
            node_type=self.node_type,
        )
        max_intermediate = _optional_positive_int_config(
            task.config,
            "max_intermediate",
            node_type=self.node_type,
        )
        remove_duplicates = _bool_config(
            task.config,
            "remove_duplicates",
            default=False,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=_advanced_filter_output_batches(
                context,
                input_ref,
                conditions=conditions,
                logic=logic,
                output_fields=output_fields,
                result_limit=result_limit,
                max_intermediate=max_intermediate,
                remove_duplicates=remove_duplicates,
            ),
        )
