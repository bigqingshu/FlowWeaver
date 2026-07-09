from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    WorkflowDefinitionRecord,
    WorkflowRecord,
    WorkflowRevisionRecord,
)
from flowweaver.engine.runtime_models import (
    WorkflowDefinition,
    WorkflowRevision,
    WorkflowRevisionConflict,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
)
from flowweaver.engine.runtime_workflow_definition_records import (
    initial_workflow_definition_records as _initial_workflow_definition_records,
)
from flowweaver.engine.runtime_workflow_definition_records import (
    next_workflow_revision_record as _next_workflow_revision_record,
)
from flowweaver.engine.runtime_workflow_definition_records import (
    sync_legacy_workflow_definition_record as _sync_legacy_workflow_definition_record,
)
from flowweaver.engine.runtime_workflow_record_mappers import (
    _workflow_definition_from_records,
    _workflow_revision_from_record,
)


class RuntimeWorkflowDefinitionStoreMixin:
    _session_factory: sessionmaker[Session]

    def create_workflow_definition(
        self,
        *,
        name: str,
        definition: dict[str, Any],
        workflow_id: str | None = None,
        created_by: str | None = None,
    ) -> WorkflowDefinition:
        records = _initial_workflow_definition_records(
            name=name,
            definition=definition,
            workflow_id=workflow_id,
            created_by=created_by,
        )
        with self._session_factory.begin() as session:
            session.add_all([records.workflow, records.revision, records.legacy])
        return _workflow_definition_from_records(records.workflow, records.revision)

    def get_workflow_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._session_factory() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return None
            revision = session.get(WorkflowRevisionRecord, workflow.current_revision_id)
            if revision is None:
                return None
            return _workflow_definition_from_records(workflow, revision)

    def list_workflow_definitions(self) -> list[WorkflowDefinition]:
        with self._session_factory() as session:
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

    def update_workflow_definition(
        self,
        workflow_id: str,
        *,
        name: str | None = None,
        definition: dict[str, Any] | None = None,
        base_revision_id: str | None = None,
        created_by: str | None = None,
    ) -> WorkflowDefinition | WorkflowRevisionConflict | None:
        updated: WorkflowDefinition | WorkflowRevisionConflict | None = None
        with self._session_factory.begin() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return None
            if (
                base_revision_id is not None
                and workflow.current_revision_id != base_revision_id
            ):
                return WorkflowRevisionConflict(
                    workflow_id=workflow_id,
                    expected_revision_id=base_revision_id,
                    current_revision_id=workflow.current_revision_id,
                )
            if name is not None:
                workflow.name = name
            current_revision = session.get(
                WorkflowRevisionRecord,
                workflow.current_revision_id,
            )
            if current_revision is None:
                return None
            if definition is not None:
                revision = _next_workflow_revision_record(
                    workflow_id=workflow_id,
                    version=current_revision.version + 1,
                    definition=definition,
                    created_by=created_by,
                )
                session.add(revision)
                workflow.current_revision_id = revision.revision_id
                current_revision = revision
            workflow.updated_at = _datetime_to_text(utc_now())
            legacy = session.get(WorkflowDefinitionRecord, workflow_id)
            if legacy is not None:
                _sync_legacy_workflow_definition_record(
                    legacy,
                    workflow=workflow,
                    revision=current_revision,
                )
            updated = _workflow_definition_from_records(workflow, current_revision)
        return updated

    def delete_workflow_definition(self, workflow_id: str) -> bool:
        with self._session_factory.begin() as session:
            workflow = session.get(WorkflowRecord, workflow_id)
            if workflow is None or workflow.status == "DELETED":
                return False
            workflow.status = "DELETED"
            workflow.updated_at = _datetime_to_text(utc_now())
        return True

    def list_workflow_revisions(self, workflow_id: str) -> list[WorkflowRevision]:
        with self._session_factory() as session:
            records = session.scalars(
                select(WorkflowRevisionRecord)
                .where(WorkflowRevisionRecord.workflow_id == workflow_id)
                .order_by(WorkflowRevisionRecord.version)
            ).all()
            return [_workflow_revision_from_record(record) for record in records]

    def get_workflow_revision(self, revision_id: str) -> WorkflowRevision | None:
        with self._session_factory() as session:
            record = session.get(WorkflowRevisionRecord, revision_id)
            if record is None:
                return None
            return _workflow_revision_from_record(record)
