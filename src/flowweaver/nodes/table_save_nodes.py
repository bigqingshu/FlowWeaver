from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import (
    SAVE_MEMORY_TABLE_NODE_TYPE,
    SAVE_RUN_TABLE_NODE_TYPE,
)
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import (
    named_output_config as _named_output_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import TableRole
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class SaveMemoryTableNodeHandler:
    node_type = SAVE_MEMORY_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        table_name = _named_output_config(
            task.config,
            node_type=self.node_type,
            keys=("table_name",),
        )
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveMemoryTableNode mode: {mode}"
            )
        memory_ref = context.create_memory_table_from_batches(
            task,
            logical_table_id=table_name,
            schema=input_ref.schema,
            row_batches=context.iter_row_batches(input_ref),
            role=TableRole.AUXILIARY,
        )
        return [input_ref, memory_ref]


class SaveRunTableNodeHandler:
    node_type = SAVE_RUN_TABLE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        save_memory = _bool_config(
            task.config,
            "save_memory",
            default=True,
        )
        if not save_memory:
            return [input_ref]
        table_name = _named_output_config(
            task.config,
            node_type=self.node_type,
            keys=("transit_name", "table_name"),
        )
        mode = str(task.config.get("mode", "overwrite"))
        if mode != "overwrite":
            raise _NodeValidationError(
                f"Unsupported SaveRunTableNode mode: {mode}"
            )
        rows = context.read_all_rows(input_ref)
        memory_ref = context.create_memory_table(
            task,
            logical_table_id=table_name,
            schema=input_ref.schema,
            rows=rows,
            role=TableRole.AUXILIARY,
        )
        return [input_ref, memory_ref]
