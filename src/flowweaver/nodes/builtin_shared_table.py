from __future__ import annotations

from collections.abc import Iterable

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
)
from flowweaver.nodes.builtin_shared_table_execution import (
    execute_publish_shared_tables as _execute_publish_shared_tables,
)
from flowweaver.nodes.builtin_shared_table_execution import (
    execute_read_shared_tables as _execute_read_shared_tables,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    SharedTableNodeValidationError as _NodeValidationError,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    single_out_binding as _single_out_binding,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel

PUBLISH_SHARED_TABLES_NODE_TYPE = "PublishSharedTablesNode"
READ_SHARED_TABLES_NODE_TYPE = "ReadSharedTablesNode"


class BuiltinSharedTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        reader: SharedTableReader | None = None,
    ) -> None:
        self._store = store
        self._reader = reader or SharedTableReader(store)

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            if task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE:
                output_refs = self._execute_publish(task)
                output_slot_bindings = _single_out_binding(output_refs)
            elif task.node_type == READ_SHARED_TABLES_NODE_TYPE:
                output_refs, output_slot_bindings = self._execute_read(task)
            else:
                raise _NodeValidationError(
                    f"Unsupported builtin shared table node type: {task.node_type}"
                )
        except (KeyError, ValueError) as exc:
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.FAILED,
                error={
                    "error_code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "origin": ErrorOrigin.NODE.value,
                },
                started_at=started_at,
                finished_at=utc_now(),
            )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=output_refs,
            output_slot_bindings=output_slot_bindings,
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_publish(self, task: NodeTaskModel) -> list[str]:
        return _execute_publish_shared_tables(task, store=self._store)

    def _execute_read(self, task: NodeTaskModel) -> tuple[list[str], dict[str, str]]:
        return _execute_read_shared_tables(task, reader=self._reader)


def shared_table_node_types() -> tuple[str, str]:
    return (PUBLISH_SHARED_TABLES_NODE_TYPE, READ_SHARED_TABLES_NODE_TYPE)


def is_shared_table_node_type(
    node_type: str,
    node_types: Iterable[str] | None = None,
) -> bool:
    candidates = (
        tuple(node_types) if node_types is not None else shared_table_node_types()
    )
    return node_type in candidates
