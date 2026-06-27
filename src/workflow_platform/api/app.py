from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from workflow_platform.api.responses import error_response
from workflow_platform.api.routes_runs import router as runs_router
from workflow_platform.api.routes_workflows import router as workflows_router
from workflow_platform.api.websocket_events import router as events_router
from workflow_platform.engine.runtime_store import RuntimeStore, sqlite_url

DEFAULT_DATABASE_PATH = Path("runtime/metadata/flowweaver.db")


def create_app(
    *,
    runtime_store: RuntimeStore | None = None,
    database_url: str | None = None,
    run_migrations: bool = True,
) -> FastAPI:
    app = FastAPI(title="FlowWeaver EngineHost", version="0.1.0")

    if runtime_store is None:
        url = database_url or sqlite_url(DEFAULT_DATABASE_PATH)
        if run_migrations:
            _upgrade_database(url)
        runtime_store = RuntimeStore(url)

    app.state.runtime_store = runtime_store

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
    app.include_router(events_router)
    return app


def _upgrade_database(database_url: str) -> None:
    database_path = _sqlite_path_from_url(database_url)
    if database_path is not None:
        database_path.parent.mkdir(parents=True, exist_ok=True)

    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _sqlite_path_from_url(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url.removeprefix(prefix))
