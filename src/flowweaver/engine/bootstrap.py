from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.config import (
    EngineConfig,
    WorkflowProcessExecutionMode,
    resolve_workflow_process_execution_mode,
    resolve_workflow_process_max_concurrent_node_tasks,
)
from flowweaver.common.ids import new_id
from flowweaver.common.instance_lock import InstanceLock
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.shared_publication_cleanup_worker import (
    SharedPublicationCleanupWorker,
)
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationLifecycleService,
)
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.engine.table_provider_registry import (
    create_default_table_provider_registry,
)
from flowweaver.engine.table_ref_release import TableRefReleaseService
from flowweaver.nodes.default_registry import (
    create_default_node_registry,
    default_node_definitions,
)
from flowweaver.plugin_runtime.discovery import discover_plugins


class EngineHostBootstrap:
    def __init__(self, config: EngineConfig) -> None:
        self.config = _resolve_config_paths(config)

    def initialize(self) -> ServiceContainer:
        self._ensure_directories()
        lock: InstanceLock | None = None
        if self.config.enforce_single_instance:
            lock = InstanceLock(self.config.data_dir / "enginehost.lock")
            lock.acquire()

        token = self.config.local_api_token or self._load_or_create_token()
        config = self.config.model_copy(update={"local_api_token": token})
        database_url = f"sqlite:///{config.resolved_metadata_db_path().as_posix()}"
        self._upgrade_database(database_url)
        runtime_store = RuntimeStore(database_url)
        event_router = EventRouter(runtime_store)
        table_lease_manager = TableLeaseManager(runtime_store.engine)
        supervisor = Supervisor(
            config=config,
            runtime_store=runtime_store,
            event_router=event_router,
        )
        table_provider_registry = create_default_table_provider_registry(
            config.resolved_runtime_dir(),
            memory_table_limits=config.memory_table_limits(),
        )
        lifecycle_service = SharedPublicationLifecycleService(
            runtime_store,
            table_ref_release_service=TableRefReleaseService(
                store=runtime_store,
                provider_registry=table_provider_registry,
            ),
        )
        cleanup_worker = SharedPublicationCleanupWorker(
            config=config,
            store=runtime_store,
            lifecycle_service=lifecycle_service,
        )
        core_definitions = default_node_definitions()
        plugin_catalog = discover_plugins(
            config.resolved_plugin_dir()
        ).with_reserved_definitions(
            core_definitions,
            reserved_plugin_ids={"flowweaver.core", "flowweaver.dev_test"},
        )
        return ServiceContainer(
            config=config,
            runtime_store=runtime_store,
            event_router=event_router,
            table_lease_manager=table_lease_manager,
            supervisor=supervisor,
            node_registry=create_default_node_registry(plugin_catalog),
            plugin_catalog=plugin_catalog,
            table_provider_registry=table_provider_registry,
            shared_publication_lifecycle_service=lifecycle_service,
            shared_publication_cleanup_worker=cleanup_worker,
            instance_lock=lock,
        )

    def _ensure_directories(self) -> None:
        for path in [
            self.config.data_dir,
            self.config.resolved_metadata_db_path().parent,
            self.config.resolved_runtime_dir(),
            self.config.resolved_log_dir(),
            self.config.resolved_temp_dir(),
            self.config.data_dir / "config",
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _load_or_create_token(self) -> str:
        token_path = self.config.data_dir / "config" / "local_api_token"
        if token_path.exists():
            return token_path.read_text(encoding="utf-8").strip()
        token = new_id()
        token_path.write_text(token, encoding="utf-8")
        return token

    def _upgrade_database(self, database_url: str) -> None:
        config = Config("alembic.ini")
        config.set_main_option("script_location", "migrations")
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")


def bootstrap_default(
    data_dir: str | Path = "runtime",
    *,
    workflow_process_execution_mode: WorkflowProcessExecutionMode | str | None = None,
    workflow_process_max_concurrent_node_tasks: int | str | None = None,
) -> ServiceContainer:
    config = EngineConfig(
        data_dir=Path(data_dir),
        workflow_process_execution_mode=resolve_workflow_process_execution_mode(
            workflow_process_execution_mode
        ),
        workflow_process_max_concurrent_node_tasks=(
            resolve_workflow_process_max_concurrent_node_tasks(
                workflow_process_max_concurrent_node_tasks
            )
        ),
    )
    return EngineHostBootstrap(config).initialize()


def _resolve_config_paths(config: EngineConfig) -> EngineConfig:
    data_dir = config.data_dir.resolve()
    return config.model_copy(
        update={
            "data_dir": data_dir,
            "metadata_db_path": (
                config.metadata_db_path.resolve()
                if config.metadata_db_path is not None
                else data_dir / "metadata" / "flowweaver.db"
            ),
            "runtime_dir": (
                config.runtime_dir.resolve()
                if config.runtime_dir is not None
                else data_dir / "workflow_runs"
            ),
            "log_dir": (
                config.log_dir.resolve()
                if config.log_dir is not None
                else data_dir / "logs"
            ),
            "temp_dir": (
                config.temp_dir.resolve()
                if config.temp_dir is not None
                else data_dir / "temp"
            ),
            "plugin_dir": (
                config.plugin_dir.resolve()
                if config.plugin_dir is not None
                else data_dir.parent / "plugins"
            ),
        }
    )
