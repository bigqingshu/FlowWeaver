from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from flowweaver.common.config import EngineConfig
from flowweaver.common.instance_lock import InstanceLock
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.shared_publication_cleanup_worker import (
    SharedPublicationCleanupWorker,
)
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationLifecycleService,
)
from flowweaver.engine.supervisor import Supervisor
from flowweaver.engine.table_lease_manager import TableLeaseManager
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.nodes.registry import NodeRegistry


@dataclass
class ServiceContainer:
    config: EngineConfig
    runtime_store: RuntimeStore
    event_router: EventRouter
    table_lease_manager: TableLeaseManager
    supervisor: Supervisor
    node_registry: NodeRegistry
    table_provider_registry: TableProviderRegistry | None = None
    shared_publication_lifecycle_service: (
        SharedPublicationLifecycleService | None
    ) = None
    shared_publication_cleanup_worker: SharedPublicationCleanupWorker | None = None
    instance_lock: InstanceLock | None = None
    _started: bool = field(default=False, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _lifecycle_lock: RLock = field(
        default_factory=RLock,
        init=False,
        repr=False,
    )

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("ServiceContainer is closed")
            if self._started:
                return
            self.supervisor.start()
            try:
                if self.shared_publication_cleanup_worker is not None:
                    self.shared_publication_cleanup_worker.start()
            except Exception:
                self.supervisor.close()
                raise
            self._started = True

    def close(self) -> None:
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            self._started = False

        errors: list[Exception] = []
        if self.shared_publication_cleanup_worker is not None:
            try:
                self.shared_publication_cleanup_worker.close()
            except Exception as exc:
                errors.append(exc)
        try:
            self.supervisor.close()
        except Exception as exc:
            errors.append(exc)
        try:
            self.runtime_store.dispose()
        except Exception as exc:
            errors.append(exc)
        if self.instance_lock is not None:
            try:
                self.instance_lock.release()
            except Exception as exc:
                errors.append(exc)
            finally:
                self.instance_lock = None
        if errors:
            raise ExceptionGroup("ServiceContainer close failed", errors)
