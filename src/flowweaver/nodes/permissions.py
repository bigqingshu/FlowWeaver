from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.builtin_table import (
    FILTER_ROWS_NODE_TYPE,
    GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.protocols.enums import PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.permissions import (
    PermissionRequestModel,
    PermissionScopeModel,
)


def resolve_builtin_node_permissions(task: NodeTaskModel) -> PermissionRequestModel:
    if task.node_type == GENERATE_TEST_TABLE_NODE_TYPE:
        scopes = _generate_test_table_permissions(task)
    elif task.node_type == FILTER_ROWS_NODE_TYPE:
        scopes = _filter_rows_permissions(task)
    elif task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE:
        scopes = _publish_shared_tables_permissions(task)
    elif task.node_type == READ_SHARED_TABLES_NODE_TYPE:
        scopes = _read_shared_tables_permissions(task)
    else:
        raise ValueError(f"Unsupported builtin node type: {task.node_type}")
    return PermissionRequestModel(
        workflow_run_id=task.workflow_run_id,
        node_run_id=task.node_run_id,
        node_instance_id=task.node_instance_id,
        node_type=task.node_type,
        scopes=scopes,
        reason=f"Resolved permissions for {task.node_type}",
    )


def _generate_test_table_permissions(
    task: NodeTaskModel,
) -> list[PermissionScopeModel]:
    if task.input_refs:
        raise ValueError("GenerateTestTableNode does not accept inputs")
    return [
        PermissionScopeModel(
            action=PermissionAction.PUBLISH,
            resource_type="NODE_OUTPUT",
            resource_id=_node_output_resource_id(task),
            constraints={
                "columns": task.config.get("columns"),
                "rows": task.config.get("rows"),
            },
        )
    ]


def _filter_rows_permissions(task: NodeTaskModel) -> list[PermissionScopeModel]:
    if len(task.input_refs) != 1:
        raise ValueError("FilterRowsNode requires exactly one input_ref")
    field = task.config.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError("FilterRowsNode config.field is required")
    input_ref = task.input_refs[0]
    return [
        PermissionScopeModel(
            action=PermissionAction.READ_TABLE,
            resource_type="TABLE_REF",
            resource_id=input_ref,
        ),
        PermissionScopeModel(
            action=PermissionAction.READ_FIELDS,
            resource_type="TABLE_REF",
            resource_id=input_ref,
            fields=[field],
            constraints={
                "operator": task.config.get("operator"),
                "value": task.config.get("value"),
            },
        ),
        PermissionScopeModel(
            action=PermissionAction.PUBLISH,
            resource_type="NODE_OUTPUT",
            resource_id=_node_output_resource_id(task),
        ),
    ]


def _publish_shared_tables_permissions(
    task: NodeTaskModel,
) -> list[PermissionScopeModel]:
    if not task.input_refs:
        raise ValueError("PublishSharedTablesNode requires at least one input_ref")
    share_name = _required_string_config(task.config, "share_name")
    export_names = _required_string_list_config(task.config, "export_names")
    if len(export_names) != len(task.input_refs):
        raise ValueError(
            "PublishSharedTablesNode config.export_names must match input_refs"
        )
    scopes = [
        PermissionScopeModel(
            action=PermissionAction.READ_TABLE,
            resource_type="TABLE_REF",
            resource_id=input_ref,
            constraints={"export_name": export_name},
        )
        for export_name, input_ref in zip(export_names, task.input_refs, strict=True)
    ]
    scopes.append(
        PermissionScopeModel(
            action=PermissionAction.PUBLISH,
            resource_type="SHARED_PUBLICATION",
            resource_id=share_name,
            constraints={
                "export_names": list(export_names),
                "input_refs": list(task.input_refs),
            },
        )
    )
    return scopes


def _read_shared_tables_permissions(task: NodeTaskModel) -> list[PermissionScopeModel]:
    if task.input_refs:
        raise ValueError("ReadSharedTablesNode does not accept inputs")
    share_name = _required_string_config(task.config, "share_name")
    version_policy = _required_string_config(task.config, "version_policy")
    return [
        PermissionScopeModel(
            action=PermissionAction.READ_SHARED,
            resource_type="SHARED_PUBLICATION",
            resource_id=share_name,
            constraints={
                "version_policy": version_policy,
                "exact_version": task.config.get("exact_version"),
                "selected_members": _optional_string_list(
                    task.config.get("selected_members"),
                    key="selected_members",
                ),
            },
        )
    ]


def _node_output_resource_id(task: NodeTaskModel) -> str:
    return f"{task.workflow_run_id}:{task.node_instance_id}:output"


def _required_string_config(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    return value


def _required_string_list_config(
    config: dict[str, Any],
    key: str,
) -> tuple[str, ...]:
    value = config.get(key)
    if value is None:
        raise ValueError(f"config.{key} must be a list")
    return _string_list_value(value, key)


def _optional_string_list(value: Any, *, key: str) -> list[str] | None:
    if value is None:
        return None
    return list(_string_list_value(value, key))


def _string_list_value(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"config.{key} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"config.{key} must contain non-empty strings")
        items.append(item)
    return tuple(items)
