from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from flowweaver.engine.db_models import (
    InputSnapshotRecord,
    ReadLeaseRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
)
from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    ReadLease,
    SharedPublication,
    SharedPublicationMember,
)
from flowweaver.engine.runtime_record_codecs import (
    _datetime_from_text,
    _json_dumps,
    _optional_datetime_from_text,
)


def _shared_publication_from_records(
    record: SharedPublicationRecord,
    members: Iterable[SharedPublicationMemberRecord],
) -> SharedPublication:
    return SharedPublication(
        publication_id=record.publication_id,
        share_name=record.share_name,
        publication_version=record.publication_version,
        producer_workflow_id=record.producer_workflow_id,
        producer_run_id=record.producer_run_id,
        status=record.status,
        input_snapshot_id=record.input_snapshot_id,
        retention_policy=json.loads(record.retention_policy_json),
        created_at=_datetime_from_text(record.created_at),
        members=tuple(
            _shared_publication_member_from_record(member) for member in members
        ),
    )


def _shared_publication_member_from_record(
    record: SharedPublicationMemberRecord,
) -> SharedPublicationMember:
    return SharedPublicationMember(
        publication_id=record.publication_id,
        export_name=record.export_name,
        table_ref_id=record.table_ref_id,
        exact_table_version=record.exact_table_version,
    )


def _input_snapshot_from_record(record: InputSnapshotRecord) -> InputSnapshot:
    snapshot = json.loads(record.snapshot_json)
    return InputSnapshot(
        input_snapshot_id=record.input_snapshot_id,
        workflow_run_id=record.workflow_run_id,
        inputs=tuple(
            _input_snapshot_entry_from_json(item) for item in snapshot.get("inputs", [])
        ),
        created_at=_datetime_from_text(record.created_at),
    )


def _input_snapshot_entry_to_json(
    entry: InputSnapshotEntry,
) -> dict[str, Any]:
    return {
        "source_name": entry.source_name,
        "publication_id": entry.publication_id,
        "publication_version": entry.publication_version,
        "selected_members": list(entry.selected_members),
    }


def _input_snapshot_entry_from_json(
    value: Mapping[str, Any],
) -> InputSnapshotEntry:
    selected_members = value.get("selected_members", [])
    return InputSnapshotEntry(
        source_name=str(value["source_name"]),
        publication_id=str(value["publication_id"]),
        publication_version=int(value["publication_version"]),
        selected_members=tuple(str(item) for item in selected_members),
    )


def _input_snapshot_json(inputs: tuple[InputSnapshotEntry, ...]) -> str:
    return _json_dumps(
        {"inputs": [_input_snapshot_entry_to_json(item) for item in inputs]}
    )


def _selected_members_json(selected_members: tuple[str, ...]) -> str:
    return json.dumps(
        list(selected_members),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _read_lease_from_record(record: ReadLeaseRecord) -> ReadLease:
    return ReadLease(
        lease_id=record.lease_id,
        publication_id=record.publication_id,
        publication_version=record.publication_version,
        selected_members=tuple(
            str(item) for item in json.loads(record.selected_members_json)
        ),
        consumer_workflow_run_id=record.consumer_workflow_run_id,
        acquired_at=_datetime_from_text(record.acquired_at),
        expires_at=_datetime_from_text(record.expires_at),
        released_at=_optional_datetime_from_text(record.released_at),
    )
