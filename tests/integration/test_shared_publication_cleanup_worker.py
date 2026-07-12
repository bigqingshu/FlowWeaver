from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from threading import Event

import pytest

from flowweaver.common.config import EngineConfig
from flowweaver.engine.shared_publication_cleanup_worker import (
    SharedPublicationCleanupWorker,
)
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationCleanupOutcome,
    SharedPublicationCleanupResult,
)


class FakeCleanupCandidateStore:
    def __init__(self, candidate_pages: list[list[str]]) -> None:
        self._candidate_pages = deque(candidate_pages)
        self.calls: list[tuple[datetime, datetime, int]] = []
        self.called = Event()

    def list_shared_publication_cleanup_candidate_ids(
        self,
        *,
        now: datetime,
        stale_before: datetime,
        limit: int,
    ) -> list[str]:
        self.calls.append((now, stale_before, limit))
        self.called.set()
        page = self._candidate_pages.popleft() if self._candidate_pages else []
        return page[:limit]


class FakeLifecycleService:
    def __init__(self) -> None:
        self._responses: defaultdict[
            str,
            deque[SharedPublicationCleanupOutcome | Exception],
        ] = defaultdict(deque)
        self.calls: list[tuple[str, int, float, datetime | None]] = []

    def queue(
        self,
        publication_id: str,
        *responses: SharedPublicationCleanupOutcome | Exception,
    ) -> None:
        self._responses[publication_id].extend(responses)

    def cleanup(
        self,
        publication_id: str,
        *,
        max_table_refs: int,
        time_budget_seconds: float,
        now: datetime | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> SharedPublicationCleanupResult:
        self.calls.append(
            (publication_id, max_table_refs, time_budget_seconds, now)
        )
        response = (
            self._responses[publication_id].popleft()
            if self._responses[publication_id]
            else SharedPublicationCleanupOutcome.CLEANED
        )
        if isinstance(response, Exception):
            raise response
        return SharedPublicationCleanupResult(
            publication_id=publication_id,
            outcome=response,
            status=(
                "RELEASING"
                if response == SharedPublicationCleanupOutcome.RETRY_PENDING
                else "RELEASED"
            ),
        )


def worker_config(tmp_path: Path, **updates: object) -> EngineConfig:
    values: dict[str, object] = {
        "data_dir": tmp_path,
        "shared_publication_cleanup_enabled": True,
        "shared_publication_cleanup_interval_seconds": 0.05,
        "shared_publication_cleanup_publication_batch_size": 3,
        "shared_publication_cleanup_table_ref_batch_size": 7,
        "shared_publication_cleanup_cycle_budget_seconds": 2.0,
        "shared_publication_releasing_stale_seconds": 30,
    }
    values.update(updates)
    return EngineConfig.model_validate(values)


def make_worker(
    tmp_path: Path,
    *,
    store: FakeCleanupCandidateStore,
    lifecycle_service: FakeLifecycleService,
    **config_updates: object,
) -> SharedPublicationCleanupWorker:
    return SharedPublicationCleanupWorker(
        config=worker_config(tmp_path, **config_updates),
        store=store,
        lifecycle_service=lifecycle_service,
    )


def test_worker_cycle_respects_publication_and_table_ref_batches(
    tmp_path: Path,
) -> None:
    store = FakeCleanupCandidateStore([["pub-1", "pub-2", "pub-3", "pub-4"]])
    service = FakeLifecycleService()
    worker = make_worker(tmp_path, store=store, lifecycle_service=service)

    result = worker.run_cycle()

    assert [call[0] for call in service.calls] == ["pub-1", "pub-2", "pub-3"]
    assert all(call[1] == 7 for call in service.calls)
    assert result.candidate_count == 3
    assert result.attempted_count == 3
    assert result.cleaned_count == 3
    assert store.calls[0][2] == 3


def test_worker_continues_after_one_candidate_raises(tmp_path: Path) -> None:
    store = FakeCleanupCandidateStore([["pub-fail", "pub-ok"]])
    service = FakeLifecycleService()
    service.queue("pub-fail", ValueError("provider unavailable"))
    worker = make_worker(tmp_path, store=store, lifecycle_service=service)

    result = worker.run_cycle()

    assert [call[0] for call in service.calls] == ["pub-fail", "pub-ok"]
    assert result.failed_count == 1
    assert result.cleaned_count == 1


def test_worker_cycle_stops_starting_candidates_after_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeCleanupCandidateStore([["pub-1", "pub-2", "pub-3"]])
    service = FakeLifecycleService()
    worker = make_worker(
        tmp_path,
        store=store,
        lifecycle_service=service,
        shared_publication_cleanup_cycle_budget_seconds=2.0,
    )
    monotonic_values = iter([0.0, 0.0, 3.0, 3.0])
    monkeypatch.setattr(
        "flowweaver.engine.shared_publication_cleanup_worker.monotonic",
        lambda: next(monotonic_values),
    )

    result = worker.run_cycle()

    assert [call[0] for call in service.calls] == ["pub-1"]
    assert result.attempted_count == 1
    assert result.budget_exhausted is True


def test_worker_retries_its_pending_publication_next_cycle(tmp_path: Path) -> None:
    store = FakeCleanupCandidateStore([["pub-retry"], []])
    service = FakeLifecycleService()
    service.queue(
        "pub-retry",
        SharedPublicationCleanupOutcome.RETRY_PENDING,
        SharedPublicationCleanupOutcome.CLEANED,
    )
    worker = make_worker(tmp_path, store=store, lifecycle_service=service)

    first = worker.run_cycle()
    second = worker.run_cycle()

    assert first.retry_pending_count == 1
    assert second.cleaned_count == 1
    assert [call[0] for call in service.calls] == ["pub-retry", "pub-retry"]


def test_worker_passes_stale_cutoff_to_single_candidate_query(
    tmp_path: Path,
) -> None:
    store = FakeCleanupCandidateStore([["pub-stale"]])
    service = FakeLifecycleService()
    worker = make_worker(tmp_path, store=store, lifecycle_service=service)

    worker.run_cycle()

    assert len(store.calls) == 1
    now, stale_before, _limit = store.calls[0]
    assert (now - stale_before).total_seconds() == 30
    assert service.calls[0][0] == "pub-stale"


def test_worker_stop_prevents_further_store_access(tmp_path: Path) -> None:
    store = FakeCleanupCandidateStore([[], [], []])
    service = FakeLifecycleService()
    worker = make_worker(tmp_path, store=store, lifecycle_service=service)

    worker.start()
    assert store.called.wait(timeout=2)
    assert worker.stop(join_timeout_seconds=2)
    call_count_after_stop = len(store.calls)
    time.sleep(0.1)

    assert worker.is_running is False
    assert len(store.calls) == call_count_after_stop
    worker.close()
