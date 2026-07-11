from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
)
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_models import SharedPublication
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
)
from flowweaver.engine.runtime_shared_publication_queries import (
    get_latest_shared_publication_from_session as _get_latest_publication,
)
from flowweaver.engine.runtime_shared_publication_queries import (
    get_shared_publication_from_session as _get_publication,
)
from flowweaver.engine.runtime_shared_publication_queries import (
    get_shared_publication_version_from_session as _get_publication_version,
)
from flowweaver.engine.runtime_shared_publication_queries import (
    list_shared_publications_from_session as _list_publications,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _shared_publication_from_records,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    next_shared_publication_version as _next_shared_publication_version,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    require_shared_publication_producer_run as _require_shared_publication_producer_run,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    validate_shared_publication_members as _validate_shared_publication_members,
)


class RuntimeSharedPublicationStoreMixin:
    engine: Engine
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
        with immediate_session(self.engine) as session:
            _require_shared_publication_producer_run(
                session,
                producer_run_id=producer_run_id,
                producer_workflow_id=producer_workflow_id,
            )
            table_ref_records = _validate_shared_publication_members(
                session,
                producer_run_id=producer_run_id,
                members=members,
            )
            publication_version = _next_shared_publication_version(
                session,
                share_name=share_name,
            )
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
            return _get_publication(session, publication_id)

    def get_shared_publication_version(
        self,
        *,
        share_name: str,
        publication_version: int,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            return _get_publication_version(
                session,
                share_name=share_name,
                publication_version=publication_version,
            )

    def get_latest_shared_publication(
        self,
        share_name: str,
    ) -> SharedPublication | None:
        with self._session_factory() as session:
            return _get_latest_publication(session, share_name)

    def list_shared_publications(
        self,
        *,
        share_name: str | None = None,
        limit: int = 100,
    ) -> list[SharedPublication]:
        with self._session_factory() as session:
            return _list_publications(
                session,
                share_name=share_name,
                limit=limit,
            )
