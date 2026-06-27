from __future__ import annotations

from dataclasses import dataclass

from flowweaver.common.config import EngineConfig
from flowweaver.common.instance_lock import InstanceLock
from flowweaver.engine.event_router import EventRouter
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.nodes.registry import NodeRegistry


@dataclass
class ServiceContainer:
    config: EngineConfig
    runtime_store: RuntimeStore
    event_router: EventRouter
    node_registry: NodeRegistry
    instance_lock: InstanceLock | None = None

    def close(self) -> None:
        self.runtime_store.dispose()
        if self.instance_lock is not None:
            self.instance_lock.release()
            self.instance_lock = None
