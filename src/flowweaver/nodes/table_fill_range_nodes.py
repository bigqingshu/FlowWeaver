from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import FILL_RANGE_NODE_TYPE
from flowweaver.nodes.table_fill_range_helpers import field_range as _field_range
from flowweaver.nodes.table_fill_range_helpers import (
    fill_range_output_batches as _fill_range_output_batches,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_positive_int_config as _optional_positive_int_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.protocols.node_task import NodeTaskModel

DEFAULT_FILL_RANGE_MAX_CELLS = 100_000
_NodeValidationError = BuiltinTableNodeValidationError


class FillRangeNodeHandler:
    node_type = FILL_RANGE_NODE_TYPE

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
        start_field = _node_string_config(
            task.config,
            "start_field",
            node_type=self.node_type,
        )
        end_field = _optional_node_string_config(
            task.config,
            "end_field",
            default=start_field,
            node_type=self.node_type,
        )
        target_fields = _field_range(
            input_ref.schema,
            start_field=start_field,
            end_field=end_field,
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        end_row = _optional_positive_int_config(
            task.config,
            "end_row",
            node_type=self.node_type,
        )
        if end_row is None:
            end_row = total_rows
        if total_rows > 0 and (start_row > total_rows or end_row > total_rows):
            raise _NodeValidationError("FillRangeNode row range is out of range")
        if start_row > end_row:
            raise _NodeValidationError("FillRangeNode start_row must be <= end_row")
        max_cells = _positive_int_config(
            task.config,
            "max_cells",
            default=DEFAULT_FILL_RANGE_MAX_CELLS,
            node_type=self.node_type,
        )
        target_row_count = 0 if total_rows <= 0 else end_row - start_row + 1
        target_cell_count = target_row_count * len(target_fields)
        if target_cell_count > max_cells:
            raise _NodeValidationError("FillRangeNode target range exceeds max_cells")
        value_source = _value_source_config(
            task.config,
            "value_source",
            fallback_key="manual_value",
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=_fill_range_output_batches(
                context,
                input_ref,
                start_row=start_row,
                end_row=end_row,
                target_fields=target_fields,
                value_source=value_source,
                overwrite_rule=overwrite_rule,
            ),
        )
