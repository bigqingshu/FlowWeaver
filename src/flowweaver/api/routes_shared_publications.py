from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from flowweaver.api.api_models import APIResponseModel
from flowweaver.api.dependencies import (
    check_origin,
    get_runtime_store,
    require_api_token,
)
from flowweaver.api.responses import ok_response
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


@router.get("/{share_name}/versions", response_model=APIResponseModel)
def list_shared_publication_versions(
    request: Request,
    share_name: str,
    store: Annotated[RuntimeStore, Depends(get_runtime_store)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    return ok_response(
        request,
        store.list_shared_publications(share_name=share_name, limit=limit),
    )
