from __future__ import annotations

from datetime import timedelta

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
    SharedTableVersionPolicy,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    SharedTableNodeValidationError as _NodeValidationError,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    publish_shared_tables_config as _publish_shared_tables_config,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    read_shared_tables_config as _read_shared_tables_config,
)
from flowweaver.nodes.builtin_shared_table_helpers import (
    shared_publication_ref as _shared_publication_ref,
)
from flowweaver.protocols.node_task import NodeTaskModel


def execute_publish_shared_tables(
    task: NodeTaskModel,
    *,
    store: RuntimeStore,
) -> list[str]:
    if not task.input_refs:
        raise _NodeValidationError(
            "PublishSharedTablesNode requires at least one input_ref"
        )
    config = _publish_shared_tables_config(
        task.config,
        input_ref_count=len(task.input_refs),
    )
    workflow = store.get_workflow_run(task.workflow_run_id)
    if workflow is None:
        raise _NodeValidationError(f"Workflow run not found: {task.workflow_run_id}")
    publication = store.create_shared_publication(
        share_name=config.share_name,
        producer_workflow_id=workflow.workflow_id,
        producer_run_id=task.workflow_run_id,
        members=dict(zip(config.export_names, task.input_refs, strict=True)),
        retention_policy=config.retention_policy,
    )
    return [_shared_publication_ref(publication)]


def execute_read_shared_tables(
    task: NodeTaskModel,
    *,
    reader: SharedTableReader,
) -> tuple[list[str], dict[str, str]]:
    if task.input_refs:
        raise _NodeValidationError("ReadSharedTablesNode does not accept inputs")
    config = _read_shared_tables_config(task.config)
    result = reader.read(
        consumer_workflow_run_id=task.workflow_run_id,
        share_name=config.share_name,
        version_policy=SharedTableVersionPolicy(config.version_policy),
        exact_version=config.exact_version,
        selected_members=config.selected_members,
        lease_expires_at=utc_now() + timedelta(seconds=task.timeout_seconds),
    )
    output_refs = [table_ref.table_ref_id for table_ref in result.table_refs]
    selected_member_names = result.input_snapshot.inputs[0].selected_members
    return (
        output_refs,
        dict(zip(selected_member_names, output_refs, strict=True)),
    )
