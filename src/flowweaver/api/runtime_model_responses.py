from __future__ import annotations

from typing import Any

from flowweaver.api.runtime_event_responses import (
    runtime_event_log_to_jsonable as _runtime_event_log_to_jsonable,
)
from flowweaver.api.runtime_loop_responses import (
    loop_iteration_run_to_jsonable as _loop_iteration_run_to_jsonable,
)
from flowweaver.api.runtime_loop_responses import (
    loop_iteration_table_ref_to_jsonable as _loop_iteration_table_ref_to_jsonable,
)
from flowweaver.api.runtime_loop_responses import (
    loop_run_to_jsonable as _loop_run_to_jsonable,
)
from flowweaver.api.runtime_shared_publication_responses import (
    shared_publication_to_jsonable as _shared_publication_to_jsonable,
)
from flowweaver.api.runtime_workflow_responses import (
    node_run_to_jsonable as _node_run_to_jsonable,
)
from flowweaver.api.runtime_workflow_responses import (
    workflow_definition_to_jsonable as _workflow_definition_to_jsonable,
)
from flowweaver.api.runtime_workflow_responses import (
    workflow_process_to_jsonable as _workflow_process_to_jsonable,
)
from flowweaver.api.runtime_workflow_responses import (
    workflow_revision_to_jsonable as _workflow_revision_to_jsonable,
)
from flowweaver.api.runtime_workflow_responses import (
    workflow_run_to_jsonable as _workflow_run_to_jsonable,
)
from flowweaver.engine.runtime_models import (
    LoopIterationRun,
    LoopIterationTableRef,
    LoopRun,
    NodeRun,
    RuntimeEventLog,
    SharedPublication,
    WorkflowDefinition,
    WorkflowProcess,
    WorkflowRevision,
    WorkflowRun,
)


def runtime_model_to_jsonable(value: Any) -> dict[str, Any] | None:
    if isinstance(value, WorkflowDefinition):
        return _workflow_definition_to_jsonable(value)
    if isinstance(value, WorkflowRevision):
        return _workflow_revision_to_jsonable(value)
    if isinstance(value, WorkflowRun):
        return _workflow_run_to_jsonable(value)
    if isinstance(value, WorkflowProcess):
        return _workflow_process_to_jsonable(value)
    if isinstance(value, NodeRun):
        return _node_run_to_jsonable(value)
    if isinstance(value, LoopRun):
        return _loop_run_to_jsonable(value)
    if isinstance(value, LoopIterationRun):
        return _loop_iteration_run_to_jsonable(value)
    if isinstance(value, LoopIterationTableRef):
        return _loop_iteration_table_ref_to_jsonable(value)
    if isinstance(value, RuntimeEventLog):
        return _runtime_event_log_to_jsonable(value)
    if isinstance(value, SharedPublication):
        return _shared_publication_to_jsonable(value)
    return None
