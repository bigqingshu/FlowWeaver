from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    get_runtime_table_provider,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import TableRefModel

DEFAULT_ROW_LIMIT = 50
MAX_ROW_LIMIT = 200

router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("/{table_ref_id}", response_model=None)
def get_table_ref(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider: Annotated[
        SQLiteRuntimeTableProvider,
        Depends(get_runtime_table_provider),
    ],
):
    table_ref, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider=provider,
    )
    if rejection is not None:
        return rejection
    return ok_response(request, table_ref)


@router.get("/{table_ref_id}/schema", response_model=None)
def get_table_ref_schema(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider: Annotated[
        SQLiteRuntimeTableProvider,
        Depends(get_runtime_table_provider),
    ],
):
    table_ref, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider=provider,
    )
    if rejection is not None:
        return rejection

    try:
        schema = provider.get_schema(table_ref)
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
    provider: Annotated[
        SQLiteRuntimeTableProvider,
        Depends(get_runtime_table_provider),
    ],
):
    table_ref, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider=provider,
    )
    if rejection is not None:
        return rejection

    try:
        row_count = provider.count_rows(table_ref)
    except ValueError as exc:
        return _rejected_data_read(request, exc)

    return ok_response(request, _summary_payload(table_ref, row_count=row_count))


@router.get("/{table_ref_id}/rows", response_model=None)
def get_table_ref_rows(
    request: Request,
    table_ref_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    provider: Annotated[
        SQLiteRuntimeTableProvider,
        Depends(get_runtime_table_provider),
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_ROW_LIMIT)] = DEFAULT_ROW_LIMIT,
    columns: Annotated[list[str] | None, Query()] = None,
    order_by: Annotated[list[str] | None, Query()] = None,
):
    table_ref, rejection = _load_readable_table_ref(
        request,
        table_ref_id,
        store=store,
        provider=provider,
    )
    if rejection is not None:
        return rejection

    selected_columns = columns or [field.name for field in table_ref.schema]
    try:
        rows = provider.read_rows(
            table_ref,
            offset=offset,
            limit=limit,
            columns=columns,
            order_by=order_by,
        )
        row_count = provider.count_rows(table_ref)
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
    provider: SQLiteRuntimeTableProvider,
) -> tuple[TableRefModel, None] | tuple[None, JSONResponse]:
    table_ref = store.get_table_ref(table_ref_id)
    if table_ref is None:
        return None, error_response(
            request,
            error_code="TABLE_REF_NOT_FOUND",
            message="TableRef not found",
            status_code=404,
        )
    if table_ref.provider_id != provider.provider_id:
        return None, error_response(
            request,
            error_code="DATA_PROVIDER_UNSUPPORTED",
            message="TableRef provider is not supported by this EngineHost",
            status_code=400,
        )
    if table_ref.storage_kind != TableStorageKind.RUNTIME_SQL:
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
    return table_ref, None


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
