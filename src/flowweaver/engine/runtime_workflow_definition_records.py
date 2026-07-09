from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    WorkflowDefinitionRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _definition_hash,
    _json_dumps,
)


@dataclass(frozen=True)
class InitialWorkflowDefinitionRecords:
    workflow: WorkflowRecord
    revision: WorkflowRevisionRecord
    legacy: WorkflowDefinitionRecord


def initial_workflow_definition_records(
    *,
    name: str,
    definition: dict[str, Any],
    workflow_id: str | None,
    created_by: str | None,
) -> InitialWorkflowDefinitionRecords:
    now = utc_now()
    resolved_workflow_id = workflow_id or new_id()
    revision_id = new_id()
    definition_json = _json_dumps(definition)
    definition_hash = _definition_hash(definition_json)
    created_at = _datetime_to_text(now)
    workflow = WorkflowRecord(
        workflow_id=resolved_workflow_id,
        name=name,
        current_revision_id=revision_id,
        status="ACTIVE",
        created_at=created_at,
        updated_at=created_at,
    )
    revision = WorkflowRevisionRecord(
        revision_id=revision_id,
        workflow_id=resolved_workflow_id,
        version=1,
        definition_json=definition_json,
        definition_hash=definition_hash,
        created_at=created_at,
        created_by=created_by,
    )
    legacy = WorkflowDefinitionRecord(
        workflow_id=resolved_workflow_id,
        name=name,
        version=1,
        definition_json=definition_json,
        created_at=created_at,
        updated_at=created_at,
    )
    return InitialWorkflowDefinitionRecords(
        workflow=workflow,
        revision=revision,
        legacy=legacy,
    )


def next_workflow_revision_record(
    *,
    workflow_id: str,
    version: int,
    definition: dict[str, Any],
    created_by: str | None,
) -> WorkflowRevisionRecord:
    definition_json = _json_dumps(definition)
    return WorkflowRevisionRecord(
        revision_id=new_id(),
        workflow_id=workflow_id,
        version=version,
        definition_json=definition_json,
        definition_hash=_definition_hash(definition_json),
        created_at=_datetime_to_text(utc_now()),
        created_by=created_by,
    )


def sync_legacy_workflow_definition_record(
    legacy: WorkflowDefinitionRecord,
    *,
    workflow: WorkflowRecord,
    revision: WorkflowRevisionRecord,
) -> None:
    legacy.name = workflow.name
    legacy.version = revision.version
    legacy.definition_json = revision.definition_json
    legacy.updated_at = workflow.updated_at
