from __future__ import annotations

from fastapi import APIRouter, Depends

from flowweaver.api.dependencies import check_origin, require_api_token
from flowweaver.api.routes_workflow_definitions import (
    include_workflow_definition_routes,
)
from flowweaver.api.routes_workflow_revisions import (
    router as workflow_revisions_router,
)
from flowweaver.api.routes_workflow_runs import router as workflow_runs_router

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows"],
    dependencies=[Depends(require_api_token), Depends(check_origin)],
)
router.include_router(workflow_revisions_router)
router.include_router(workflow_runs_router)
include_workflow_definition_routes(router)
