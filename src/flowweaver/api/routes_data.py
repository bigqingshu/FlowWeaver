from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.data_table_refs import (
    load_readable_table_ref,
    rejected_data_read,
    summary_payload,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    get_table_provider_registry,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry

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
    provider_registry: Annotated[
        TableProviderRegistry,
        Depends(get_table_provider_registry),
    ],
):
    context, rejection = load_readable_table_ref(
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
    context, rejection = load_readable_table_ref(
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
        return rejected_data_read(request, exc)

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
    context, rejection = load_readable_table_ref(
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
        return rejected_data_read(request, exc)

    return ok_response(request, summary_payload(table_ref, row_count=row_count))


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
    context, rejection = load_readable_table_ref(
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
        return rejected_data_read(request, exc)

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
