from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import DataRefRecord
from flowweaver.engine.runtime_models import RunTableDirectoryEntry
from flowweaver.engine.runtime_record_mappers import (
    _data_ref_from_model,
    _datetime_to_text,
    _table_ref_from_record,
)
from flowweaver.engine.runtime_table_ref_queries import (
    count_table_ref_directory_from_session as _count_table_ref_directory,
)
from flowweaver.engine.runtime_table_ref_queries import (
    get_latest_table_ref_by_logical_identity_from_session as _get_latest_by_identity,
)
from flowweaver.engine.runtime_table_ref_queries import (
    get_table_ref_from_session as _get_table_ref,
)
from flowweaver.engine.runtime_table_ref_queries import (
    list_table_ref_directory_by_ids_from_session as _list_directory_by_ids,
)
from flowweaver.engine.runtime_table_ref_queries import (
    list_table_ref_directory_from_session as _list_table_ref_directory,
)
from flowweaver.engine.runtime_table_ref_queries import (
    list_table_refs_by_ids_from_session as _list_by_ids,
)
from flowweaver.engine.runtime_table_ref_queries import (
    list_table_refs_by_node_run_from_session as _list_by_node_run,
)
from flowweaver.engine.runtime_table_ref_queries import (
    list_table_refs_by_workflow_run_from_session as _list_by_workflow_run,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableRole,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import TableRefModel


class RuntimeTableRefStoreMixin:
    _session_factory: sessionmaker[Session]

    def register_table_ref(self, table_ref: TableRefModel) -> None:
        with self._session_factory.begin() as session:
            session.add(_data_ref_from_model(table_ref))

    def get_table_ref(self, table_ref_id: str) -> TableRefModel | None:
        with self._session_factory() as session:
            return _get_table_ref(session, table_ref_id)

    def get_latest_table_ref_by_logical_identity(
        self,
        *,
        workflow_run_id: str,
        storage_kind: TableStorageKind,
        role: TableRole,
        logical_table_id: str,
    ) -> TableRefModel | None:
        with self._session_factory() as session:
            return _get_latest_by_identity(
                session,
                workflow_run_id=workflow_run_id,
                storage_kind=storage_kind,
                role=role,
                logical_table_id=logical_table_id,
            )

    def list_table_refs_by_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            return _list_by_workflow_run(session, workflow_run_id)

    def list_table_refs_by_ids(
        self,
        table_ref_ids: list[str],
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            return _list_by_ids(session, table_ref_ids)

    def list_table_ref_directory(
        self,
        workflow_run_id: str,
        *,
        node_run_id: str | None = None,
        table_type: str | None = None,
        lifecycle_statuses: Iterable[LifecycleStatus | str] | None = None,
        logical_table_id: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[RunTableDirectoryEntry]:
        with self._session_factory() as session:
            return _list_table_ref_directory(
                session,
                workflow_run_id,
                node_run_id=node_run_id,
                table_type=table_type,
                lifecycle_statuses=lifecycle_statuses,
                logical_table_id=logical_table_id,
                offset=offset,
                limit=limit,
            )

    def list_table_ref_directory_by_ids(
        self,
        table_ref_ids: list[str],
    ) -> list[RunTableDirectoryEntry]:
        with self._session_factory() as session:
            return _list_directory_by_ids(session, table_ref_ids)

    def count_table_ref_directory(
        self,
        workflow_run_id: str,
        *,
        node_run_id: str | None = None,
        table_type: str | None = None,
        lifecycle_statuses: Iterable[LifecycleStatus | str] | None = None,
        logical_table_id: str | None = None,
    ) -> int:
        with self._session_factory() as session:
            return _count_table_ref_directory(
                session,
                workflow_run_id,
                node_run_id=node_run_id,
                table_type=table_type,
                lifecycle_statuses=lifecycle_statuses,
                logical_table_id=logical_table_id,
            )

    def list_table_refs_by_node_run(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            return _list_by_node_run(
                session,
                workflow_run_id=workflow_run_id,
                node_run_id=node_run_id,
            )

    def mark_staging_table_ref_released(
        self,
        table_ref_id: str,
    ) -> TableRefModel | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if (
                record is None
                or record.lifecycle_status != LifecycleStatus.STAGING.value
            ):
                return None
            record.lifecycle_status = LifecycleStatus.RELEASED.value
            record.released_at = _datetime_to_text(now)
            return _table_ref_from_record(record)

    def mark_table_ref_released(
        self,
        table_ref_id: str,
    ) -> TableRefModel | None:
        now = utc_now()
        with self._session_factory.begin() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None or record.lifecycle_status in {
                LifecycleStatus.RELEASED.value,
                LifecycleStatus.RETIRED.value,
                LifecycleStatus.ORPHANED.value,
            }:
                return None
            record.lifecycle_status = LifecycleStatus.RELEASED.value
            record.released_at = _datetime_to_text(now)
            return _table_ref_from_record(record)
