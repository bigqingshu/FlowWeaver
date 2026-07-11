from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import (
    DataRefRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import InputSnapshotEntry
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableStorageKind,
)


def get_shared_publication_member_records(
    session: Session,
    publication_id: str,
) -> list[SharedPublicationMemberRecord]:
    return list(
        session.scalars(
            select(SharedPublicationMemberRecord)
            .where(SharedPublicationMemberRecord.publication_id == publication_id)
            .order_by(SharedPublicationMemberRecord.export_name)
        ).all()
    )


def require_shared_publication_producer_run(
    session: Session,
    *,
    producer_run_id: str,
    producer_workflow_id: str,
) -> WorkflowRunRecord:
    producer_run = session.get(WorkflowRunRecord, producer_run_id)
    if producer_run is None:
        raise ValueError(f"Producer run not found: {producer_run_id}")
    if producer_run.workflow_id != producer_workflow_id:
        raise ValueError(
            f"Producer run does not belong to workflow: {producer_run_id}"
        )
    return producer_run


def validate_shared_publication_members(
    session: Session,
    *,
    producer_run_id: str,
    members: Mapping[str, str],
) -> dict[str, DataRefRecord]:
    table_ref_records: dict[str, DataRefRecord] = {}
    for export_name, table_ref_id in members.items():
        table_ref_record = session.get(DataRefRecord, table_ref_id)
        if table_ref_record is None:
            raise ValueError(f"TableRef not found: {table_ref_id}")
        if table_ref_record.workflow_run_id != producer_run_id:
            raise ValueError(
                "Shared publication member does not belong to "
                f"producer run: {table_ref_id}"
            )
        if table_ref_record.lifecycle_status != LifecycleStatus.PUBLISHED.value:
            raise ValueError(
                f"Shared publication member must be PUBLISHED: {table_ref_id}"
            )
        if table_ref_record.mutability != TableMutability.PUBLISHED_IMMUTABLE.value:
            raise ValueError(
                "Shared publication member must be PUBLISHED_IMMUTABLE: "
                f"{table_ref_id}"
            )
        if table_ref_record.storage_kind == TableStorageKind.MEMORY.value:
            raise ValueError(
                "SHARED_TABLE_STORAGE_NOT_DURABLE: "
                f"Shared publication member must use RUNTIME_SQL: {table_ref_id}"
            )
        if table_ref_record.storage_kind == TableStorageKind.EXTERNAL_SQL.value:
            raise ValueError(
                "SHARED_TABLE_REQUIRES_MATERIALIZED_SNAPSHOT: "
                f"Shared publication member must use RUNTIME_SQL: {table_ref_id}"
            )
        if table_ref_record.storage_kind != TableStorageKind.RUNTIME_SQL.value:
            raise ValueError(
                "SHARED_TABLE_STORAGE_UNSUPPORTED: "
                f"Shared publication member must use RUNTIME_SQL: {table_ref_id}"
            )
        table_ref_records[export_name] = table_ref_record
    return table_ref_records


def next_shared_publication_version(
    session: Session,
    *,
    share_name: str,
) -> int:
    max_version = cast(
        int | None,
        session.scalar(
            select(func.max(SharedPublicationRecord.publication_version)).where(
                SharedPublicationRecord.share_name == share_name
            )
        ),
    )
    return 1 if max_version is None else max_version + 1


def validate_input_snapshot_publications(
    session: Session,
    inputs: tuple[InputSnapshotEntry, ...],
) -> None:
    for item in inputs:
        publication = session.get(
            SharedPublicationRecord,
            item.publication_id,
        )
        if publication is None:
            raise ValueError(
                f"Input snapshot publication not found: {item.publication_id}"
            )
        if publication.publication_version != item.publication_version:
            raise ValueError(
                f"Input snapshot publication version mismatch: {item.publication_id}"
            )
