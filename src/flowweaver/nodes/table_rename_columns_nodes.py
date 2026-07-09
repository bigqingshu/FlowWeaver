from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import RENAME_COLUMNS_NODE_TYPE
from flowweaver.nodes.table_node_config import enum_config as _enum_config
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
from flowweaver.nodes.table_rename_columns_helpers import (
    rename_columns_apply_duplicate_policy as _rename_columns_apply_duplicate_policy,
)
from flowweaver.nodes.table_rename_columns_helpers import (
    rename_columns_proposed_names as _rename_columns_proposed_names,
)
from flowweaver.nodes.table_rename_columns_helpers import (
    rename_columns_schema as _rename_columns_schema,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class RenameColumnsNodeHandler:
    node_type = RENAME_COLUMNS_NODE_TYPE

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
        proposed_names = _rename_columns_proposed_names(
            task.config,
            input_ref=input_ref,
        )
        input_names = [field.name for field in input_ref.schema]
        output_names = _rename_columns_apply_duplicate_policy(
            input_names,
            proposed_names,
            duplicate_policy=_enum_config(
                task.config,
                "duplicate_policy",
                default="error",
                allowed={"error", "skip", "append_number"},
                node_type=self.node_type,
            ),
        )
        schema = _rename_columns_schema(input_ref.schema, output_names)
        source_to_output = {
            field.name: output_name
            for field, output_name in zip(input_ref.schema, output_names, strict=True)
        }

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    output_rows.append(
                        {
                            source_to_output[field.name]: row.get(field.name)
                            for field in input_ref.schema
                        }
                    )
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=schema,
            row_batches=output_batches(),
        )


