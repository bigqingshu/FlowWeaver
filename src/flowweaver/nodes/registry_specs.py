from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from flowweaver.nodes.registry_config_specs import (
    NodeConfigFieldSpec as NodeConfigFieldSpec,
)
from flowweaver.nodes.registry_config_specs import (
    NodeConfigSchemaSpec as NodeConfigSchemaSpec,
)
from flowweaver.nodes.registry_definition_specs import (
    NodeDefinitionSpec as NodeDefinitionSpec,
)
from flowweaver.nodes.registry_io_specs import NodePortSpec as NodePortSpec
from flowweaver.nodes.registry_io_specs import (
    NodeTableInputSlotSpec as NodeTableInputSlotSpec,
)
from flowweaver.nodes.registry_io_specs import (
    NodeTableOutputSlotSpec as NodeTableOutputSlotSpec,
)


@dataclass(frozen=True)
class NodeCatalogState:
    catalog_hash: str
    node_count: int


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()
