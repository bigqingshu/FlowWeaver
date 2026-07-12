from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import COPY_COLUMN_NODE_TYPE
from flowweaver.nodes.table_copy_column_helpers import (
    copy_column_output_batches as _copy_column_output_batches,
)
from flowweaver.nodes.table_copy_column_helpers import (
    copy_column_output_mode_config as _copy_column_output_mode_config,
)
from flowweaver.nodes.table_copy_column_helpers import (
    copy_column_target_field_config as _copy_column_target_field_config,
)
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
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
from flowweaver.nodes.table_ops import (
    append_field,
    find_field,
    has_field,
    replace_field_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class CopyColumnNodeHandler:
    node_type = COPY_COLUMN_NODE_TYPE

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
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        source_schema = find_field(input_ref.schema, source_field)
        if source_schema is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        output_mode = _copy_column_output_mode_config(task.config)
        target_field = _copy_column_target_field_config(
            task.config,
            output_mode=output_mode,
        )
        if output_mode == "new_field":
            if has_field(input_ref.schema, target_field):
                raise _NodeValidationError(f"Field already exists: {target_field}")
            schema = append_field(
                input_ref.schema,
                name=target_field,
                data_type=source_schema.data_type,
                nullable=source_schema.nullable,
            )
        else:
            if not has_field(input_ref.schema, target_field):
                raise _NodeValidationError(f"Field does not exist: {target_field}")
            schema = replace_field_schema(
                input_ref.schema,
                target_field,
                data_type=source_schema.data_type,
                nullable=source_schema.nullable,
            )
        trim_value = _bool_config(task.config, "trim_value", default=False)
        empty_default = task.config.get("empty_default")

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=_copy_column_output_batches(
                context,
                input_ref,
                source_field=source_field,
                target_field=target_field,
                trim_value=trim_value,
                empty_default=empty_default,
            ),
        )
