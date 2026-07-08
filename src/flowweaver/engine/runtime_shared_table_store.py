from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, select
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
from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    ReadLease,
    SharedPublication,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _input_snapshot_from_record,
    _input_snapshot_json,
    _json_dumps,
    _read_lease_from_record,
    _selected_members_json,
    _shared_publication_from_records,
)
from flowweaver.protocols.enums import LifecycleStatus, TableMutability


class RuntimeSharedTableStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_shared_publication(
        self,
        *,
        share_name: str,
        producer_workflow_id: str,
        producer_run_id: str,
        members: Mapping[str, str],
        publication_id: str | None = None,
        input_snapshot_id: str | None = None,
        retention_policy: dict[str, Any] | None = None,
    ) -> SharedPublication:
        if not members:
            raise ValueError("Shared publication requires at least one member")

        now = utc_now()
        publication_id = publication_id or new_id()
        member_records: list[SharedPublicationMemberRecord] = []
        with self._session_factory.begin() as session:
            producer_run = session.get(WorkflowRunRecord, producer_run_id)
            if producer_run is None:
                raise ValueError(f"Producer run not found: {producer_run_id}")
            if producer_run.workflow_id != producer_workflow_id:
                raise ValueError(
                    f"Producer run does not belong to workflow: {producer_run_id}"
                )
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
                if (
                    table_ref_record.mutability
                    != TableMutability.PUBLISHED_IMMUTABLE.value
                ):
                    raise ValueError(
                        "Shared publication member must be PUBLISHED_IMMUTABLE: "
                        f"{table_ref_id}"
                    )
                table_ref_records[export_name] = table_ref_record

            max_version = cast(
                int | None,
                session.scalar(
                    select(func.max(SharedPublicationRecord.publication_version)).where(
                        SharedPublicationRecord.share_name == share_name
                    )
                ),
            )
            publication_version = 1 if max_version is None else max_version + 1
            publication_record = SharedPublicationRecord(
                publication_id=publication_id,
                share_name=share_name,
                publication_version=publication_version,
                producer_workflow_id=producer_workflow_id,
                producer_run_id=producer_run_id,
                status="PUBLISHED",
                input_snapshot_id=input_snapshot_id,
                retention_policy_json=_json_dumps(retention_policy or {}),
                created_at=_datetime_to_text(now),
            )
            session.add(publication_record)
            session.flush()
            for export_name, table_ref_record in table_ref_records.items():
                member_record = SharedPublicationMemberRecord(
                    publication_id=publication_id,
                    export_name=export_name,
                    table_ref_id=table_ref_record.table_ref_id,
                    exact_table_version=table_ref_record.version,
                )
                session.add(member_record)
                member_records.append(member_record)
            session.flush()
            return _shared_publication_from_records(
                publication_record,
                sorted(member_records, key=lambda record: record.export_name),
            )

    def get_shared_publication(
        self,
        publication_id: str,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.get(SharedPublicationRecord, publication_id)
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(session, publication_id),
            )

    def get_shared_publication_version(
        self,
        *,
        share_name: str,
        publication_version: int,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(SharedPublicationRecord)
                .where(SharedPublicationRecord.share_name == share_name)
                .where(
                    SharedPublicationRecord.publication_version == publication_version
                )
            )
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(
                    session,
                    record.publication_id,
                ),
            )

    def get_latest_shared_publication(
        self,
        share_name: str,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(SharedPublicationRecord)
                .where(SharedPublicationRecord.share_name == share_name)
                .order_by(SharedPublicationRecord.publication_version.desc())
                .limit(1)
            )
            if record is None:
                return None
            return _shared_publication_from_records(
                record,
                _get_shared_publication_member_records(
                    session,
                    record.publication_id,
                ),
            )

    def list_shared_publications(
        self,
        *,
        share_name: str | None = None,
        limit: int = 100,
    ) -> list[SharedPublication]:
        limit = max(1, min(limit, 1000))
        statement = select(SharedPublicationRecord).order_by(
            SharedPublicationRecord.share_name,
            SharedPublicationRecord.publication_version.desc(),
            SharedPublicationRecord.created_at.desc(),
        )
        if share_name is not None:
            statement = statement.where(
                SharedPublicationRecord.share_name == share_name
            )
        statement = statement.limit(limit)
        with self._session_factory() as session:
            records = session.scalars(statement).all()
            return [
                _shared_publication_from_records(
                    record,
                    _get_shared_publication_member_records(
                        session,
                        record.publication_id,
                    ),
                )
                for record in records
            ]

    def create_input_snapshot(
        self,
        *,
        workflow_run_id: str,
        inputs: Iterable[InputSnapshotEntry],
        input_snapshot_id: str | None = None,
    ) -> InputSnapshot:
        input_snapshot_id = input_snapshot_id or new_id()
        inputs_tuple = tuple(inputs)
        now = utc_now()
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            record = InputSnapshotRecord(
                input_snapshot_id=input_snapshot_id,
                workflow_run_id=workflow_run_id,
                snapshot_json=_input_snapshot_json(inputs_tuple),
                created_at=_datetime_to_text(now),
            )
            session.add(record)
            run.input_snapshot_id = input_snapshot_id
            session.flush()
            return _input_snapshot_from_record(record)

    def get_input_snapshot(
        self,
        input_snapshot_id: str,
    ) -> InputSnapshot | None:
        with self._session_factory() as session:
            record = session.get(InputSnapshotRecord, input_snapshot_id)
            if record is None:
                return None
            return _input_snapshot_from_record(record)

    def create_read_lease(
        self,
        *,
        publication_id: str,
        publication_version: int,
        consumer_workflow_run_id: str,
        selected_members: Iterable[str],
        expires_at: datetime,
        lease_id: str | None = None,
    ) -> ReadLease:
        lease_id = lease_id or new_id()
        selected_members_tuple = tuple(selected_members)
        now = utc_now()
        with self._session_factory.begin() as session:
            consumer_run = session.get(WorkflowRunRecord, consumer_workflow_run_id)
            if consumer_run is None:
                raise ValueError(
                    f"Consumer workflow run not found: {consumer_workflow_run_id}"
                )
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
            if publication.publication_version != publication_version:
                raise ValueError(
                    f"Read lease publication version mismatch: {publication_id}"
                )
            record = ReadLeaseRecord(
                lease_id=lease_id,
                publication_id=publication_id,
                publication_version=publication_version,
                consumer_workflow_run_id=consumer_workflow_run_id,
                selected_members_json=_selected_members_json(selected_members_tuple),
                acquired_at=_datetime_to_text(now),
                expires_at=_datetime_to_text(expires_at),
                released_at=None,
            )
            session.add(record)
            session.flush()
            return _read_lease_from_record(record)

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
        with self._session_factory.begin() as session:
            run = session.get(WorkflowRunRecord, workflow_run_id)
            if run is None:
                raise ValueError(f"Workflow run not found: {workflow_run_id}")
            _validate_input_snapshot_publications(session, inputs_tuple)
            publication = session.get(SharedPublicationRecord, publication_id)
            if publication is None:
                raise ValueError(f"Read lease publication not found: {publication_id}")
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

    def get_read_lease(self, lease_id: str) -> ReadLease | None:
        with self._session_factory() as session:
            record = session.get(ReadLeaseRecord, lease_id)
            if record is None:
                return None
            return _read_lease_from_record(record)

    def list_read_leases_by_workflow_run(
        self,
        workflow_run_id: str,
        *,
        active_only: bool = False,
    ) -> list[ReadLease]:
        statement = (
            select(ReadLeaseRecord)
            .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
            .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
        )
        if active_only:
            statement = statement.where(ReadLeaseRecord.released_at.is_(None))
            statement = statement.where(
                ReadLeaseRecord.expires_at > _datetime_to_text(utc_now())
            )
        with self._session_factory() as session:
            return [
                _read_lease_from_record(record) for record in session.scalars(statement)
            ]

    def release_read_lease(self, lease_id: str) -> ReadLease | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(ReadLeaseRecord, lease_id)
            if record is None:
                return None
            if record.released_at is None:
                record.released_at = _datetime_to_text(now)
            return _read_lease_from_record(record)

    def release_unreleased_read_leases_for_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[ReadLease]:
        now = utc_now()
        with self._session_factory.begin() as session:
            records = session.scalars(
                select(ReadLeaseRecord)
                .where(ReadLeaseRecord.consumer_workflow_run_id == workflow_run_id)
                .where(ReadLeaseRecord.released_at.is_(None))
                .order_by(ReadLeaseRecord.acquired_at, ReadLeaseRecord.lease_id)
            ).all()
            for record in records:
                record.released_at = _datetime_to_text(now)
            session.flush()
            return [_read_lease_from_record(record) for record in records]


def _get_shared_publication_member_records(
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


def _validate_input_snapshot_publications(
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
