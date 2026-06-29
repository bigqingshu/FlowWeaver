from __future__ import annotations

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.enums import PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel


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
        raise PermissionCheckError("Node task is missing permission_handle_id")
    grant = store.get_permission_grant(handle_id)
    if grant is None:
        raise PermissionCheckError(f"Permission grant not found: {handle_id}")
    if grant.workflow_run_id != task.workflow_run_id:
        raise PermissionCheckError("Permission grant workflow_run_id mismatch")
    if grant.node_run_id != task.node_run_id:
        raise PermissionCheckError("Permission grant node_run_id mismatch")
    if not grant.granted:
        raise PermissionCheckError("Permission grant was denied")
    if grant.revoked_at is not None:
        raise PermissionCheckError("Permission grant was revoked")
    if grant.expires_at is not None and grant.expires_at <= utc_now():
        raise PermissionCheckError("Permission grant expired")
    if not any(
        scope.action == action
        and scope.resource_type == resource_type
        and scope.resource_id == resource_id
        for scope in grant.scopes
    ):
        raise PermissionCheckError(
            "Permission grant does not cover required scope: "
            f"{action.value} {resource_type} {resource_id}"
        )
