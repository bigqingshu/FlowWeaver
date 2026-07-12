from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    PluginCatalogEntryView,
    PluginCatalogStateView,
)
from flowweaver.api.dependencies import (
    check_origin,
    get_plugin_catalog,
    require_api_token,
)
from flowweaver.api.responses import ok_response
from flowweaver.plugin_runtime.catalog import PluginCatalog

router = APIRouter(
    prefix="/api/v1/plugins",
    tags=["plugins"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.get("", response_model=APIResponseModel)
def list_plugins(
    request: Request,
    catalog: Annotated[PluginCatalog, Depends(get_plugin_catalog)],
):
    entries = [
        PluginCatalogEntryView.model_validate(entry.to_public_data())
        for entry in catalog.list_entries()
    ]
    return ok_response(
        request,
        [entry.model_dump(mode="json") for entry in entries],
    )


@router.get("/state", response_model=APIResponseModel)
def get_plugin_catalog_state(
    request: Request,
    catalog: Annotated[PluginCatalog, Depends(get_plugin_catalog)],
):
    state = catalog.catalog_state()
    return ok_response(
        request,
        PluginCatalogStateView(
            catalog_hash=state.catalog_hash,
            plugin_count=state.plugin_count,
            enabled_count=state.enabled_count,
        ).model_dump(mode="json"),
    )
