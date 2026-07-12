from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from flowweaver.engine.runtime_models import RunTableCleanupCandidate
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.engine.table_ref_release import (
    TableRefReleaseOutcome,
    TableRefReleaseService,
)

_COMPLETED = "COMPLETED"
_RETRY_PENDING = "RETRY_PENDING"


@dataclass(frozen=True)
class _CleanupCursor:
    created_at: str
    table_ref_id: str


def cleanup_table_refs_for_run(
    *,
    workflow_run_id: str,
    store: RuntimeStore,
    provider_registry: TableProviderRegistry,
    cursor: str | None = None,
    max_refs: int = 100,
    time_budget_ms: int = 1000,
    clock: Callable[[], float] = monotonic,
) -> dict[str, object]:
    if max_refs <= 0:
        raise ValueError("max_refs must be positive")
    if time_budget_ms <= 0:
        raise ValueError("time_budget_ms must be positive")
    decoded_cursor = _decode_cursor(cursor)
    started_at = clock()
    candidates = store.list_table_ref_cleanup_candidates(
        workflow_run_id,
        after_created_at=(
            decoded_cursor.created_at if decoded_cursor is not None else None
        ),
        after_table_ref_id=(
            decoded_cursor.table_ref_id if decoded_cursor is not None else None
        ),
        limit=max_refs + 1,
    )
    cleaned_table_ref_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    processed_count = 0
    last_processed: RunTableCleanupCandidate | None = None
    release_service = TableRefReleaseService(
        store=store,
        provider_registry=provider_registry,
    )
    time_budget_seconds = time_budget_ms / 1000
    for candidate in candidates[:max_refs]:
        if clock() - started_at >= time_budget_seconds:
            break
        result = release_service.release(candidate.table_ref_id)
        processed_count += 1
        last_processed = candidate
        if result.outcome == TableRefReleaseOutcome.SKIPPED:
            skipped.append(
                {
                    "table_ref_id": candidate.table_ref_id,
                    "reason": result.reason or "release_skipped",
                }
            )
            continue
        if result.outcome == TableRefReleaseOutcome.FAILED:
            failed.append(
                {
                    "table_ref_id": candidate.table_ref_id,
                    "reason": result.reason or "release_failed",
                }
            )
            continue
        cleaned_table_ref_ids.append(candidate.table_ref_id)
    has_more = processed_count < len(candidates)
    continuation_cursor = None
    if has_more:
        continuation_cursor = (
            _encode_cursor(last_processed)
            if last_processed is not None
            else cursor
        )
    return {
        "workflow_run_id": workflow_run_id,
        "outcome": _RETRY_PENDING if has_more else _COMPLETED,
        "processed_count": processed_count,
        "cleaned_count": len(cleaned_table_ref_ids),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "cleaned_table_ref_ids": cleaned_table_ref_ids,
        "skipped": skipped,
        "failed": failed,
        "continuation_cursor": continuation_cursor,
    }


def _encode_cursor(candidate: RunTableCleanupCandidate) -> str:
    payload = json.dumps(
        [candidate.created_at, candidate.table_ref_id],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(value: str | None) -> _CleanupCursor | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid cleanup cursor") from exc
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not all(isinstance(item, str) and item for item in payload)
    ):
        raise ValueError("invalid cleanup cursor")
    return _CleanupCursor(created_at=payload[0], table_ref_id=payload[1])
