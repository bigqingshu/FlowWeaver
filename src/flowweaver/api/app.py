from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from flowweaver.api.dependencies import APIAuthError
from flowweaver.api.responses import error_response
from flowweaver.api.routes_events import router as rest_events_router
from flowweaver.api.routes_runs import router as runs_router
from flowweaver.api.routes_workflows import router as workflows_router
from flowweaver.api.websocket_events import router as events_router
from flowweaver.engine.bootstrap import bootstrap_default
from flowweaver.engine.service_container import ServiceContainer


def create_app(container: ServiceContainer) -> FastAPI:
    app = FastAPI(title="FlowWeaver EngineHost", version="0.1.0")
    app.state.container = container

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        return error_response(
            request,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(APIAuthError)
    async def api_auth_exception_handler(request: Request, _exc: APIAuthError):
        return error_response(
            request,
            error_code="UNAUTHORIZED",
            message="Invalid local API token",
            status_code=401,
        )

    @app.get("/api/v1/health")
    def health(request: Request):
        return {
            "ok": True,
            "data": {"status": "ok"},
            "error": None,
            "request_id": request.headers.get("x-request-id") or "health",
        }

    app.include_router(workflows_router)
    app.include_router(runs_router)
    app.include_router(rest_events_router)
    app.include_router(events_router)
    return app


def create_default_app() -> FastAPI:
    return create_app(bootstrap_default())
