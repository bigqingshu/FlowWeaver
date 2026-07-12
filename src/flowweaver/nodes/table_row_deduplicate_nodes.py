from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import DEDUPLICATE_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
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
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_groups as _deduplicate_groups,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_key_fields as _deduplicate_key_fields,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_marker_fields as _deduplicate_marker_fields,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_output_batches as _deduplicate_output_batches,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_output_schema as _deduplicate_output_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class DeduplicateRowsNodeHandler:
    node_type = DEDUPLICATE_ROWS_NODE_TYPE

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
        key_fields = _deduplicate_key_fields(task.config, input_ref)
        trim = _bool_config(task.config, "trim", default=False)
        ignore_case = _bool_config(task.config, "ignore_case", default=False)
        empty_key_policy = _enum_config(
            task.config,
            "empty_key_policy",
            default="include",
            allowed={"include", "skip"},
            node_type=self.node_type,
        )
        keep_policy = _enum_config(
            task.config,
            "keep_policy",
            default="first",
            allowed={"first", "last", "all"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="dedupe",
            allowed={"dedupe", "mark"},
            node_type=self.node_type,
        )
        add_marker_columns = _bool_config(
            task.config,
            "add_marker_columns",
            default=output_mode == "mark",
        )
        if output_mode == "mark" and not add_marker_columns:
            raise _NodeValidationError(
                "DeduplicateRowsNode output_mode=mark requires marker columns"
            )
        marker_fields = _deduplicate_marker_fields(task.config)
        output_schema = (
            _deduplicate_output_schema(input_ref.schema, marker_fields)
            if add_marker_columns
            else input_ref.schema
        )
        groups = _deduplicate_groups(
            context,
            input_ref=input_ref,
            key_fields=key_fields,
            trim=trim,
            ignore_case=ignore_case,
            empty_key_policy=empty_key_policy,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=_deduplicate_output_batches(
                context,
                input_ref,
                key_fields=key_fields,
                trim=trim,
                ignore_case=ignore_case,
                empty_key_policy=empty_key_policy,
                keep_policy=keep_policy,
                output_mode=output_mode,
                add_marker_columns=add_marker_columns,
                marker_fields=marker_fields,
                groups=groups,
            ),
        )


