from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


class RowBatchCounter:
    def __init__(self, row_batches: Iterable[Sequence[dict[str, Any]]]) -> None:
        self._row_batches = row_batches
        self.row_count = 0

    def __iter__(self):
        for rows in self._row_batches:
            self.row_count += len(rows)
            yield rows
