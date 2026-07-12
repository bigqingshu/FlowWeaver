from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import FILTER_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_common import row_matches as _row_matches
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class FilterRowsNodeHandler:
    node_type = FILTER_ROWS_NODE_TYPE

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
        field = task.config.get("field")
        if not isinstance(field, str) or not field:
            raise _NodeValidationError("FilterRowsNode config.field is required")
        if find_field(input_ref.schema, field) is None:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_operator(task.config.get("operator"))
        value = task.config.get("value")

        def filtered_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row
                    for row in rows
                    if _row_matches(row.get(field), operator=operator, value=value)
                ]

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=filtered_batches(),
        )


def _normalize_operator(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("FilterRowsNode config.operator is required")
    operator = value.upper()
    if operator not in {"EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"}:
        raise _NodeValidationError(f"Unsupported filter operator: {value}")
    return operator
