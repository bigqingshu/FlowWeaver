from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flowweaver.engine.runtime_event_sink import RuntimeEventSink
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.workflow.definition import (
    RuntimeOptionsWorkflowModel,
    WorkflowDefinitionModel,
)
from flowweaver.workflow_process.controller import (
    initialize_node_runs,
    recover_ready_nodes,
)
from flowweaver.workflow_process.dag import WorkflowDag
from flowweaver.workflow_process.loop_recovery import (
    recover_serial_loop_runtime_state,
)
from flowweaver.workflow_process.loop_runtime_initialization import (
    initialize_enabled_loop_runtime_state,
)
from flowweaver.workflow_process.node_tasks import NodeTaskManager


@dataclass(frozen=True)
class WorkflowProcessRuntimeInitialization:
    task_manager: NodeTaskManager
    table_provider_registry: TableProviderRegistry


def initialize_workflow_process_runtime(
    *,
    store: RuntimeStore,
    event_sink: RuntimeEventSink,
    definition: WorkflowDefinitionModel,
    workflow_run_id: str,
    process_id: str,
    process_generation: int | None,
    dag: WorkflowDag,
    runtime_dir: Path,
    runtime_options_by_node: dict[str, RuntimeOptionsWorkflowModel],
) -> WorkflowProcessRuntimeInitialization:
    initialize_node_runs(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    initialize_enabled_loop_runtime_state(
        store,
        definition=definition,
        workflow_run_id=workflow_run_id,
        dag=dag,
    )
    recover_ready_nodes(
        store,
        workflow_run_id=workflow_run_id,
        process_id=process_id,
        process_generation=process_generation,
        dag=dag,
    )
    table_provider_registry = create_default_table_provider_registry(runtime_dir)
    recover_serial_loop_runtime_state(
        store,
        table_provider_registry,
        workflow_run_id=workflow_run_id,
        dag=dag,
        process_id=process_id,
        process_generation=process_generation,
    )
    task_manager = NodeTaskManager(
        store=store,
        event_sink=event_sink,
        dag=dag,
        failure_policy_mode=definition.failure_policy.mode,
        runtime_options_by_node=runtime_options_by_node,
        table_provider_registry=table_provider_registry,
    )
    return WorkflowProcessRuntimeInitialization(
        task_manager=task_manager,
        table_provider_registry=table_provider_registry,
    )
