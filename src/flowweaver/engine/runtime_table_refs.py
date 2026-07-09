from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_table_sql import (
    identifier_token,
    schema_fingerprint,
    table_location,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def runtime_database_path(runtime_root: Path, workflow_run_id: str) -> Path:
    return runtime_root / f"{identifier_token(workflow_run_id)}.db"


def runtime_staging_table_ref(
    *,
    runtime_root: Path,
    provider_id: str,
    workflow_run_id: str,
    node_run_id: str,
    output_name: str,
    schema: Sequence[FieldSchemaModel],
    role: TableRole,
    version: int,
) -> TableRefModel:
    table_name = f"stg_{identifier_token(node_run_id)}_{identifier_token(output_name)}"
    return TableRefModel(
        table_ref_id=new_id(),
        role=role,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.WORKING_MUTABLE,
        provider_id=provider_id,
        logical_table_id=output_name,
        opaque_handle={
            "database_path": runtime_database_path(
                runtime_root,
                workflow_run_id,
            ).as_posix(),
            "table_name": table_name,
        },
        schema=list(schema),
        schema_fingerprint=schema_fingerprint(schema),
        version=version,
        capabilities={"READ", "APPEND"},
        lifecycle_status=LifecycleStatus.STAGING,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def published_runtime_table_ref_from_staging(
    staging_ref: TableRefModel,
    *,
    provider_id: str,
    version: int | None,
) -> TableRefModel:
    database_path, staging_table = table_location(staging_ref)
    published_version = staging_ref.version + 1 if version is None else version
    published_table = f"pub_{identifier_token(staging_table)}_v{published_version}"
    return TableRefModel(
        table_ref_id=new_id(),
        role=staging_ref.role,
        storage_kind=staging_ref.storage_kind,
        scope=staging_ref.scope,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id=provider_id,
        resource_profile_id=staging_ref.resource_profile_id,
        mount_id=staging_ref.mount_id,
        logical_table_id=staging_ref.logical_table_id,
        opaque_handle={
            "database_path": database_path.as_posix(),
            "table_name": published_table,
        },
        schema=staging_ref.schema,
        schema_fingerprint=staging_ref.schema_fingerprint,
        version=published_version,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=staging_ref.created_by_workflow_run_id,
        created_by_node_run_id=staging_ref.created_by_node_run_id,
        created_at=utc_now(),
    )
