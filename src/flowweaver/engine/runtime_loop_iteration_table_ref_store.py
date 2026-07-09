from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    LoopIterationRunRecord,
    LoopIterationTableRefRecord,
    LoopRunRecord,
)
from flowweaver.engine.runtime_loop_iteration_run_store import (
    RuntimeLoopIterationRunStoreMixin,
)
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_table_ref_from_record,
)
from flowweaver.engine.runtime_loop_validators import (
    validate_loop_table_ref as _validate_loop_table_ref,
)
from flowweaver.engine.runtime_models import LoopIterationTableRef
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
)
from flowweaver.protocols.enums import (
    LoopIterationTableRefRole,
)


class RuntimeLoopIterationTableRefStoreMixin(RuntimeLoopIterationRunStoreMixin):
    _session_factory: sessionmaker[Session]

    def add_loop_iteration_table_ref(
        self,
        *,
        loop_iteration_id: str,
        table_ref_id: str,
        role: LoopIterationTableRefRole | str,
    ) -> LoopIterationTableRef | None:
        role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
        now = utc_now()
        record = LoopIterationTableRefRecord(
            loop_iteration_id=loop_iteration_id,
            table_ref_id=table_ref_id,
            role=role_value,
            created_at=_datetime_to_text(now),
        )
        try:
            with self._session_factory.begin() as session:
                iteration = session.get(LoopIterationRunRecord, loop_iteration_id)
                if iteration is None:
                    raise ValueError(f"Loop iteration not found: {loop_iteration_id}")
                loop = session.get(LoopRunRecord, iteration.loop_run_id)
                if loop is None:
                    raise ValueError(f"Loop run not found: {iteration.loop_run_id}")
                _validate_loop_table_ref(
                    session,
                    loop=loop,
                    table_ref_id=table_ref_id,
                )
                session.add(record)
            return _loop_iteration_table_ref_from_record(record)
        except IntegrityError:
            return self.get_loop_iteration_table_ref(
                loop_iteration_id=loop_iteration_id,
                table_ref_id=table_ref_id,
                role=role_value,
            )

    def get_loop_iteration_table_ref(
        self,
        *,
        loop_iteration_id: str,
        table_ref_id: str,
        role: LoopIterationTableRefRole | str,
    ) -> LoopIterationTableRef | None:
        role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
        with self._session_factory() as session:
            record = session.get(
                LoopIterationTableRefRecord,
                {
                    "loop_iteration_id": loop_iteration_id,
                    "table_ref_id": table_ref_id,
                    "role": role_value,
                },
            )
            if record is None:
                return None
            return _loop_iteration_table_ref_from_record(record)

    def list_loop_iteration_table_refs(
        self,
        loop_iteration_id: str,
        *,
        role: LoopIterationTableRefRole | str | None = None,
    ) -> list[LoopIterationTableRef]:
        statement = (
            select(LoopIterationTableRefRecord)
            .where(LoopIterationTableRefRecord.loop_iteration_id == loop_iteration_id)
            .order_by(
                LoopIterationTableRefRecord.role,
                LoopIterationTableRefRecord.table_ref_id,
            )
        )
        if role is not None:
            role_value = (
                role.value if isinstance(role, LoopIterationTableRefRole) else role
            )
            statement = statement.where(LoopIterationTableRefRecord.role == role_value)
        with self._session_factory() as session:
            return [
                _loop_iteration_table_ref_from_record(record)
                for record in session.scalars(statement)
            ]
