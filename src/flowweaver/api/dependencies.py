from __future__ import annotations

from fastapi import Request

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationLifecycleService,
)
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_provider_registry import (
    TableProviderRegistry,
    create_default_table_provider_registry,
)
from flowweaver.engine.table_ref_release import TableRefReleaseService
from flowweaver.plugin_runtime.catalog import PluginCatalog


class APIAuthError(Exception):
    pass


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


def get_runtime_store(request: Request) -> RuntimeStore:
    return get_container(request).runtime_store


def get_runtime_table_provider(request: Request) -> SQLiteRuntimeTableProvider:
    return SQLiteRuntimeTableProvider(
        get_container(request).config.resolved_runtime_dir()
    )


def get_table_provider_registry(request: Request) -> TableProviderRegistry:
    container = get_container(request)
    if container.table_provider_registry is None:
        container.table_provider_registry = create_default_table_provider_registry(
            container.config.resolved_runtime_dir(),
            memory_table_limits=container.config.memory_table_limits(),
        )
    return container.table_provider_registry


def get_shared_publication_lifecycle_service(
    request: Request,
) -> SharedPublicationLifecycleService:
    container = get_container(request)
    if container.shared_publication_lifecycle_service is None:
        provider_registry = get_table_provider_registry(request)
        container.shared_publication_lifecycle_service = (
            SharedPublicationLifecycleService(
                container.runtime_store,
                table_ref_release_service=TableRefReleaseService(
                    store=container.runtime_store,
                    provider_registry=provider_registry,
                ),
            )
        )
    return container.shared_publication_lifecycle_service


def get_node_registry(request: Request):
    return get_container(request).node_registry


def get_plugin_catalog(request: Request) -> PluginCatalog:
    return get_container(request).plugin_catalog


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
