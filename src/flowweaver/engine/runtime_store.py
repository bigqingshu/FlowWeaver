from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import DataRefRecord
from flowweaver.engine.runtime_event_store import RuntimeEventStoreMixin
from flowweaver.engine.runtime_input_snapshot_store import (
    RuntimeInputSnapshotStoreMixin,
)
from flowweaver.engine.runtime_loop_store import (
    RuntimeLoopStoreMixin,
)
from flowweaver.engine.runtime_models import InputSnapshot as InputSnapshot
from flowweaver.engine.runtime_models import InputSnapshotEntry as InputSnapshotEntry
from flowweaver.engine.runtime_models import (
    LoopIterationNodeRun as LoopIterationNodeRun,
)
from flowweaver.engine.runtime_models import (
    LoopIterationRun as LoopIterationRun,
)
from flowweaver.engine.runtime_models import (
    LoopIterationTableRef as LoopIterationTableRef,
)
from flowweaver.engine.runtime_models import (
    LoopRun as LoopRun,
)
from flowweaver.engine.runtime_models import (
    NodeRun as NodeRun,
)
from flowweaver.engine.runtime_models import ReadLease as ReadLease
from flowweaver.engine.runtime_models import RuntimeEventLog as RuntimeEventLog
from flowweaver.engine.runtime_models import SharedPublication as SharedPublication
from flowweaver.engine.runtime_models import (
    WorkflowProcess as WorkflowProcess,
)
from flowweaver.engine.runtime_models import (
    WorkflowRun as WorkflowRun,
)
from flowweaver.engine.runtime_node_run_store import (
    RuntimeNodeRunStoreMixin,
)
from flowweaver.engine.runtime_node_task_store import (
    RuntimeNodeTaskStoreMixin,
)
from flowweaver.engine.runtime_read_lease_store import (
    RuntimeReadLeaseStoreMixin,
)
from flowweaver.engine.runtime_record_mappers import (
    _data_ref_from_model,
    _datetime_to_text,
    _table_ref_from_record,
)
from flowweaver.engine.runtime_shared_publication_store import (
    RuntimeSharedPublicationStoreMixin,
)
from flowweaver.engine.runtime_shared_table_store import (
    RuntimeSharedTableStoreMixin,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUS_VALUES as TERMINAL_WORKFLOW_STATUS_VALUES,
)
from flowweaver.engine.runtime_workflow_definition_store import (
    RuntimeWorkflowDefinitionStoreMixin,
)
from flowweaver.engine.runtime_workflow_process_store import (
    RuntimeWorkflowProcessStoreMixin,
)
from flowweaver.engine.runtime_workflow_run_store import (
    RuntimeWorkflowRunStoreMixin,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
)
from flowweaver.protocols.table_ref import TableRefModel


class RuntimeStore(
    RuntimeWorkflowDefinitionStoreMixin,
    RuntimeWorkflowRunStoreMixin,
    RuntimeWorkflowProcessStoreMixin,
    RuntimeNodeRunStoreMixin,
    RuntimeNodeTaskStoreMixin,
    RuntimeEventStoreMixin,
    RuntimeLoopStoreMixin,
    RuntimeSharedPublicationStoreMixin,
    RuntimeSharedTableStoreMixin,
    RuntimeInputSnapshotStoreMixin,
    RuntimeReadLeaseStoreMixin,
):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = create_sqlite_engine(database_url)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_sqlite_path(cls, path: str | Path) -> RuntimeStore:
        return cls(sqlite_url(path))

    def register_table_ref(self, table_ref: TableRefModel) -> None:
        with self._session_factory.begin() as session:
            session.add(_data_ref_from_model(table_ref))

    def get_table_ref(self, table_ref_id: str) -> TableRefModel | None:
        with self._session_factory() as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None:
                return None
            return _table_ref_from_record(record)

    def list_table_refs_by_workflow_run(
        self,
        workflow_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DataRefRecord)
                .where(DataRefRecord.workflow_run_id == workflow_run_id)
                .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
            ).all()
            return [_table_ref_from_record(record) for record in records]

    def list_table_refs_by_node_run(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
    ) -> list[TableRefModel]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DataRefRecord)
                .where(DataRefRecord.workflow_run_id == workflow_run_id)
                .where(DataRefRecord.node_run_id == node_run_id)
                .order_by(DataRefRecord.created_at, DataRefRecord.table_ref_id)
            ).all()
            return [_table_ref_from_record(record) for record in records]

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

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_sqlite_engine(database_url)
