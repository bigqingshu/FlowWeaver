from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import LoopIterationTableRefRecord
from flowweaver.engine.runtime_loop_record_mappers import (
    _loop_iteration_table_ref_from_record,
)
from flowweaver.engine.runtime_models import LoopIterationTableRef
from flowweaver.protocols.enums import LoopIterationTableRefRole


def get_loop_iteration_table_ref_from_session(
    session: Session,
    *,
    loop_iteration_id: str,
    table_ref_id: str,
    role: LoopIterationTableRefRole | str,
) -> LoopIterationTableRef | None:
    role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
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


def list_loop_iteration_table_refs_from_session(
    session: Session,
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
        role_value = role.value if isinstance(role, LoopIterationTableRefRole) else role
        statement = statement.where(LoopIterationTableRefRecord.role == role_value)
    return [
        _loop_iteration_table_ref_from_record(record)
        for record in session.scalars(statement)
    ]
