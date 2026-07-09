from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    LoopIterationNodeRunRecord,
    LoopIterationRunRecord,
    LoopRunRecord,
)
from flowweaver.engine.runtime_loop_iteration_node_run_queries import (
    get_loop_iteration_node_run_from_session as _get_iteration_node_run,
)
from flowweaver.engine.runtime_loop_iteration_node_run_queries import (
    list_loop_iteration_node_runs_by_node_run_from_session as _list_by_node_run,
)
from flowweaver.engine.runtime_loop_iteration_node_run_queries import (
    list_loop_iteration_node_runs_from_session as _list_iteration_node_runs,
)
from flowweaver.engine.runtime_loop_iteration_table_ref_store import (
    RuntimeLoopIterationTableRefStoreMixin,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_node_run_from_record,
)
from flowweaver.engine.runtime_loop_validators import (
    validate_loop_node_run as _validate_loop_node_run,
)
from flowweaver.engine.runtime_models import LoopIterationNodeRun
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
)


class RuntimeLoopIterationNodeRunStoreMixin(RuntimeLoopIterationTableRefStoreMixin):
    _session_factory: sessionmaker[Session]

    def add_loop_iteration_node_run(
        self,
        *,
        loop_iteration_id: str,
        node_run_id: str,
        node_instance_id: str | None = None,
        role: str = "BODY",
    ) -> LoopIterationNodeRun | None:
        if not role:
            raise ValueError("Loop iteration node run role cannot be empty")
        now = utc_now()
        try:
            with self._session_factory.begin() as session:
                iteration = session.get(LoopIterationRunRecord, loop_iteration_id)
                if iteration is None:
                    raise ValueError(f"Loop iteration not found: {loop_iteration_id}")
                loop = session.get(LoopRunRecord, iteration.loop_run_id)
                if loop is None:
                    raise ValueError(f"Loop run not found: {iteration.loop_run_id}")
                node_run = _validate_loop_node_run(
                    session,
                    loop=loop,
                    node_run_id=node_run_id,
                )
                resolved_node_instance_id = (
                    node_instance_id
                    if node_instance_id is not None
                    else node_run.node_instance_id
                )
                if resolved_node_instance_id != node_run.node_instance_id:
                    raise ValueError(
                        "Loop node instance id does not match node run: "
                        f"{resolved_node_instance_id}"
                    )
                record = LoopIterationNodeRunRecord(
                    loop_iteration_id=loop_iteration_id,
                    node_run_id=node_run_id,
                    node_instance_id=resolved_node_instance_id,
                    role=role,
                    created_at=_datetime_to_text(now),
                )
                session.add(record)
            return _loop_iteration_node_run_from_record(record)
        except IntegrityError:
            return self.get_loop_iteration_node_run(
                loop_iteration_id=loop_iteration_id,
                node_run_id=node_run_id,
            )

    def get_loop_iteration_node_run(
        self,
        *,
        loop_iteration_id: str,
        node_run_id: str,
    ) -> LoopIterationNodeRun | None:
        with self._session_factory() as session:
            return _get_iteration_node_run(
                session,
                loop_iteration_id=loop_iteration_id,
                node_run_id=node_run_id,
            )

    def list_loop_iteration_node_runs(
        self,
        loop_iteration_id: str,
        *,
        node_instance_id: str | None = None,
        role: str | None = None,
    ) -> list[LoopIterationNodeRun]:
        with self._session_factory() as session:
            return _list_iteration_node_runs(
                session,
                loop_iteration_id,
                node_instance_id=node_instance_id,
                role=role,
            )

    def list_loop_iteration_node_runs_by_node_run(
        self,
        node_run_id: str,
    ) -> list[LoopIterationNodeRun]:
        with self._session_factory() as session:
            return _list_by_node_run(session, node_run_id)
