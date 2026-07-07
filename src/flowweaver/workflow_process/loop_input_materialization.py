from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from flowweaver.engine.runtime_store import LoopIterationTableRef, RuntimeStore
from flowweaver.engine.runtime_table_provider import (
    SQLITE_RUNTIME_PROVIDER_ID,
    SQLiteRuntimeTableProvider,
)
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import LoopIterationTableRefRole
from flowweaver.protocols.table_ref import TableRefModel


class LoopInputMaterializationStatus(str, Enum):
    MATERIALIZED = "MATERIALIZED"
    ALREADY_MATERIALIZED = "ALREADY_MATERIALIZED"
    LOOP_ITERATION_NOT_FOUND = "LOOP_ITERATION_NOT_FOUND"
    LOOP_RUN_NOT_FOUND = "LOOP_RUN_NOT_FOUND"
    SOURCE_TABLE_NOT_FOUND = "SOURCE_TABLE_NOT_FOUND"
    SOURCE_TABLE_RUN_MISMATCH = "SOURCE_TABLE_RUN_MISMATCH"
    SOURCE_PROVIDER_NOT_FOUND = "SOURCE_PROVIDER_NOT_FOUND"
    OUTPUT_PROVIDER_NOT_AVAILABLE = "OUTPUT_PROVIDER_NOT_AVAILABLE"
    MATERIALIZER_NODE_RUN_NOT_FOUND = "MATERIALIZER_NODE_RUN_NOT_FOUND"
    MATERIALIZER_NODE_RUN_MISMATCH = "MATERIALIZER_NODE_RUN_MISMATCH"
    INVALID_SELECTOR = "INVALID_SELECTOR"
    SOURCE_ROW_NOT_FOUND = "SOURCE_ROW_NOT_FOUND"


@dataclass(frozen=True)
class LoopInputMaterializationResult:
    status: LoopInputMaterializationStatus
    table_ref: TableRefModel | None = None
    detail: str | None = None


def materialize_loop_iteration_input(
    store: RuntimeStore,
    registry: TableProviderRegistry,
    *,
    loop_iteration_id: str,
    source_table_ref_id: str | None = None,
    input_selector: Mapping[str, Any] | None = None,
    materializer_node_run_id: str | None = None,
    output_name: str | None = None,
) -> LoopInputMaterializationResult:
    iteration = store.get_loop_iteration_run(loop_iteration_id)
    if iteration is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.LOOP_ITERATION_NOT_FOUND,
            detail=loop_iteration_id,
        )
    loop = store.get_loop_run(iteration.loop_run_id)
    if loop is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.LOOP_RUN_NOT_FOUND,
            detail=iteration.loop_run_id,
        )
    resolved_source_table_ref_id = source_table_ref_id or iteration.input_table_ref_id
    if resolved_source_table_ref_id is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.SOURCE_TABLE_NOT_FOUND,
            detail="source_table_ref_id is required",
        )
    selector = (
        input_selector if input_selector is not None else iteration.input_selector
    )
    row_index = _row_index_from_selector(selector)
    if row_index is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.INVALID_SELECTOR,
            detail="input_selector.row_index must be a non-negative integer",
        )

    existing = _find_existing_materialized_input(
        store,
        loop_iteration_id=loop_iteration_id,
        source_table_ref_id=resolved_source_table_ref_id,
        row_index=row_index,
    )
    if existing is not None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.ALREADY_MATERIALIZED,
            table_ref=existing,
        )

    source_ref = store.get_table_ref(resolved_source_table_ref_id)
    if source_ref is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.SOURCE_TABLE_NOT_FOUND,
            detail=resolved_source_table_ref_id,
        )
    if source_ref.created_by_workflow_run_id != loop.workflow_run_id:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.SOURCE_TABLE_RUN_MISMATCH,
            detail=resolved_source_table_ref_id,
        )
    creator_node_run_id = materializer_node_run_id or source_ref.created_by_node_run_id
    creator = store.get_node_run(creator_node_run_id)
    if creator is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.MATERIALIZER_NODE_RUN_NOT_FOUND,
            detail=creator_node_run_id,
        )
    if creator.workflow_run_id != loop.workflow_run_id:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.MATERIALIZER_NODE_RUN_MISMATCH,
            detail=creator_node_run_id,
        )

    source_provider = registry.get(source_ref.provider_id)
    if source_provider is None:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.SOURCE_PROVIDER_NOT_FOUND,
            detail=source_ref.provider_id,
        )
    output_provider = registry.get(SQLITE_RUNTIME_PROVIDER_ID)
    if not isinstance(output_provider, SQLiteRuntimeTableProvider):
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.OUTPUT_PROVIDER_NOT_AVAILABLE,
            detail=SQLITE_RUNTIME_PROVIDER_ID,
        )

    rows = source_provider.read_rows(source_ref, offset=row_index, limit=1)
    if not rows:
        return LoopInputMaterializationResult(
            LoopInputMaterializationStatus.SOURCE_ROW_NOT_FOUND,
            detail=str(row_index),
        )

    staging_ref = output_provider.create_staging_table(
        workflow_run_id=loop.workflow_run_id,
        node_run_id=creator_node_run_id,
        output_name=output_name or f"loop_input_{loop_iteration_id}",
        schema=source_ref.schema,
    )
    output_provider.insert_rows(staging_ref, rows)
    published_ref = output_provider.published_ref_from_staging(staging_ref)
    published_ref = published_ref.model_copy(
        update={
            "opaque_handle": {
                **published_ref.opaque_handle,
                "materialized_from": {
                    "source_table_ref_id": resolved_source_table_ref_id,
                    "row_index": row_index,
                },
            },
        }
    )
    output_provider.publish_staging(staging_ref, published_ref)
    store.register_table_ref(published_ref)
    store.add_loop_iteration_table_ref(
        loop_iteration_id=loop_iteration_id,
        table_ref_id=published_ref.table_ref_id,
        role=LoopIterationTableRefRole.INPUT,
    )
    return LoopInputMaterializationResult(
        LoopInputMaterializationStatus.MATERIALIZED,
        table_ref=published_ref,
    )


def _row_index_from_selector(selector: Mapping[str, Any] | None) -> int | None:
    if selector is None:
        return None
    row_index = selector.get("row_index")
    if not isinstance(row_index, int) or isinstance(row_index, bool) or row_index < 0:
        return None
    return row_index


def _find_existing_materialized_input(
    store: RuntimeStore,
    *,
    loop_iteration_id: str,
    source_table_ref_id: str,
    row_index: int,
) -> TableRefModel | None:
    for link in store.list_loop_iteration_table_refs(
        loop_iteration_id,
        role=LoopIterationTableRefRole.INPUT,
    ):
        table_ref = _table_ref_for_link(store, link)
        if table_ref is None:
            continue
        materialized_from = table_ref.opaque_handle.get("materialized_from")
        if materialized_from == {
            "source_table_ref_id": source_table_ref_id,
            "row_index": row_index,
        }:
            return table_ref
    return None


def _table_ref_for_link(
    store: RuntimeStore,
    link: LoopIterationTableRef,
) -> TableRefModel | None:
    return store.get_table_ref(link.table_ref_id)
