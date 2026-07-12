from __future__ import annotations

import shutil
import sqlite3
import time
from collections.abc import Iterator, Sequence
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from typing import Any

from flowweaver.engine.runtime_table_sql import (
    identifier_token,
    quote_identifier,
    sqlite_type,
)
from flowweaver.engine.table_provider_protocol import TableProvider
from flowweaver.plugin_runtime.errors import PluginRuntimeError
from flowweaver.plugin_runtime.manifest import PluginOutputTableSlotModel
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.plugin_runtime import (
    PluginInputTableRefModel,
    PluginOutputTableResultModel,
    PluginOutputTableTargetModel,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

PLUGIN_TABLE_BATCH_SIZE = 1000


class PluginTaskStaging:
    def __init__(self, *, runtime_root: Path, task: NodeTaskModel) -> None:
        staging_root = Path(runtime_root).resolve() / "_plugin_staging"
        self.task_dir = (
            staging_root
            / _safe_component(task.workflow_run_id)
            / _safe_component(task.task_id)
        )
        self._input_database_path = self.task_dir / "inputs.db"
        self._output_database_path = self.task_dir / "outputs.db"
        self._output_targets: dict[str, PluginOutputTableTargetModel] = {}

    def prepare(self) -> None:
        if self.task_dir.exists():
            self.cleanup()
        if self.task_dir.exists():
            raise PluginRuntimeError(
                "PLUGIN_STAGING_CLEANUP_FAILED",
                "Plugin task staging could not be reset",
            )
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def allocate_output_targets(
        self,
        slots: Sequence[PluginOutputTableSlotModel],
    ) -> list[PluginOutputTableTargetModel]:
        if not slots:
            return []
        self.prepare_if_needed()
        with closing(sqlite3.connect(self._output_database_path)):
            pass
        targets: list[PluginOutputTableTargetModel] = []
        for index, slot in enumerate(slots):
            table_name = f"out_{index}_{identifier_token(slot.name)}"
            target = PluginOutputTableTargetModel(
                slot_name=slot.name,
                database_path=str(self._output_database_path),
                table_name=table_name,
            )
            self._output_targets[slot.name] = target
            targets.append(target)
        return targets

    def materialize_input(
        self,
        *,
        slot_name: str,
        table_ref: TableRefModel,
        schema: Sequence[FieldSchemaModel],
        provider: TableProvider,
    ) -> PluginInputTableRefModel:
        self.prepare_if_needed()
        table_name = f"in_{identifier_token(slot_name)}"
        with closing(sqlite3.connect(self._input_database_path)) as connection:
            connection.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")
            connection.execute(
                f"CREATE TABLE {quote_identifier(table_name)} "
                f"({_columns_sql(schema)})"
            )
            offset = 0
            while True:
                rows = provider.read_rows(
                    table_ref,
                    offset,
                    PLUGIN_TABLE_BATCH_SIZE,
                )
                if not rows:
                    break
                _insert_rows(connection, table_name, schema, rows)
                offset += len(rows)
                if len(rows) < PLUGIN_TABLE_BATCH_SIZE:
                    break
            connection.commit()
        return PluginInputTableRefModel(
            slot_name=slot_name,
            table_ref_id=table_ref.table_ref_id,
            database_uri=sqlite_read_only_uri(self._input_database_path),
            table_name=table_name,
            schema=list(schema),
            materialized=True,
        )

    def target_for_slot(self, slot_name: str) -> PluginOutputTableTargetModel:
        target = self._output_targets.get(slot_name)
        if target is None:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SLOT_UNDECLARED",
                f"Plugin returned undeclared output slot: {slot_name}",
            )
        return target

    def validate_output(
        self,
        output: PluginOutputTableResultModel,
        target: PluginOutputTableTargetModel,
    ) -> None:
        output_path = Path(output.database_path)
        try:
            resolved_output_path = output_path.resolve(strict=True)
            resolved_target_path = Path(target.database_path).resolve(strict=True)
            resolved_task_dir = self.task_dir.resolve(strict=True)
        except OSError as exc:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_MISSING",
                f"Plugin output database is not available: {output.slot_name}",
            ) from exc
        if (
            resolved_output_path != resolved_target_path
            or not resolved_output_path.is_relative_to(resolved_task_dir)
            or not resolved_output_path.is_file()
        ):
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_PATH_OUTSIDE_STAGING",
                f"Plugin output path is outside task staging: {output.slot_name}",
            )
        if output.table_name != target.table_name:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_TARGET_MISMATCH",
                f"Plugin output table does not match its target: {output.slot_name}",
            )
        _validate_schema(output.schema, slot_name=output.slot_name)
        with closing(
            sqlite3.connect(
                sqlite_read_only_uri(resolved_output_path),
                uri=True,
            )
        ) as connection:
            columns = connection.execute(
                f"PRAGMA table_info({quote_identifier(output.table_name)})"
            ).fetchall()
        if not columns:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_TABLE_MISSING",
                f"Plugin output table does not exist: {output.slot_name}",
            )
        actual_names = [str(column[1]) for column in columns]
        expected_fields = sorted(output.schema, key=lambda field: field.ordinal)
        expected_names = [field.name for field in expected_fields]
        if actual_names != expected_names:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SCHEMA_MISMATCH",
                f"Plugin output columns do not match schema: {output.slot_name}",
            )
        actual_types = [sqlite_type(str(column[2])) for column in columns]
        expected_types = [sqlite_type(field.data_type) for field in expected_fields]
        if actual_types != expected_types:
            raise PluginRuntimeError(
                "PLUGIN_OUTPUT_SCHEMA_MISMATCH",
                f"Plugin output column types do not match schema: {output.slot_name}",
            )

    def output_row_batches(
        self,
        output: PluginOutputTableResultModel,
    ) -> Iterator[list[dict[str, Any]]]:
        fields = sorted(output.schema, key=lambda field: field.ordinal)
        columns_sql = ", ".join(quote_identifier(field.name) for field in fields)
        connection = sqlite3.connect(
            sqlite_read_only_uri(Path(output.database_path)),
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.execute(
                f"SELECT {columns_sql} FROM {quote_identifier(output.table_name)}"
            )
            while True:
                rows = cursor.fetchmany(PLUGIN_TABLE_BATCH_SIZE)
                if not rows:
                    return
                yield [dict(row) for row in rows]
        finally:
            connection.close()

    def cleanup(self) -> None:
        for attempt in range(5):
            if not self.task_dir.exists():
                break
            try:
                shutil.rmtree(self.task_dir)
                break
            except OSError:
                if attempt == 4:
                    return
                time.sleep(0.02)
        for directory in (self.task_dir.parent, self.task_dir.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                pass

    def prepare_if_needed(self) -> None:
        if not self.task_dir.exists():
            self.task_dir.mkdir(parents=True, exist_ok=True)


def sqlite_read_only_uri(database_path: Path) -> str:
    return f"{database_path.resolve(strict=True).as_uri()}?mode=ro"


def _safe_component(value: str) -> str:
    token = identifier_token(value)[:48]
    digest = sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{token}-{digest}"


def _columns_sql(schema: Sequence[FieldSchemaModel]) -> str:
    _validate_schema(schema, slot_name="input")
    return ", ".join(
        f"{quote_identifier(field.name)} {sqlite_type(field.data_type)}"
        for field in sorted(schema, key=lambda field: field.ordinal)
    )


def _insert_rows(
    connection: sqlite3.Connection,
    table_name: str,
    schema: Sequence[FieldSchemaModel],
    rows: Sequence[dict[str, Any]],
) -> None:
    fields = sorted(schema, key=lambda field: field.ordinal)
    field_names = [field.name for field in fields]
    placeholders = ", ".join("?" for _ in fields)
    columns_sql = ", ".join(quote_identifier(name) for name in field_names)
    connection.executemany(
        f"INSERT INTO {quote_identifier(table_name)} "
        f"({columns_sql}) VALUES ({placeholders})",
        [[row.get(name) for name in field_names] for row in rows],
    )


def _validate_schema(
    schema: Sequence[FieldSchemaModel],
    *,
    slot_name: str,
) -> None:
    if not schema:
        raise PluginRuntimeError(
            "PLUGIN_OUTPUT_SCHEMA_INVALID",
            f"Plugin table schema is empty: {slot_name}",
        )
    fields = sorted(schema, key=lambda field: field.ordinal)
    ordinals = [field.ordinal for field in fields]
    names = [field.name for field in fields]
    field_ids = [field.field_id for field in fields]
    if ordinals != list(range(len(fields))):
        raise PluginRuntimeError(
            "PLUGIN_OUTPUT_SCHEMA_INVALID",
            f"Plugin table schema ordinals are invalid: {slot_name}",
        )
    if len(names) != len(set(names)) or any(not name.strip() for name in names):
        raise PluginRuntimeError(
            "PLUGIN_OUTPUT_SCHEMA_INVALID",
            f"Plugin table schema field names are invalid: {slot_name}",
        )
    if len(field_ids) != len(set(field_ids)) or any(
        not field_id.strip() for field_id in field_ids
    ):
        raise PluginRuntimeError(
            "PLUGIN_OUTPUT_SCHEMA_INVALID",
            f"Plugin table schema field ids are invalid: {slot_name}",
        )
