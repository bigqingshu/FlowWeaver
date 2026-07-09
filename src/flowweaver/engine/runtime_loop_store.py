from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from flowweaver.engine.runtime_loop_iteration_node_run_store import (
    RuntimeLoopIterationNodeRunStoreMixin,
)


class RuntimeLoopStoreMixin(RuntimeLoopIterationNodeRunStoreMixin):
    _session_factory: sessionmaker[Session]


