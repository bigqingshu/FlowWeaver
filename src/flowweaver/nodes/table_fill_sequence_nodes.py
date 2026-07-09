from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import FILL_SEQUENCE_NODE_TYPE
from flowweaver.nodes.table_fill_sequence_output import (
    fill_sequence_output_schema as _fill_sequence_output_schema,
)
from flowweaver.nodes.table_fill_sequence_output import (
    format_sequence_value as _format_sequence_value,
)
from flowweaver.nodes.table_fill_sequence_selection import (
    fill_sequence_selected_index as _fill_sequence_selected_index,
)
from flowweaver.nodes.table_fill_sequence_selection import (
    fill_sequence_selector as _fill_sequence_selector,
)
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    non_negative_int_config as _non_negative_int_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
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
from flowweaver.nodes.table_numeric_datetime_nodes import _number_config
from flowweaver.nodes.table_ops import find_field
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class FillSequenceNodeHandler:
    node_type = FILL_SEQUENCE_NODE_TYPE

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
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, target_field) is None:
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        total_rows = context.count_rows(input_ref)
        selector = _fill_sequence_selector(
            task.config,
            input_ref=input_ref,
            total_rows=total_rows,
        )
        start_value = _number_config(
            task.config,
            "start_value",
            default=1,
            node_type=self.node_type,
        )
        step = _number_config(
            task.config,
            "step",
            default=1,
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )
        zero_pad = _non_negative_int_config(
            task.config,
            "zero_pad",
            default=0,
            node_type=self.node_type,
        )
        prefix = _optional_string_config(
            task.config,
            "prefix",
            node_type=self.node_type,
        )
        suffix = _optional_string_config(
            task.config,
            "suffix",
            node_type=self.node_type,
        )
        output_schema = _fill_sequence_output_schema(
            input_ref.schema,
            target_field=target_field,
            formatted=bool(prefix or suffix or zero_pad),
        )

        def output_batches():
            row_number = 1
            sequence_index = 0
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    selected_index = _fill_sequence_selected_index(
                        row,
                        row_number=row_number,
                        selector=selector,
                    )
                    should_fill = selected_index is not None and (
                        overwrite_rule == "all"
                        or _is_empty_cell(row.get(target_field))
                    )
                    if should_fill:
                        assert selected_index is not None
                        if selected_index <= 0:
                            sequence_index += 1
                            selected_index = sequence_index
                        output_rows.append(
                            dict(row) | {
                                target_field: _format_sequence_value(
                                    start_value + (selected_index - 1) * step,
                                    zero_pad=zero_pad,
                                    prefix=prefix,
                                    suffix=suffix,
                                )
                            }
                        )
                    else:
                        output_rows.append(dict(row))
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )
