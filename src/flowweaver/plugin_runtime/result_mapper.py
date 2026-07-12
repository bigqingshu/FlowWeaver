from __future__ import annotations

from dataclasses import dataclass

from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.plugin_runtime.errors import PluginRuntimeError
from flowweaver.plugin_runtime.manifest import (
    PluginManifestModel,
    PluginOutputTableSlotModel,
)
from flowweaver.plugin_runtime.staging import PluginTaskStaging
from flowweaver.protocols.enums import NodeResultStatus, TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.plugin_runtime import PluginOutputTableResultModel
from flowweaver.protocols.table_ref import TableRefModel


@dataclass(frozen=True)
class _PreparedOutput:
    slot: PluginOutputTableSlotModel
    output: PluginOutputTableResultModel


class PluginResultMapper:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        runtime_provider: SQLiteRuntimeTableProvider,
        data_registry: RuntimeDataRegistry,
    ) -> None:
        self._store = store
        self._runtime_provider = runtime_provider
        self._data_registry = data_registry

    def map_result(
        self,
        *,
        task: NodeTaskModel,
        manifest: PluginManifestModel,
        staging: PluginTaskStaging,
        result: NodeTaskResultModel,
    ) -> NodeTaskResultModel:
        if result.status != NodeResultStatus.SUCCEEDED:
            return result.model_copy(
                update={
                    "output_refs": [],
                    "output_slot_bindings": {},
                    "plugin_runtime": None,
                }
            )
        if result.output_refs or result.output_slot_bindings:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_REFS_FORBIDDEN",
                "Plugin process cannot publish FlowWeaver output references",
            )
        prepared = self._prepare_outputs(
            manifest=manifest,
            staging=staging,
            result=result,
        )
        if not prepared:
            return result.model_copy(update={"plugin_runtime": None})

        published_refs: list[TableRefModel] = []
        try:
            self._data_registry.cleanup_staging_for_node(
                workflow_run_id=task.workflow_run_id,
                node_run_id=task.node_run_id,
            )
            staging_refs = [
                self._copy_to_runtime_staging(
                    task=task,
                    staging=staging,
                    prepared_output=prepared_output,
                )
                for prepared_output in prepared
            ]
            for staging_ref in staging_refs:
                published_ref = self._publish_staging(staging_ref)
                published_refs.append(published_ref)
            self._data_registry.cleanup_staging_for_node(
                workflow_run_id=task.workflow_run_id,
                node_run_id=task.node_run_id,
            )
        except Exception:
            self._rollback_published(published_refs)
            self._data_registry.cleanup_staging_for_node(
                workflow_run_id=task.workflow_run_id,
                node_run_id=task.node_run_id,
            )
            raise

        output_refs = [table_ref.table_ref_id for table_ref in published_refs]
        output_slot_bindings = {
            prepared_output.slot.name: table_ref.table_ref_id
            for prepared_output, table_ref in zip(
                prepared,
                published_refs,
                strict=True,
            )
        }
        return result.model_copy(
            update={
                "output_refs": output_refs,
                "output_slot_bindings": output_slot_bindings,
                "plugin_runtime": None,
            }
        )

    def _prepare_outputs(
        self,
        *,
        manifest: PluginManifestModel,
        staging: PluginTaskStaging,
        result: NodeTaskResultModel,
    ) -> list[_PreparedOutput]:
        runtime_result = result.plugin_runtime
        outputs = runtime_result.outputs if runtime_result is not None else []
        output_names = [output.slot_name for output in outputs]
        duplicates = sorted(
            name for name in set(output_names) if output_names.count(name) > 1
        )
        if duplicates:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SLOT_DUPLICATE",
                "Plugin returned duplicate output slots: " + ", ".join(duplicates),
            )
        declared_slots = {
            slot.name: slot for slot in manifest.output_table_slots
        }
        unknown_slots = sorted(set(output_names) - set(declared_slots))
        if unknown_slots:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SLOT_UNDECLARED",
                "Plugin returned undeclared output slots: "
                + ", ".join(unknown_slots),
            )
        required_slots = {
            port.name
            for port in manifest.output_ports
            if port.required and port.name in declared_slots
        }
        missing_slots = sorted(required_slots - set(output_names))
        if missing_slots:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SLOT_MISSING",
                "Plugin required output slots are missing: "
                + ", ".join(missing_slots),
            )
        prepared: list[_PreparedOutput] = []
        outputs_by_name = {output.slot_name: output for output in outputs}
        for slot in manifest.output_table_slots:
            output = outputs_by_name.get(slot.name)
            if output is None:
                continue
            target = staging.target_for_slot(slot.name)
            staging.validate_output(output, target)
            prepared.append(_PreparedOutput(slot=slot, output=output))
        return prepared

    def _copy_to_runtime_staging(
        self,
        *,
        task: NodeTaskModel,
        staging: PluginTaskStaging,
        prepared_output: _PreparedOutput,
    ) -> TableRefModel:
        output = prepared_output.output
        latest_ref = self._store.get_latest_table_ref_by_logical_identity(
            workflow_run_id=task.workflow_run_id,
            storage_kind=TableStorageKind.RUNTIME_SQL,
            role=prepared_output.slot.default_role,
            logical_table_id=prepared_output.slot.name,
        )
        staging_ref = self._runtime_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=prepared_output.slot.name,
            schema=output.schema,
            role=prepared_output.slot.default_role,
            version=latest_ref.version if latest_ref is not None else 1,
        )
        self._runtime_provider.drop_table(staging_ref)
        self._runtime_provider.create_table(staging_ref)
        self._data_registry.register_staging(staging_ref)
        for rows in staging.output_row_batches(output):
            self._runtime_provider.insert_rows(staging_ref, rows)
        return staging_ref

    def _publish_staging(self, staging_ref: TableRefModel) -> TableRefModel:
        published_ref = self._runtime_provider.published_ref_from_staging(
            staging_ref
        )
        self._runtime_provider.publish_staging(staging_ref, published_ref)
        try:
            self._store.register_table_ref(published_ref)
        except Exception:
            self._runtime_provider.drop_table(published_ref)
            raise
        return published_ref

    def _rollback_published(self, published_refs: list[TableRefModel]) -> None:
        for table_ref in reversed(published_refs):
            try:
                self._runtime_provider.drop_table(table_ref)
            except Exception:
                pass
            try:
                self._store.mark_table_ref_released(table_ref.table_ref_id)
            except Exception:
                pass
