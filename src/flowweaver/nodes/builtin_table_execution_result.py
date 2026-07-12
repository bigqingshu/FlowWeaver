from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Self

from flowweaver.nodes.table_node_output_target_models import (
    TableOutputWriteResult,
)
from flowweaver.protocols.table_ref import TableRefModel


@dataclass(frozen=True)
class BuiltinTableExecutionResult:
    output_refs: tuple[TableRefModel, ...]
    writes: tuple[TableOutputWriteResult, ...] = ()
    output_slot_bindings: dict[str, str] = field(default_factory=dict)
    summary_details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_output_refs(cls, output_refs: Sequence[TableRefModel]) -> Self:
        return cls(output_refs=tuple(output_refs))

    @classmethod
    def from_writes(cls, writes: Sequence[TableOutputWriteResult]) -> Self:
        write_results = tuple(writes)
        return cls(
            output_refs=tuple(write.table_ref for write in write_results),
            writes=write_results,
            output_slot_bindings={
                write.slot: write.table_ref.table_ref_id for write in write_results
            },
        )
