from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.builtin_sql import SqlMappingNodeRunner
from flowweaver.nodes.builtin_table_execution_result import (
    BuiltinTableExecutionResult,
)
from flowweaver.nodes.builtin_table_registry import (
    create_builtin_table_node_handler_registry,
)
from flowweaver.nodes.builtin_table_result_metadata import (
    output_slot_bindings_for_result as _output_slot_bindings_for_result,
)
from flowweaver.nodes.builtin_table_result_metadata import (
    table_output_summary as _table_output_summary,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel


class BuiltinTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
        memory_provider: MemoryTableProvider | None = None,
    ) -> None:
        memory_provider = memory_provider or MemoryTableProvider()
        self._context = BuiltinTableNodeContext(
            store=store,
            registry=registry,
            table_provider=table_provider,
            memory_provider=memory_provider,
            sql_mapping_runner=SqlMappingNodeRunner(store=store),
        )
        self._handler_registry = create_builtin_table_node_handler_registry()

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            execution_result = self._execute_node(task)
        except BuiltinTableNodeValidationError as exc:
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
        output_refs = list(execution_result.output_refs)
        output_slot_bindings = dict(execution_result.output_slot_bindings)
        if not output_slot_bindings:
            output_slot_bindings = _output_slot_bindings_for_result(
                task,
                output_refs,
            )
        summary = _table_output_summary(
            output_refs,
            writes=execution_result.writes,
        )
        summary.update(execution_result.summary_details)
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[table_ref.table_ref_id for table_ref in output_refs],
            output_slot_bindings=output_slot_bindings,
            summary=summary,
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_node(self, task: NodeTaskModel) -> BuiltinTableExecutionResult:
        handler = self._handler_registry.get(task.node_type)
        if handler is not None:
            result = handler.execute(task, self._context)
            if isinstance(result, BuiltinTableExecutionResult):
                return result
            return BuiltinTableExecutionResult.from_output_refs(result)
        raise BuiltinTableNodeValidationError(
            f"Unsupported builtin node type: {task.node_type}"
        )
