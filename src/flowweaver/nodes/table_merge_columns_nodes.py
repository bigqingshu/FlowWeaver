from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import MERGE_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_merge_columns_helpers import (
    merge_columns_output_schema as _merge_columns_output_schema,
)
from flowweaver.nodes.table_merge_columns_helpers import (
    merge_columns_separators as _merge_columns_separators,
)
from flowweaver.nodes.table_merge_columns_helpers import (
    merge_columns_value as _merge_columns_value,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import has_field
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class MergeColumnsNodeHandler:
    node_type = MERGE_COLUMNS_NODE_TYPE

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
        fields = _string_list_config(
            task.config,
            "fields",
            node_type=self.node_type,
        )
        missing_fields = [
            field_name
            for field_name in fields
            if not has_field(input_ref.schema, field_name)
        ]
        if missing_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_fields)}"
            )
        separators = _merge_columns_separators(task.config, field_count=len(fields))
        output_field = _optional_node_string_config(
            task.config,
            "output_field",
            default="merged",
            node_type=self.node_type,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "overwrite"},
            node_type=self.node_type,
        )
        output_schema = _merge_columns_output_schema(
            input_ref.schema,
            output_field=output_field,
            conflict_mode=conflict_mode,
        )
        skip_empty = _bool_config(task.config, "skip_empty", default=False)
        trim_value = _bool_config(task.config, "trim_value", default=False)
        empty_placeholder = task.config.get("empty_placeholder", "")

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                yield [
                    row
                    | {
                        output_field: _merge_columns_value(
                            row,
                            fields=fields,
                            separators=separators,
                            skip_empty=skip_empty,
                            trim_value=trim_value,
                            empty_placeholder=empty_placeholder,
                        )
                    }
                    for row in rows
                ]

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )
