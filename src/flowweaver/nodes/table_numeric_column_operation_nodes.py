from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    NUMERIC_COLUMN_OPERATION_NODE_TYPE,
)
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_non_negative_int_config as _optional_non_negative_int_config,
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
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    _number_config as _number_config,
)
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_operand_config as _numeric_operand_config,
)
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_output_field as _numeric_output_field,
)
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_output_schema as _numeric_output_schema,
)
from flowweaver.nodes.table_numeric_column_operation_helpers import (
    numeric_row_selector as _numeric_row_selector,
)
from flowweaver.nodes.table_numeric_column_operation_output import (
    numeric_operation_output_batches as _numeric_operation_output_batches,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class NumericColumnOperationNodeHandler:
    node_type = NUMERIC_COLUMN_OPERATION_NODE_TYPE

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
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, target_field) is None:
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        operation = _enum_config(
            task.config,
            "operation",
            default="add",
            allowed={
                "add",
                "subtract",
                "multiply",
                "divide",
                "sequence",
                "round",
                "floor",
                "ceil",
            },
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="overwrite",
            allowed={"overwrite", "new_field"},
            node_type=self.node_type,
        )
        output_field = _numeric_output_field(
            task.config,
            input_ref=input_ref,
            target_field=target_field,
            output_mode=output_mode,
        )
        output_schema = _numeric_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        row_selector = _numeric_row_selector(task.config, input_ref=input_ref)
        operand_config = _numeric_operand_config(task.config, input_ref=input_ref)
        decimal_places = _optional_non_negative_int_config(
            task.config,
            "decimal_places",
            node_type=self.node_type,
        )
        non_number_policy = _enum_config(
            task.config,
            "non_number_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )
        divide_zero_policy = _enum_config(
            task.config,
            "divide_zero_policy",
            default="error",
            allowed={"error", "empty", "fixed", "keep_original"},
            node_type=self.node_type,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=_numeric_operation_output_batches(
                context,
                input_ref,
                config=task.config,
                target_field=target_field,
                operation=operation,
                operand_config=operand_config,
                decimal_places=decimal_places,
                non_number_policy=non_number_policy,
                divide_zero_policy=divide_zero_policy,
                row_selector=row_selector,
                output_field=output_field,
            ),
        )

