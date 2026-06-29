from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, SharedPublication
from flowweaver.engine.shared_table_reader import (
    SharedTableReader,
    SharedTableVersionPolicy,
)
from flowweaver.nodes.permission_checks import (
    PermissionCheckError,
    ensure_task_permission_scope,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus, PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel

PUBLISH_SHARED_TABLES_NODE_TYPE = "PublishSharedTablesNode"
READ_SHARED_TABLES_NODE_TYPE = "ReadSharedTablesNode"


class BuiltinSharedTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        reader: SharedTableReader | None = None,
    ) -> None:
        self._store = store
        self._reader = reader or SharedTableReader(store)

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            if task.node_type == PUBLISH_SHARED_TABLES_NODE_TYPE:
                output_refs = self._execute_publish(task)
            elif task.node_type == READ_SHARED_TABLES_NODE_TYPE:
                output_refs = self._execute_read(task)
            else:
                raise _NodeValidationError(
                    f"Unsupported builtin shared table node type: {task.node_type}"
                )
        except (KeyError, ValueError, PermissionCheckError) as exc:
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.FAILED,
                error={
                    "error_code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "origin": ErrorOrigin.NODE.value,
                },
                started_at=started_at,
                finished_at=utc_now(),
            )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=output_refs,
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_publish(self, task: NodeTaskModel) -> list[str]:
        if not task.input_refs:
            raise _NodeValidationError(
                "PublishSharedTablesNode requires at least one input_ref"
            )
        share_name = _required_str_config(task.config, "share_name")
        export_names = _required_str_list_config(task.config, "export_names")
        if len(export_names) != len(task.input_refs):
            raise _NodeValidationError(
                "PublishSharedTablesNode config.export_names must match input_refs"
            )
        if len(set(export_names)) != len(export_names):
            raise _NodeValidationError(
                "PublishSharedTablesNode config.export_names must be unique"
            )
        ensure_task_permission_scope(
            store=self._store,
            task=task,
            action=PermissionAction.PUBLISH,
            resource_type="SHARED_PUBLICATION",
            resource_id=share_name,
        )
        retention_policy = _retention_policy(task.config)
        workflow = self._store.get_workflow_run(task.workflow_run_id)
        if workflow is None:
            raise _NodeValidationError(
                f"Workflow run not found: {task.workflow_run_id}"
            )
        publication = self._store.create_shared_publication(
            share_name=share_name,
            producer_workflow_id=workflow.workflow_id,
            producer_run_id=task.workflow_run_id,
            members=dict(zip(export_names, task.input_refs, strict=True)),
            retention_policy=retention_policy,
        )
        return [_shared_publication_ref(publication)]

    def _execute_read(self, task: NodeTaskModel) -> list[str]:
        if task.input_refs:
            raise _NodeValidationError("ReadSharedTablesNode does not accept inputs")
        share_name = _required_str_config(task.config, "share_name")
        version_policy = _required_str_config(task.config, "version_policy")
        exact_version = _optional_int_config(task.config, "exact_version")
        selected_members = _optional_str_list_config(task.config, "selected_members")
        result = self._reader.read(
            consumer_workflow_run_id=task.workflow_run_id,
            share_name=share_name,
            version_policy=SharedTableVersionPolicy(version_policy),
            exact_version=exact_version,
            selected_members=selected_members,
            lease_expires_at=utc_now() + timedelta(seconds=task.timeout_seconds),
        )
        return [table_ref.table_ref_id for table_ref in result.table_refs]


class _NodeValidationError(ValueError):
    pass


def _required_str_config(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise _NodeValidationError(f"config.{key} must be a non-empty string")
    return value


def _optional_str_list_config(
    config: dict[str, Any],
    key: str,
) -> tuple[str, ...] | None:
    value = config.get(key)
    if value is None:
        return None
    return _str_list_config_value(value, key)


def _required_str_list_config(
    config: dict[str, Any],
    key: str,
) -> tuple[str, ...]:
    value = config.get(key)
    if value is None:
        raise _NodeValidationError(f"config.{key} must be a list")
    return _str_list_config_value(value, key)


def _str_list_config_value(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _NodeValidationError(f"config.{key} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise _NodeValidationError(
                f"config.{key} must contain non-empty strings"
            )
        items.append(item)
    return tuple(items)


def _optional_int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
) -> int | None:
    value = config.get(key, default)
    if value is None:
        return None
    if not isinstance(value, int):
        raise _NodeValidationError(f"config.{key} must be an integer")
    return value


def _retention_policy(config: dict[str, Any]) -> dict[str, Any]:
    retention_seconds = _optional_int_config(config, "retention_seconds")
    if retention_seconds is None:
        return {}
    if retention_seconds <= 0:
        raise _NodeValidationError(
            "PublishSharedTablesNode config.retention_seconds must be positive"
        )
    return {"retention_seconds": retention_seconds}


def _shared_publication_ref(publication: SharedPublication) -> str:
    return (
        "shared-publication:"
        f"{publication.share_name}:"
        f"{publication.publication_version}:"
        f"{publication.publication_id}"
    )


def shared_table_node_types() -> tuple[str, str]:
    return (PUBLISH_SHARED_TABLES_NODE_TYPE, READ_SHARED_TABLES_NODE_TYPE)


def is_shared_table_node_type(
    node_type: str,
    node_types: Iterable[str] | None = None,
) -> bool:
    candidates = (
        tuple(node_types) if node_types is not None else shared_table_node_types()
    )
    return node_type in candidates
