from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    InputSnapshotRecord,
    ReadLeaseRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.immediate_session import run_immediate_transaction
from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    ReadLease,
    SharedTableReadAcquisition,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _table_ref_from_record,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _input_snapshot_from_record,
    _input_snapshot_json,
    _read_lease_from_record,
    _selected_members_json,
    _shared_publication_from_records,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    validate_input_snapshot_publications as _validate_input_snapshot_publications,
)
from flowweaver.protocols.enums import LifecycleStatus


class RuntimeSharedTableStoreMixin:
    engine: Engine
    _session_factory: sessionmaker[Session]

    def acquire_shared_table_read(
        self,
        *,
        workflow_run_id: str,
        share_name: str,
        version_policy: str,
        exact_version: int | None,
        selected_members: tuple[str, ...] | None,
        expires_at: datetime,
    ) -> SharedTableReadAcquisition:
        if version_policy == "EXACT_VERSION" and exact_version is None:
            raise ValueError("EXACT_VERSION requires exact_version")
        if version_policy not in {"LATEST", "EXACT_VERSION"}:
            raise ValueError(
                f"Unsupported shared table version policy: {version_policy}"
            )
        input_snapshot_id = new_id()
        lease_id = new_id()
        now = utc_now()

        def operation(session: Session) -> SharedTableReadAcquisition:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            publication_statement = (
                select(SharedPublicationRecord)
                .where(SharedPublicationRecord.share_name == share_name)
                .where(SharedPublicationRecord.status == "PUBLISHED")
            )
            if version_policy == "LATEST":
                publication_statement = publication_statement.order_by(
                    SharedPublicationRecord.publication_version.desc()
                ).limit(1)
            else:
                publication_statement = publication_statement.where(
                    SharedPublicationRecord.publication_version == exact_version
                )
            publication_record = session.scalar(publication_statement)
            if publication_record is None:
                raise ValueError(f"Shared publication not found: {share_name}")

            member_records = list(
                session.scalars(
                    select(SharedPublicationMemberRecord)
                    .where(
                        SharedPublicationMemberRecord.publication_id
                        == publication_record.publication_id
                    )
                    .order_by(SharedPublicationMemberRecord.export_name)
                )
            )
            if not member_records:
                raise ValueError(
                    "Shared publication has no members: "
                    f"{publication_record.publication_id}"
                )
            member_by_name = {
                member.export_name: member for member in member_records
            }
            if selected_members is None:
                selected_member_records = tuple(member_records)
            else:
                missing = [
                    name for name in selected_members if name not in member_by_name
                ]
                if missing:
                    raise ValueError(
                        "Shared publication members not found: "
                        + ",".join(sorted(missing))
                    )
                selected_member_records = tuple(
                    member_by_name[name] for name in selected_members
                )
            selected_member_names = tuple(
                member.export_name for member in selected_member_records
            )
            selected_table_ref_ids = {
                member.table_ref_id for member in selected_member_records
            }
            table_ref_records = {
                record.table_ref_id: record
                for record in session.scalars(
                    select(DataRefRecord).where(
                        DataRefRecord.table_ref_id.in_(selected_table_ref_ids)
                    )
                )
            }
            table_refs = []
            for member in selected_member_records:
                table_ref_record = table_ref_records.get(member.table_ref_id)
                if table_ref_record is None:
                    raise ValueError(f"TableRef not found: {member.table_ref_id}")
                if table_ref_record.version != member.exact_table_version:
                    raise ValueError(
                        "TableRef version mismatch for shared publication member: "
                        f"{member.export_name}"
                    )
                if (
                    table_ref_record.lifecycle_status
                    != LifecycleStatus.PUBLISHED.value
                ):
                    raise ValueError(
                        "TableRef unavailable for shared publication member: "
                        f"{member.export_name}"
                    )
                table_refs.append(_table_ref_from_record(table_ref_record))

            snapshot_input = InputSnapshotEntry(
                source_name=share_name,
                publication_id=publication_record.publication_id,
                publication_version=publication_record.publication_version,
                selected_members=selected_member_names,
            )
            snapshot_record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json((snapshot_input,)),
                created_at=_datetime_to_text(now),
            )
            lease_record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_record.publication_id,
                publication_version=publication_record.publication_version,
                consumer_workflow_run_id=workflow_run_id,
                selected_members_json=_selected_members_json(
                    selected_member_names
                ),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add_all([snapshot_record, lease_record])
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return SharedTableReadAcquisition(
                publication=_shared_publication_from_records(
                    publication_record,
                    member_records,
                ),
                table_refs=tuple(table_refs),
                input_snapshot=_input_snapshot_from_record(snapshot_record),
                read_lease=_read_lease_from_record(lease_record),
            )

        return run_immediate_transaction(self.engine, operation)

    def create_input_snapshot_and_read_lease(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        publication_id: str,
        publication_version: int,
        selected_members: Iterable[str],
        expires_at: datetime,
    ) -> tuple[InputSnapshot, ReadLease]:
        input_snapshot_id = new_id()
        lease_id = new_id()
        inputs_tuple = tuple(inputs)
        selected_members_tuple = tuple(selected_members)
        if len(inputs_tuple) != 1:
            raise ValueError(
                "Atomic input snapshot/read lease requires exactly one input"
            )
        snapshot_input = inputs_tuple[0]
        if snapshot_input.publication_id != publication_id:
            raise ValueError("Input snapshot and read lease publication mismatch")
        if snapshot_input.publication_version != publication_version:
            raise ValueError(
                "Input snapshot and read lease publication version mismatch"
            )
        if snapshot_input.selected_members != selected_members_tuple:
            raise ValueError("Input snapshot and read lease selected members mismatch")
        now = utc_now()

        def operation(session: Session) -> tuple[InputSnapshot, ReadLease]:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.status != "PUBLISHED":
                raise ValueError(
                    f"Read lease publication unavailable: {publication_id}"
                )
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            snapshot_record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
                created_at=_datetime_to_text(now),
            )
            lease_record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=workflow_run_id,
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add_all([snapshot_record, lease_record])
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return (
                _input_snapshot_from_record(snapshot_record),
                _read_lease_from_record(lease_record),
            )

        return run_immediate_transaction(self.engine, operation)
