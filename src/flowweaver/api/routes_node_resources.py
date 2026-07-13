from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request

from flowweaver.api.api_models import (
    APIResponseModel,
    SqliteTableCatalogRequest,
    SqliteTableCatalogView,
)
from flowweaver.api.dependencies import check_origin, require_api_token
from flowweaver.api.responses import error_response, ok_response
from flowweaver.nodes.builtin_sql_schema import list_sqlite_table_names

router = APIRouter(
    prefix="/api/v1/node-resources",
    tags=["node-resources"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)


@router.post("/sqlite/tables", response_model=APIResponseModel)
def list_sqlite_tables(
    request: Request,
    payload: SqliteTableCatalogRequest,
):
    try:
        tables = list_sqlite_table_names(Path(payload.database_path))
    except (OSError, ValueError) as exc:
        return error_response(
            request,
            error_code="SQLITE_TABLE_CATALOG_UNAVAILABLE",
            message=str(exc),
            status_code=400,
        )
    return ok_response(
        request,
        SqliteTableCatalogView(tables=tables).model_dump(mode="json"),
    )
