from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from flowweaver.common.database import create_sqlite_engine, sqlite_url
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
from flowweaver.engine.runtime_shared_publication_store import (
    RuntimeSharedPublicationStoreMixin,
)
from flowweaver.engine.runtime_shared_table_store import (
    RuntimeSharedTableStoreMixin,
)
from flowweaver.engine.runtime_status_guards import (
    TERMINAL_WORKFLOW_STATUS_VALUES as TERMINAL_WORKFLOW_STATUS_VALUES,
)
from flowweaver.engine.runtime_table_ref_store import RuntimeTableRefStoreMixin
from flowweaver.engine.runtime_workflow_definition_store import (
    RuntimeWorkflowDefinitionStoreMixin,
)
from flowweaver.engine.runtime_workflow_process_store import (
    RuntimeWorkflowProcessStoreMixin,
)
from flowweaver.engine.runtime_workflow_run_store import (
    RuntimeWorkflowRunStoreMixin,
)


class RuntimeStore(
    RuntimeWorkflowDefinitionStoreMixin,
    RuntimeWorkflowRunStoreMixin,
    RuntimeWorkflowProcessStoreMixin,
    RuntimeNodeRunStoreMixin,
    RuntimeNodeTaskStoreMixin,
    RuntimeTableRefStoreMixin,
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

    def dispose(self) -> None:
        self.engine.dispose()


def create_runtime_engine(database_url: str) -> Engine:
    return create_sqlite_engine(database_url)
