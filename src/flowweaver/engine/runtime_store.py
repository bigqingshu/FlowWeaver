from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    RuntimeEventRecord,
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
from flowweaver.engine.runtime_models import (
    RuntimeEventLog,
)
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
from flowweaver.engine.runtime_record_mappers import (
    _data_ref_from_model,
    _datetime_to_text,
    _json_dumps,
    _runtime_event_from_record,
    _table_ref_from_record,
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
from flowweaver.protocols.events import EventModel
from flowweaver.protocols.table_ref import TableRefModel


class RuntimeStore(
    RuntimeWorkflowDefinitionStoreMixin,
    RuntimeWorkflowRunStoreMixin,
    RuntimeWorkflowProcessStoreMixin,
    RuntimeNodeRunStoreMixin,
    RuntimeLoopStoreMixin,
    RuntimeSharedTableStoreMixin,
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

    def append_runtime_event(self, event: EventModel) -> int:
        with self._session_factory.begin() as session:
            record = RuntimeEventRecord(
                event_id=event.event_id,
                event_version=event.event_version,
                event_type=event.event_type.value,
                timestamp=_datetime_to_text(event.timestamp),
                workflow_run_id=event.workflow_run_id,
                node_run_id=event.node_run_id,
                payload_json=_json_dumps(event.payload),
            )
            session.add(record)
            session.flush()
            return record.sequence_number

    def list_runtime_events(
        self,
        *,
        after_sequence_number: int | None = None,
        workflow_run_id: str | None = None,
        node_run_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[RuntimeEventLog]:
        limit = max(1, min(limit, 1000))
        statement = select(RuntimeEventRecord).order_by(
            RuntimeEventRecord.sequence_number
        )
        if after_sequence_number is not None:
            statement = statement.where(
                RuntimeEventRecord.sequence_number > after_sequence_number
            )
        if workflow_run_id is not None:
            statement = statement.where(
                RuntimeEventRecord.workflow_run_id == workflow_run_id
            )
        if node_run_id is not None:
            statement = statement.where(RuntimeEventRecord.node_run_id == node_run_id)
        if event_type is not None:
            statement = statement.where(RuntimeEventRecord.event_type == event_type)
        with self._session_factory() as session:
            return [
                _runtime_event_from_record(record)
                for record in session.scalars(statement.limit(limit))
            ]

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_sqlite_engine(database_url)
