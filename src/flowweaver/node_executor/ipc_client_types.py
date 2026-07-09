from __future__ import annotations

from collections.abc import Callable

from flowweaver.protocols.ipc_messages import IPCEnvelope
from flowweaver.protocols.node_task import NodeTaskModel

NodeTaskIpcEventHandler = Callable[[NodeTaskModel, IPCEnvelope], None]
