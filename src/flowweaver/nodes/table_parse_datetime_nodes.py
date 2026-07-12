from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import PARSE_DATETIME_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
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
from flowweaver.nodes.table_parse_datetime_helpers import (
    parse_datetime_output_field as _parse_datetime_output_field,
)
from flowweaver.nodes.table_parse_datetime_helpers import (
    parse_datetime_output_schema as _parse_datetime_output_schema,
)
from flowweaver.nodes.table_parse_datetime_output import (
    parse_datetime_output_batches as _parse_datetime_output_batches,
)
from flowweaver.protocols.node_task import NodeTaskModel

_NodeValidationError = BuiltinTableNodeValidationError


class ParseDateTimeNodeHandler:
    node_type = PARSE_DATETIME_NODE_TYPE

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
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        use_separate_time_field = _bool_config(
            task.config,
            "use_separate_time_field",
            default=False,
        )
        time_source_field = None
        if use_separate_time_field:
            time_source_field = _node_string_config(
                task.config,
                "time_source_field",
                node_type=self.node_type,
            )
            if find_field(input_ref.schema, time_source_field) is None:
                raise _NodeValidationError(f"Field does not exist: {time_source_field}")
        parse_type = _enum_config(
            task.config,
            "parse_type",
            default="datetime",
            allowed={"date", "time", "datetime"},
            node_type=self.node_type,
        )
        input_structure = _enum_config(
            task.config,
            "input_structure",
            default="auto",
            allowed={"auto", "strptime"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite_source", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _parse_datetime_output_field(
            task.config,
            input_ref=input_ref,
            source_field=source_field,
            output_mode=output_mode,
        )
        output_status = _bool_config(task.config, "output_status", default=True)
        status_field = None
        if output_status:
            status_field = _optional_node_string_config(
                task.config,
                "status_field",
                default="parse_status",
                node_type=self.node_type,
            )
        output_schema = _parse_datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
            status_field=status_field,
        )
        unmatched_mode = _enum_config(
            task.config,
            "unmatched_mode",
            default="empty",
            allowed={"empty", "keep_original", "fixed"},
            node_type=self.node_type,
        )

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=_parse_datetime_output_batches(
                context,
                input_ref,
                config=task.config,
                source_field=source_field,
                time_source_field=time_source_field,
                parse_type=parse_type,
                input_structure=input_structure,
                output_field=output_field,
                status_field=status_field,
                unmatched_mode=unmatched_mode,
            ),
        )
