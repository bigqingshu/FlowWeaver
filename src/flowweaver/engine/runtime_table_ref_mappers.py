from __future__ import annotations

import json

from flowweaver.engine.db_models import DataRefRecord
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def _data_ref_from_model(table_ref: TableRefModel) -> DataRefRecord:
    return DataRefRecord(
        table_ref_id=table_ref.table_ref_id,
        workflow_run_id=table_ref.created_by_workflow_run_id,
        node_run_id=table_ref.created_by_node_run_id,
        role=table_ref.role.value,
        storage_kind=table_ref.storage_kind.value,
        scope=table_ref.scope.value,
        mutability=table_ref.mutability.value,
        provider_id=table_ref.provider_id,
        resource_profile_id=table_ref.resource_profile_id,
        mount_id=table_ref.mount_id,
        logical_table_id=table_ref.logical_table_id,
        opaque_handle_json=_json_dumps(table_ref.opaque_handle),
        schema_json=json.dumps(
            [field.model_dump(mode="json") for field in table_ref.schema],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        schema_fingerprint=table_ref.schema_fingerprint,
        version=table_ref.version,
        capabilities_json=json.dumps(sorted(table_ref.capabilities)),
        lifecycle_status=table_ref.lifecycle_status.value,
        created_at=_datetime_to_text(table_ref.created_at),
        published_at=None,
        released_at=None,
    )


def _table_ref_from_record(record: DataRefRecord) -> TableRefModel:
    return TableRefModel(
        table_ref_id=record.table_ref_id,
        role=TableRole(record.role),
        storage_kind=TableStorageKind(record.storage_kind),
        scope=TableScope(record.scope),
        mutability=TableMutability(record.mutability),
        provider_id=record.provider_id,
        resource_profile_id=record.resource_profile_id,
        mount_id=record.mount_id,
        logical_table_id=record.logical_table_id,
        opaque_handle=json.loads(record.opaque_handle_json),
        schema=[
            FieldSchemaModel.model_validate(item)
            for item in json.loads(record.schema_json)
        ],
        schema_fingerprint=record.schema_fingerprint,
        version=record.version,
        capabilities=set(json.loads(record.capabilities_json)),
        lifecycle_status=LifecycleStatus(record.lifecycle_status),
        created_by_workflow_run_id=record.workflow_run_id,
        created_by_node_run_id=record.node_run_id,
        created_at=_datetime_from_text(record.created_at),
    )
