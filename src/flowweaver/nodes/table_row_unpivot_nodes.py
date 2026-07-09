from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import UNPIVOT_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_row_unpivot_helpers import (
    unpivot_output_rows as _unpivot_output_rows,
)
from flowweaver.nodes.table_row_unpivot_helpers import (
    unpivot_row_selected as _unpivot_row_selected,
)
from flowweaver.nodes.table_row_unpivot_helpers import (
    unpivot_row_selector as _unpivot_row_selector,
)
from flowweaver.nodes.table_row_unpivot_helpers import (
    unpivot_rows_config as _unpivot_rows_config,
)
from flowweaver.nodes.table_row_unpivot_helpers import (
    unpivot_rows_output_schema as _unpivot_rows_output_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class UnpivotRowsNodeHandler:
    node_type = UNPIVOT_ROWS_NODE_TYPE

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
        config = _unpivot_rows_config(task.config, input_ref=input_ref)
        output_schema = _unpivot_rows_output_schema(
            input_ref.schema,
            keep_fields=config["keep_fields"],
            output_value_field=config["output_value_field"],
            source_field_name=config["source_field_name"],
            original_row_field=config["original_row_field"],
            status_field=config["status_field"],
        )
        row_selector = _unpivot_row_selector(
            task.config,
            total_rows=context.count_rows(input_ref),
        )

        def output_batches():
            row_number = 1
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    if _unpivot_row_selected(row_number, row_selector):
                        output_rows.extend(
                            _unpivot_output_rows(
                                row,
                                row_number=row_number,
                                config=config,
                            )
                        )
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )

