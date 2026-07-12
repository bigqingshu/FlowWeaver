from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.node_executor.ipc_client_messages import ipc_failure_result
from flowweaver.node_executor.ipc_client_subprocess import (
    SubprocessNodeExecutorIpcClient,
)
from flowweaver.node_executor.ipc_client_types import NodeTaskIpcEventHandler
from flowweaver.plugin_runtime.catalog import PluginCatalog
from flowweaver.plugin_runtime.data_refs import PluginDataRefResolver
from flowweaver.plugin_runtime.errors import PluginRuntimeError
from flowweaver.plugin_runtime.manifest import PluginManifestModel
from flowweaver.plugin_runtime.process_command import (
    plugin_process_command,
    plugin_process_environment,
)
from flowweaver.plugin_runtime.result_mapper import PluginResultMapper
from flowweaver.plugin_runtime.staging import PluginTaskStaging
from flowweaver.protocols.enums import NodeResultStatus
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.plugin_runtime import PluginTaskRuntimeModel
from flowweaver.protocols.runtime_feedback import (
    ResolvedRuntimeFeedbackPolicyModel,
)

PluginClientFactory = Callable[..., SubprocessNodeExecutorIpcClient]


class PluginExternalProcessExecutor:
    executor_id = "plugin-external-process-executor"

    def __init__(
        self,
        *,
        plugin_catalog: PluginCatalog,
        python_executable: str | None = None,
        startup_timeout_seconds: float = 5.0,
        client_factory: PluginClientFactory = SubprocessNodeExecutorIpcClient,
        store: RuntimeStore | None = None,
        runtime_dir: Path | None = None,
        table_provider_registry: TableProviderRegistry | None = None,
    ) -> None:
        self._plugin_catalog = plugin_catalog
        self._python_executable = python_executable or sys.executable
        self._startup_timeout_seconds = startup_timeout_seconds
        self._client_factory = client_factory
        self._runtime_dir = Path(runtime_dir) if runtime_dir is not None else None
        self._data_ref_resolver: PluginDataRefResolver | None = None
        self._result_mapper: PluginResultMapper | None = None
        if store is not None and self._runtime_dir is not None:
            runtime_provider = SQLiteRuntimeTableProvider(self._runtime_dir)
            provider_registry = table_provider_registry or (
                create_default_table_provider_registry(
                    self._runtime_dir,
                    runtime_provider=runtime_provider,
                )
            )
            self._data_ref_resolver = PluginDataRefResolver(
                store=store,
                provider_registry=provider_registry,
            )
            self._result_mapper = PluginResultMapper(
                store=store,
                runtime_provider=runtime_provider,
                data_registry=RuntimeDataRegistry(
                    store=store,
                    table_provider=runtime_provider,
                ),
            )
        self._event_handler: NodeTaskIpcEventHandler | None = None
        self._active_clients: dict[str, SubprocessNodeExecutorIpcClient] = {}
        self._closed = False
        self._lock = Lock()

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def set_event_handler(self, handler: NodeTaskIpcEventHandler | None) -> None:
        with self._lock:
            self._event_handler = handler
            clients = tuple(self._active_clients.values())
        for client in clients:
            client.set_event_handler(handler)

    def execute(self, task: NodeTaskModel) -> NodeTaskResultModel:
        descriptor = self._plugin_catalog.descriptor_for_node(
            task.node_type,
            task.node_version,
        )
        if descriptor is None:
            return self._failure_result(
                task,
                error_code="PLUGIN_NOT_AVAILABLE",
                message=(
                    "Plugin is not available for node: "
                    f"{task.node_type}@{task.node_version}"
                ),
            )
        if task.config.get("enable_execute") is not True:
            return self._failure_result(
                task,
                error_code="PLUGIN_EXECUTION_DISABLED",
                message="Plugin execution is disabled by node config",
            )
        if (
            descriptor.manifest.external_actions
            and task.config.get("allow_external_actions") is not True
        ):
            return self._failure_result(
                task,
                error_code="PLUGIN_EXTERNAL_ACTIONS_BLOCKED",
                message="Plugin declares external actions but they are not allowed",
            )

        staging: PluginTaskStaging | None = None
        try:
            plugin_runtime = PluginTaskRuntimeModel()
            if (
                descriptor.manifest.input_table_slots
                or descriptor.manifest.output_table_slots
            ):
                if (
                    self._runtime_dir is None
                    or self._data_ref_resolver is None
                    or self._result_mapper is None
                ):
                    raise PluginRuntimeError(
                        "PLUGIN_DATA_RUNTIME_UNAVAILABLE",
                        "Plugin table runtime is not configured",
                    )
                staging = PluginTaskStaging(
                    runtime_root=self._runtime_dir,
                    task=task,
                )
                plugin_runtime = self._data_ref_resolver.prepare_runtime(
                    task=task,
                    manifest=descriptor.manifest,
                    staging=staging,
                )
        except PluginRuntimeError as exc:
            if staging is not None:
                staging.cleanup()
            return self._failure_result(
                task,
                error_code=exc.error_code,
                message=str(exc),
            )
        except Exception as exc:
            if staging is not None:
                staging.cleanup()
            return self._failure_result(
                task,
                error_code="PLUGIN_INPUT_PREPARATION_FAILED",
                message=str(exc),
                error_type=type(exc).__name__,
            )

        child_executor_id = f"plugin-{task.task_id}"
        try:
            client = self._client_factory(
                executor_id=child_executor_id,
                command=plugin_process_command(
                    descriptor.entrypoint_path,
                    executor_id=child_executor_id,
                    python_executable=self._python_executable,
                ),
                cwd=descriptor.package_dir,
                env=plugin_process_environment(),
                event_handler=self._event_handler,
                inject_src_pythonpath=False,
                startup_timeout_seconds=min(
                    self._startup_timeout_seconds,
                    float(task.timeout_seconds),
                ),
            )
        except Exception as exc:
            if staging is not None:
                staging.cleanup()
            return self._failure_result(
                task,
                error_code="PLUGIN_START_FAILED",
                message=str(exc),
                error_type=type(exc).__name__,
            )

        with self._lock:
            if self._closed:
                client.close()
                if staging is not None:
                    staging.cleanup()
                return self._failure_result(
                    task,
                    error_code="PLUGIN_EXECUTOR_CLOSED",
                    message="Plugin executor is closed",
                )
            self._active_clients[task.task_id] = client
        plugin_task = task.model_copy(
            update={
                "config": self._business_config(task, descriptor.manifest),
                "plugin_runtime": plugin_runtime,
            }
        )
        try:
            result = client.execute(plugin_task)
            result = self._validate_result(task, result)
            if staging is None:
                return self._map_no_table_result(task, result)
            if result.status == NodeResultStatus.FAILED and result.error and (
                result.error.get("error_code")
                == "PLUGIN_RESULT_IDENTITY_MISMATCH"
            ):
                return result
            try:
                assert self._result_mapper is not None
                return self._result_mapper.map_result(
                    task=task,
                    manifest=descriptor.manifest,
                    staging=staging,
                    result=result,
                )
            except PluginRuntimeError as exc:
                return self._failure_result(
                    task,
                    error_code=exc.error_code,
                    message=str(exc),
                )
            except Exception as exc:
                return self._failure_result(
                    task,
                    error_code="PLUGIN_OUTPUT_PUBLISH_FAILED",
                    message=str(exc),
                    error_type=type(exc).__name__,
                )
        finally:
            with self._lock:
                self._active_clients.pop(task.task_id, None)
            client.close()
            if staging is not None:
                staging.cleanup()

    def request_cancel(
        self,
        task: NodeTaskModel,
        *,
        reason: str = "WORKFLOW_CANCEL_REQUESTED",
    ) -> bool:
        client = self._client_for_task(task.task_id)
        return client is not None and client.request_cancel(task, reason=reason)

    def request_runtime_options_update(
        self,
        task: NodeTaskModel,
        *,
        runtime_options_version: int,
        runtime_feedback_policy: ResolvedRuntimeFeedbackPolicyModel,
    ) -> bool:
        client = self._client_for_task(task.task_id)
        return client is not None and client.request_runtime_options_update(
            task,
            runtime_options_version=runtime_options_version,
            runtime_feedback_policy=runtime_feedback_policy,
        )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            clients = tuple(self._active_clients.values())
            self._active_clients.clear()
        for client in clients:
            client.close()

    def _client_for_task(
        self,
        task_id: str,
    ) -> SubprocessNodeExecutorIpcClient | None:
        with self._lock:
            return self._active_clients.get(task_id)

    def _validate_result(
        self,
        task: NodeTaskModel,
        result: NodeTaskResultModel,
    ) -> NodeTaskResultModel:
        mismatches: list[str] = []
        for field_name in (
            "task_id",
            "node_run_id",
            "attempt",
            "process_generation",
        ):
            if getattr(result, field_name) != getattr(task, field_name):
                mismatches.append(field_name)
        if mismatches:
            return self._failure_result(
                task,
                error_code="PLUGIN_RESULT_IDENTITY_MISMATCH",
                message=("Plugin result identity mismatch: " + ", ".join(mismatches)),
            )
        return result.model_copy(update={"executor_id": self.executor_id})

    @staticmethod
    def _business_config(
        task: NodeTaskModel,
        manifest: PluginManifestModel,
    ) -> dict[str, Any]:
        allowed_fields = manifest.config_schema.properties
        return {
            key: task.config[key]
            for key in allowed_fields
            if key in task.config
        }

    def _map_no_table_result(
        self,
        task: NodeTaskModel,
        result: NodeTaskResultModel,
    ) -> NodeTaskResultModel:
        plugin_outputs = (
            result.plugin_runtime.outputs
            if result.plugin_runtime is not None
            else []
        )
        if result.status == NodeResultStatus.SUCCEEDED and (
            result.output_refs
            or result.output_slot_bindings
            or plugin_outputs
        ):
            return self._failure_result(
                task,
                error_code="PLUGIN_OUTPUT_SLOT_UNDECLARED",
                message="Plugin returned table outputs not declared by manifest",
            )
        return result.model_copy(
            update={
                "output_refs": (
                    result.output_refs
                    if result.status == NodeResultStatus.SUCCEEDED
                    else []
                ),
                "output_slot_bindings": (
                    result.output_slot_bindings
                    if result.status == NodeResultStatus.SUCCEEDED
                    else {}
                ),
                "plugin_runtime": None,
            }
        )

    def _failure_result(
        self,
        task: NodeTaskModel,
        *,
        error_code: str,
        message: str,
        error_type: str | None = None,
    ) -> NodeTaskResultModel:
        error: dict[str, Any] = {
            "error_code": error_code,
            "message": message,
        }
        if error_type is not None:
            error["error_type"] = error_type
        return ipc_failure_result(
            task,
            executor_id=self.executor_id,
            error=error,
        )
