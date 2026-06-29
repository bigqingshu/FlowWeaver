from __future__ import annotations

from typing import NoReturn

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import AuditLevel, PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.permissions import (
    AuditEventModel,
    PermissionGrantModel,
    PermissionScopeModel,
)


class PermissionCheckError(ValueError):
    pass


def ensure_task_permission_scope(
    *,
    store: RuntimeStore,
    task: NodeTaskModel,
    action: PermissionAction,
    resource_type: str,
    resource_id: str,
) -> None:
    handle_id = task.permission_handle_id
    if not handle_id:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=None,
            reason="Node task is missing permission_handle_id",
        )
    grant = store.get_permission_grant(handle_id)
    if grant is None:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason=f"Permission grant not found: {handle_id}",
        )
    if grant.workflow_run_id != task.workflow_run_id:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason="Permission grant workflow_run_id mismatch",
            grant=grant,
        )
    if grant.node_run_id != task.node_run_id:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason="Permission grant node_run_id mismatch",
            grant=grant,
        )
    if not grant.granted:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason="Permission grant was denied",
            grant=grant,
        )
    if grant.revoked_at is not None:
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason="Permission grant was revoked",
            grant=grant,
        )
    if grant.expires_at is not None and grant.expires_at <= utc_now():
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason="Permission grant expired",
            grant=grant,
        )
    matched_scope = next(
        (
            scope
            for scope in grant.scopes
            if scope.action == action
            and scope.resource_type == resource_type
            and scope.resource_id == resource_id
        ),
        None,
    )
    if matched_scope is None:
        reason = (
            "Permission grant does not cover required scope: "
            f"{action.value} {resource_type} {resource_id}"
        )
        _deny_permission_check(
            store=store,
            task=task,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_handle_id=handle_id,
            reason=reason,
            grant=grant,
        )
    _append_permission_check_audit_event(
        store=store,
        task=task,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result="granted",
        permission_handle_id=handle_id,
        grant=grant,
        matched_scope=matched_scope,
    )


def _deny_permission_check(
    *,
    store: RuntimeStore,
    task: NodeTaskModel,
    action: PermissionAction,
    resource_type: str,
    resource_id: str,
    permission_handle_id: str | None,
    reason: str,
    grant: PermissionGrantModel | None = None,
) -> NoReturn:
    _append_permission_check_audit_event(
        store=store,
        task=task,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result="denied",
        permission_handle_id=permission_handle_id,
        grant=grant,
        reason=reason,
    )
    raise PermissionCheckError(reason)


def _append_permission_check_audit_event(
    *,
    store: RuntimeStore,
    task: NodeTaskModel,
    action: PermissionAction,
    resource_type: str,
    resource_id: str,
    result: str,
    permission_handle_id: str | None,
    grant: PermissionGrantModel | None = None,
    matched_scope: PermissionScopeModel | None = None,
    reason: str | None = None,
) -> None:
    store.append_audit_event(
        AuditEventModel(
            event_type="PERMISSION_CHECK",
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            subject_type="NODE",
            subject_id=task.node_run_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            audit_level=(
                grant.audit_level if grant is not None else AuditLevel.STANDARD
            ),
            summary=_permission_check_summary(
                task=task,
                permission_handle_id=permission_handle_id,
                matched_scope=matched_scope,
                reason=reason,
            ),
        )
    )


def _permission_check_summary(
    *,
    task: NodeTaskModel,
    permission_handle_id: str | None,
    matched_scope: PermissionScopeModel | None,
    reason: str | None,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "permission_handle_id": permission_handle_id,
        "node_instance_id": task.node_instance_id,
        "node_type": task.node_type,
        "task_id": task.task_id,
        "attempt": task.attempt,
    }
    if reason is not None:
        summary["reason"] = reason
    if matched_scope is not None:
        if matched_scope.fields is not None:
            summary["fields"] = matched_scope.fields
        if matched_scope.write_mode is not None:
            summary["write_mode"] = matched_scope.write_mode
        if matched_scope.constraints:
            summary["constraints"] = matched_scope.constraints
    return summary
