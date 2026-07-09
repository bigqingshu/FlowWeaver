from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import WorkflowRecord, WorkflowRevisionRecord
from flowweaver.engine.runtime_models import WorkflowDefinition, WorkflowRevision
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_definition_from_records,
    _workflow_revision_from_record,
)


def get_workflow_definition_from_session(
    session: Session,
    workflow_id: str,
) -> WorkflowDefinition | None:
    workflow = session.get(WorkflowRecord, workflow_id)
    if workflow is None or workflow.status == "DELETED":
        return None
    revision = session.get(WorkflowRevisionRecord, workflow.current_revision_id)
    if revision is None:
        return None
    return _workflow_definition_from_records(workflow, revision)


def list_workflow_definitions_from_session(
    session: Session,
) -> list[WorkflowDefinition]:
    workflows = session.scalars(
        select(WorkflowRecord)
        .where(WorkflowRecord.status != "DELETED")
        .order_by(WorkflowRecord.created_at)
    ).all()
    revisions = {
        revision.revision_id: revision
        for revision in session.scalars(
            select(WorkflowRevisionRecord).where(
                WorkflowRevisionRecord.revision_id.in_(
                    [
                        workflow.current_revision_id
                        for workflow in workflows
                        if workflow.current_revision_id
                    ]
                )
            )
        )
    }
    return [
        _workflow_definition_from_records(
            workflow,
            revisions[workflow.current_revision_id],
        )
        for workflow in workflows
        if workflow.current_revision_id in revisions
    ]


def list_workflow_revisions_from_session(
    session: Session,
    workflow_id: str,
) -> list[WorkflowRevision]:
    records = session.scalars(
        select(WorkflowRevisionRecord)
        .where(WorkflowRevisionRecord.workflow_id == workflow_id)
        .order_by(WorkflowRevisionRecord.version)
    ).all()
    return [_workflow_revision_from_record(record) for record in records]


def get_workflow_revision_from_session(
    session: Session,
    revision_id: str,
) -> WorkflowRevision | None:
    record = session.get(WorkflowRevisionRecord, revision_id)
    if record is None:
        return None
    return _workflow_revision_from_record(record)
