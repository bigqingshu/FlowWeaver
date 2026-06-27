from __future__ import annotations

from fastapi import Request

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.supervisor import Supervisor


class APIAuthError(Exception):
    pass


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


def get_runtime_store(request: Request) -> RuntimeStore:
    return get_container(request).runtime_store


def get_node_registry(request: Request):
    return get_container(request).node_registry


def get_supervisor(request: Request) -> Supervisor:
    return get_container(request).supervisor


def require_api_token(request: Request) -> None:
    token = get_container(request).config.local_api_token
    if not token:
        raise APIAuthError()
    authorization = request.headers.get("authorization", "")
    if authorization != f"Bearer {token}":
        raise APIAuthError()


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = get_container(request).config.allowed_origins
    if origin not in allowed:
        raise APIAuthError()
