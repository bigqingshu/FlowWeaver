from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.runtime_models import SharedPublication
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _shared_publication_from_records,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    get_shared_publication_member_records as _get_shared_publication_member_records,
)
from flowweaver.protocols.enums import LifecycleStatus, TableMutability


class RuntimeSharedPublicationStoreMixin:
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
