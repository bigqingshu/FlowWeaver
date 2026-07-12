from __future__ import annotations

from pathlib import Path

from flowweaver.engine.external_sql_table_provider import EXTERNAL_SQL_PROVIDER_ID
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLITE_RUNTIME_PROVIDER_ID
from flowweaver.engine.runtime_table_sql import table_location
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.plugin_runtime.errors import PluginRuntimeError
from flowweaver.plugin_runtime.manifest import PluginManifestModel
from flowweaver.plugin_runtime.staging import (
    PluginTaskStaging,
    sqlite_read_only_uri,
)
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.plugin_runtime import (
    PluginInputTableRefModel,
    PluginTaskRuntimeModel,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_READABLE_LIFECYCLE_STATUSES = {
    LifecycleStatus.ACTIVE,
    LifecycleStatus.PUBLISHED,
}


class PluginDataRefResolver:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        provider_registry: TableProviderRegistry,
    ) -> None:
        self._store = store
        self._provider_registry = provider_registry

    def prepare_runtime(
        self,
        *,
        task: NodeTaskModel,
        manifest: PluginManifestModel,
        staging: PluginTaskStaging,
    ) -> PluginTaskRuntimeModel:
        staging.prepare()
        inputs = self._prepare_inputs(
            task=task,
            manifest=manifest,
            staging=staging,
        )
        output_targets = staging.allocate_output_targets(
            manifest.output_table_slots
        )
        return PluginTaskRuntimeModel(
            inputs=inputs,
            output_targets=output_targets,
        )

    def _prepare_inputs(
        self,
        *,
        task: NodeTaskModel,
        manifest: PluginManifestModel,
        staging: PluginTaskStaging,
    ) -> list[PluginInputTableRefModel]:
        slots = {slot.name: slot for slot in manifest.input_table_slots}
        unknown_slots = sorted(set(task.input_slot_bindings) - set(slots))
        if unknown_slots:
            raise PluginRuntimeError(
                "PLUGIN_INPUT_SLOT_UNDECLARED",
                "Plugin input bindings contain undeclared slots: "
                + ", ".join(unknown_slots),
            )
        missing_slots = sorted(
            slot.name
            for slot in manifest.input_table_slots
            if slot.required and slot.name not in task.input_slot_bindings
        )
        if missing_slots:
            raise PluginRuntimeError(
                "PLUGIN_INPUT_SLOT_MISSING",
                "Plugin required input slots are missing: "
                + ", ".join(missing_slots),
            )
        bound_ref_ids = set(task.input_slot_bindings.values())
        if not bound_ref_ids.issubset(set(task.input_refs)):
            raise PluginRuntimeError(
                "PLUGIN_INPUT_BINDING_INVALID",
                "Plugin input slot bindings must reference task input_refs",
            )
        if set(task.input_refs) - bound_ref_ids:
            raise PluginRuntimeError(
                "PLUGIN_INPUT_BINDING_INVALID",
                "Plugin task contains input_refs without slot bindings",
            )

        prepared: list[PluginInputTableRefModel] = []
        for slot in manifest.input_table_slots:
            table_ref_id = task.input_slot_bindings.get(slot.name)
            if table_ref_id is None:
                continue
            table_ref = self._store.get_table_ref(table_ref_id)
            if table_ref is None:
                raise PluginRuntimeError(
                    "PLUGIN_INPUT_REF_NOT_FOUND",
                    f"Plugin input table_ref does not exist: {slot.name}",
                )
            if (
                "READ" not in table_ref.capabilities
                or table_ref.lifecycle_status not in _READABLE_LIFECYCLE_STATUSES
            ):
                raise PluginRuntimeError(
                    "PLUGIN_INPUT_REF_UNREADABLE",
                    f"Plugin input table_ref is not readable: {slot.name}",
                )
            if table_ref.storage_kind not in slot.allowed_storage_kinds:
                raise PluginRuntimeError(
                    "PLUGIN_INPUT_STORAGE_UNSUPPORTED",
                    f"Plugin input storage kind is not allowed: {slot.name}",
                )
            provider = self._provider_registry.get(table_ref.provider_id)
            if provider is None:
                raise PluginRuntimeError(
                    "PLUGIN_INPUT_PROVIDER_UNAVAILABLE",
                    f"Plugin input provider is not available: {slot.name}",
                )
            try:
                schema = provider.get_schema(table_ref)
                provider.read_rows(table_ref, 0, 1)
            except Exception as exc:
                raise PluginRuntimeError(
                    "PLUGIN_INPUT_REF_UNREADABLE",
                    f"Plugin input table_ref cannot be read: {slot.name}",
                ) from exc
            direct = _direct_sqlite_input(
                slot_name=slot.name,
                table_ref=table_ref,
                schema=schema,
            )
            if direct is not None:
                prepared.append(direct)
                continue
            prepared.append(
                staging.materialize_input(
                    slot_name=slot.name,
                    table_ref=table_ref,
                    schema=schema,
                    provider=provider,
                )
            )
        return prepared


def _direct_sqlite_input(
    *,
    slot_name: str,
    table_ref: TableRefModel,
    schema: list[FieldSchemaModel],
) -> PluginInputTableRefModel | None:
    if table_ref.provider_id == SQLITE_RUNTIME_PROVIDER_ID:
        database_path, table_name = table_location(table_ref)
    elif table_ref.provider_id == EXTERNAL_SQL_PROVIDER_ID:
        database_path_value = table_ref.opaque_handle.get("database_path")
        table_name_value = table_ref.opaque_handle.get("table_name")
        if (
            not isinstance(database_path_value, str)
            or not isinstance(table_name_value, str)
            or not database_path_value
            or not table_name_value
            or table_ref.opaque_handle.get("query") is not None
        ):
            return None
        database_path = Path(database_path_value)
        table_name = table_name_value
    else:
        return None
    try:
        database_uri = sqlite_read_only_uri(database_path)
    except OSError as exc:
        raise PluginRuntimeError(
            "PLUGIN_INPUT_REF_UNREADABLE",
            f"Plugin input database does not exist: {slot_name}",
        ) from exc
    return PluginInputTableRefModel(
        slot_name=slot_name,
        table_ref_id=table_ref.table_ref_id,
        database_uri=database_uri,
        table_name=table_name,
        schema=list(schema),
        materialized=False,
    )
