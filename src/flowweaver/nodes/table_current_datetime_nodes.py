from __future__ import annotations

from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
)
from flowweaver.nodes.table_current_datetime_helpers import (
    datetime_formatted_value as _datetime_formatted_value,
)
from flowweaver.nodes.table_current_datetime_helpers import (
    datetime_output_field as _datetime_output_field,
)
from flowweaver.nodes.table_current_datetime_helpers import (
    datetime_output_schema as _datetime_output_schema,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
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
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class AddCurrentDateTimeColumnNodeHandler:
    node_type = ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE

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
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _datetime_output_field(
            task.config,
            input_ref=input_ref,
            output_mode=output_mode,
        )
        output_schema = _datetime_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        time_mode = _enum_config(
            task.config,
            "time_mode",
            default="fixed",
            allowed={"fixed", "per_row"},
            node_type=self.node_type,
        )
        format_mode = _enum_config(
            task.config,
            "format_mode",
            default="iso",
            allowed={"iso", "strftime", "template"},
            node_type=self.node_type,
        )
        fixed_value = (
            _datetime_formatted_value(
                utc_now(),
                config=task.config,
                format_mode=format_mode,
            )
            if time_mode == "fixed"
            else None
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    value = fixed_value
                    if value is None:
                        value = _datetime_formatted_value(
                            utc_now(),
                            config=task.config,
                            format_mode=format_mode,
                        )
                    output_rows.append(dict(row) | {output_field: value})
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )
