from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import error_response, ok_response
from flowweaver.api.run_pagination import paginated_ok_response, pagination_rejection
from flowweaver.api.runtime_shared_publication_responses import (
    shared_publication_catalog_entry_to_jsonable,
    shared_publication_member_to_jsonable,
    shared_publication_summary_to_jsonable,
)
from flowweaver.engine.runtime_store import RuntimeStore

router = APIRouter(
    prefix="/api/v1/shared-publications",
    tags=["shared-publications"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_shared_publications(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    share_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    return ok_response(
        request,
        store.list_shared_publications(share_name=share_name, limit=limit),
    )


@router.get("/catalog", response_model=APIResponseModel)
def list_shared_publication_catalog(
    request: Request,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    query: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    normalized_query = query.strip() if query and query.strip() else None
    entries = store.list_shared_publication_catalog(
        query=normalized_query,
        offset=offset,
        limit=limit,
    )
    return paginated_ok_response(
        request,
        items=[shared_publication_catalog_entry_to_jsonable(item) for item in entries],
        offset=offset,
        limit=limit,
        total=store.count_shared_publication_catalog(query=normalized_query),
        paged=True,
    )


@router.get("/{share_name}/versions", response_model=APIResponseModel)
def list_shared_publication_versions(
    request: Request,
    share_name: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    offset: int = 0,
    limit: int = 50,
    paged: bool = False,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    if not paged:
        return ok_response(
            request,
            store.list_shared_publications(share_name=share_name, limit=limit),
        )
    summaries = store.list_shared_publication_summaries(
        share_name=share_name,
        offset=offset,
        limit=limit,
    )
    return paginated_ok_response(
        request,
        items=[shared_publication_summary_to_jsonable(item) for item in summaries],
        offset=offset,
        limit=limit,
        total=store.count_shared_publication_versions(share_name=share_name),
        paged=True,
    )


@router.get("/{publication_id}/members", response_model=APIResponseModel)
def list_shared_publication_members(
    request: Request,
    publication_id: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    offset: int = 0,
    limit: int = 100,
):
    rejection = pagination_rejection(request, offset=offset, limit=limit)
    if rejection is not None:
        return rejection
    total = store.count_shared_publication_members(publication_id=publication_id)
    if total == 0 and not store.shared_publication_exists(publication_id):
        return error_response(
            request,
            error_code="SHARED_PUBLICATION_NOT_FOUND",
            message="Shared publication not found",
            status_code=404,
        )
    members = store.list_shared_publication_members(
        publication_id=publication_id,
        offset=offset,
        limit=limit,
    )
    return paginated_ok_response(
        request,
        items=[shared_publication_member_to_jsonable(item) for item in members],
        offset=offset,
        limit=limit,
        total=total,
        paged=True,
    )
