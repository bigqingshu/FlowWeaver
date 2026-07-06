from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    get_table_provider_registry,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import TableProvider
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import LifecycleStatus
from flowweaver.protocols.table_ref import TableRefModel

DEFAULT_ROW_LIMIT = 50
MAX_ROW_LIMIT = 200

router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@dataclass(frozen=True)
class ReadableTableRefContext:
    table_ref: TableRefModel
    provider: TableProvider


@router.get("/{table_ref_id}", response_model=None)
def get_table_ref(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
):
    context, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider_registry=provider_registry,
    )
    if rejection is not None:
        return rejection
    assert context is not None
    return ok_response(request, context.table_ref)


@router.get("/{table_ref_id}/schema", response_model=None)
def get_table_ref_schema(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
):
    context, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider_registry=provider_registry,
    )
    if rejection is not None:
        return rejection
    assert context is not None
    table_ref = context.table_ref

    try:
        schema = context.provider.get_schema(table_ref)
    except ValueError as exc:
        return _rejected_data_read(request, exc)

    return ok_response(
        request,
        {
            "table_ref_id": table_ref.table_ref_id,
            "schema": [field.model_dump(mode="json") for field in schema],
            "schema_fingerprint": table_ref.schema_fingerprint,
        },
    )


@router.get("/{table_ref_id}/summary", response_model=None)
def get_table_ref_summary(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
):
    context, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider_registry=provider_registry,
    )
    if rejection is not None:
        return rejection
    assert context is not None
    table_ref = context.table_ref

    try:
        row_count = context.provider.count_rows(table_ref)
    except ValueError as exc:
        return _rejected_data_read(request, exc)

    return ok_response(request, _summary_payload(table_ref, row_count=row_count))


@router.get("/{table_ref_id}/rows", response_model=None)
def get_table_ref_rows(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_ROW_LIMIT)] = DEFAULT_ROW_LIMIT,
    columns: Annotated[list[str] | None, Query()] = None,
    order_by: Annotated[list[str] | None, Query()] = None,
):
    context, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider_registry=provider_registry,
    )
    if rejection is not None:
        return rejection
    assert context is not None
    table_ref = context.table_ref

    selected_columns = columns or [field.name for field in table_ref.schema]
    try:
        rows = context.provider.read_rows(
            table_ref,
            offset=offset,
            limit=limit,
            columns=columns,
            order_by=order_by,
        )
        row_count = context.provider.count_rows(table_ref)
    except ValueError as exc:
        return _rejected_data_read(request, exc)

    return ok_response(
        request,
        {
            "table_ref_id": table_ref.table_ref_id,
            "offset": offset,
            "limit": limit,
            "row_count": row_count,
            "columns": selected_columns,
            "rows": rows,
            "has_more": offset + len(rows) < row_count,
        },
    )


def _load_readable_table_ref(
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


def _summary_payload(table_ref: TableRefModel, *, row_count: int) -> dict[str, object]:
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


def _rejected_data_read(request: Request, exc: ValueError) -> JSONResponse:
    return error_response(
        request,
        error_code="DATA_READ_REJECTED",
        message=str(exc),
        status_code=400,
    )
