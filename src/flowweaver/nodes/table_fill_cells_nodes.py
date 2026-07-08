from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import FILL_CELLS_NODE_TYPE
from flowweaver.nodes.table_node_common import is_empty_cell as _is_empty_cell
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
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
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import has_field
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class FillCellsNodeHandler:
    node_type = FILL_CELLS_NODE_TYPE

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
        if not has_field(input_ref.schema, target_field):
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        value_source = _fill_cells_value_source_config(task.config)
        start_row = _positive_int_config(
            task.config,
            "start_row",
            default=1,
            node_type=self.node_type,
        )
        direction = _enum_config(
            task.config,
            "direction",
            default="down",
            allowed={"down", "up"},
            node_type=self.node_type,
        )
        count = _optional_positive_int_config(
            task.config,
            "count",
            node_type=self.node_type,
        )
        overwrite_rule = _enum_config(
            task.config,
            "overwrite_rule",
            default="all",
            allowed={"all", "empty_only"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        if start_row > total_rows and total_rows > 0:
            raise _NodeValidationError("FillCellsNode config.start_row is out of range")
        selected_rows = _fill_cells_selected_rows(
            start_row=start_row,
            direction=direction,
            count=count,
            total_rows=total_rows,
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if row_number in selected_rows and (
                        overwrite_rule == "all" or _is_empty_cell(row.get(target_field))
                    ):
                        try:
                            output_rows.append(
                                row | {target_field: value_source.resolve(row)}
                            )
                        except ValueSourceError as exc:
                            raise _NodeValidationError(str(exc)) from exc
                    else:
                        output_rows.append(row)
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=output_batches(),
        )


def _fill_cells_value_source_config(config: dict[str, Any]):
    return _value_source_config(
        config,
        "value_source",
        fallback_key="manual_value",
    )


def _fill_cells_selected_rows(
    *,
    start_row: int,
    direction: str,
    count: int | None,
    total_rows: int,
) -> set[int]:
    if total_rows <= 0:
        return set()
    if direction == "down":
        end_row = (
            total_rows
            if count is None
            else min(total_rows, start_row + count - 1)
        )
        return set(range(start_row, end_row + 1))
    end_row = 1 if count is None else max(1, start_row - count + 1)
    return set(range(end_row, start_row + 1))
