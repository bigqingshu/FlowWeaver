from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.config import EngineConfig
from flowweaver.common.ids import new_id
from flowweaver.common.instance_lock import InstanceLock
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.service_container import ServiceContainer
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.nodes.registry import NodeRegistry


class EngineHostBootstrap:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config

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
        return ServiceContainer(
            config=config,
            runtime_store=runtime_store,
            event_router=event_router,
            table_lease_manager=table_lease_manager,
            node_registry=NodeRegistry(),
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


def bootstrap_default(data_dir: str | Path = "runtime") -> ServiceContainer:
    return EngineHostBootstrap(EngineConfig(data_dir=Path(data_dir))).initialize()
