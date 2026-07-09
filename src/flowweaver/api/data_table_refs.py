from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from flowweaver.api.responses import error_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_protocol import TableProvider
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.table_ref import TableRefModel


@dataclass(frozen=True)
class ReadableTableRefContext:
    table_ref: TableRefModel
    provider: TableProvider


def load_readable_table_ref(
    request: Request,
    table_ref_id: str,
    *,
    store: RuntimeStore,
    provider_registry: TableProviderRegistry,
) -> tuple[ReadableTableRefContext, None] | tuple[None, JSONResponse]:
    table_ref = store.get_table_ref(table_ref_id)
    if table_ref is None:
        return None, error_response(
            request,
            error_code="TABLE_REF_NOT_FOUND",
            message="TableRef not found",
            status_code=404,
        )
    provider = provider_registry.get(table_ref.provider_id)
    if provider is None:
        return None, error_response(
            request,
            error_code="DATA_PROVIDER_UNSUPPORTED",
            message="TableRef provider is not supported by this EngineHost",
            status_code=400,
        )
    if not provider_registry.supports_storage_kind(
        table_ref.provider_id,
        table_ref.storage_kind,
    ):
        return None, error_response(
            request,
            error_code="DATA_STORAGE_UNSUPPORTED",
            message="TableRef storage kind is not supported by this EngineHost",
            status_code=400,
        )
    if "READ" not in table_ref.capabilities:
        return None, error_response(
            request,
            error_code="TABLE_REF_NOT_READABLE",
            message="TableRef does not declare READ capability",
            status_code=403,
        )
    if table_ref.lifecycle_status in {
        LifecycleStatus.RELEASED,
        LifecycleStatus.RETIRED,
        LifecycleStatus.ORPHANED,
    }:
        return None, error_response(
            request,
            error_code="TABLE_REF_NOT_AVAILABLE",
            message="TableRef is no longer available for reading",
            status_code=409,
        )
    return ReadableTableRefContext(table_ref=table_ref, provider=provider), None


def summary_payload(table_ref: TableRefModel, *, row_count: int) -> dict[str, object]:
    return {
        "table_ref_id": table_ref.table_ref_id,
        "workflow_run_id": table_ref.created_by_workflow_run_id,
        "node_run_id": table_ref.created_by_node_run_id,
        "logical_table_id": table_ref.logical_table_id,
        "storage_kind": table_ref.storage_kind.value,
        "lifecycle_status": table_ref.lifecycle_status.value,
        "version": table_ref.version,
        "schema_fingerprint": table_ref.schema_fingerprint,
        "capabilities": sorted(table_ref.capabilities),
        "row_count": row_count,
    }


def rejected_data_read(request: Request, exc: ValueError) -> JSONResponse:
    return error_response(
        request,
        error_code="DATA_READ_REJECTED",
        message=str(exc),
        status_code=400,
    )
