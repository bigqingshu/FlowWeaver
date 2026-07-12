from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Event, Lock, Thread
from time import monotonic
from typing import Protocol

from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationCleanupOutcome,
    SharedPublicationCleanupResult,
)


class SharedPublicationCleanupCandidateStore(Protocol):
    def list_shared_publication_cleanup_candidate_ids(
        self,
        *,
        now: datetime,
        stale_before: datetime,
        limit: int,
    ) -> list[str]: ...


class SharedPublicationCleanupService(Protocol):
    def cleanup(
        self,
        publication_id: str,
        *,
        max_table_refs: int = 50,
        time_budget_seconds: float = 2.0,
        now: datetime | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> SharedPublicationCleanupResult: ...


@dataclass(frozen=True)
class SharedPublicationCleanupCycleResult:
    candidate_count: int
    attempted_count: int
    cleaned_count: int
    retry_pending_count: int
    blocked_count: int
    failed_count: int
    budget_exhausted: bool


class SharedPublicationCleanupWorker:
    def __init__(
        self,
        *,
        config: EngineConfig,
        store: SharedPublicationCleanupCandidateStore,
        lifecycle_service: SharedPublicationCleanupService,
    ) -> None:
        self._config = config
        self._store = store
        self._lifecycle_service = lifecycle_service
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._state_lock = Lock()
        self._pending_ids: deque[str] = deque()
        self._pending_id_set: set[str] = set()

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self._config.shared_publication_cleanup_enabled:
            return
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(
                target=self._maintenance_loop,
                name="flowweaver-shared-publication-cleanup",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, join_timeout_seconds: float = 2.0) -> bool:
        self._stop_event.set()
        with self._state_lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=max(0.0, join_timeout_seconds))
        stopped = not thread.is_alive()
        if stopped:
            with self._state_lock:
                if self._thread is thread:
                    self._thread = None
        return stopped

    def close(self) -> None:
        timeout = max(
            2.0,
            self._config.shared_publication_cleanup_cycle_budget_seconds + 1.0,
        )
        if not self.stop(join_timeout_seconds=timeout):
            raise TimeoutError("Shared publication cleanup worker did not stop")

    def run_cycle(self) -> SharedPublicationCleanupCycleResult:
        cycle_started = monotonic()
        cycle_now = utc_now()
        publication_limit = (
            self._config.shared_publication_cleanup_publication_batch_size
        )
        candidate_ids = self._take_pending(publication_limit)
        remaining_slots = publication_limit - len(candidate_ids)
        if remaining_slots > 0 and not self._stop_event.is_set():
            database_candidates = (
                self._store.list_shared_publication_cleanup_candidate_ids(
                    now=cycle_now,
                    stale_before=cycle_now
                    - timedelta(
                        seconds=(
                            self._config.shared_publication_releasing_stale_seconds
                        )
                    ),
                    limit=remaining_slots,
                )
            )
            for publication_id in database_candidates:
                if publication_id not in candidate_ids:
                    candidate_ids.append(publication_id)

        attempted_count = 0
        cleaned_count = 0
        retry_pending_count = 0
        blocked_count = 0
        failed_count = 0
        budget_exhausted = False
        cycle_budget = self._config.shared_publication_cleanup_cycle_budget_seconds
        for publication_id in candidate_ids:
            elapsed = monotonic() - cycle_started
            if self._stop_event.is_set() or elapsed >= cycle_budget:
                budget_exhausted = elapsed >= cycle_budget
                self._enqueue_pending(publication_id)
                continue
            attempted_count += 1
            try:
                result = self._lifecycle_service.cleanup(
                    publication_id,
                    max_table_refs=(
                        self._config.shared_publication_cleanup_table_ref_batch_size
                    ),
                    time_budget_seconds=max(0.001, cycle_budget - elapsed),
                    now=cycle_now,
                    should_stop=self._stop_event.is_set,
                )
            except Exception:
                failed_count += 1
                continue
            if result.outcome == SharedPublicationCleanupOutcome.CLEANED:
                cleaned_count += 1
            elif result.outcome == SharedPublicationCleanupOutcome.RETRY_PENDING:
                retry_pending_count += 1
                self._enqueue_pending(publication_id)
            elif result.outcome == SharedPublicationCleanupOutcome.BLOCKED:
                blocked_count += 1

        return SharedPublicationCleanupCycleResult(
            candidate_count=len(candidate_ids),
            attempted_count=attempted_count,
            cleaned_count=cleaned_count,
            retry_pending_count=retry_pending_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            budget_exhausted=budget_exhausted,
        )

    def _maintenance_loop(self) -> None:
        interval = self._config.shared_publication_cleanup_interval_seconds
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception:
                pass
            deadline = monotonic() + interval
            while not self._stop_event.is_set():
                remaining = deadline - monotonic()
                if remaining <= 0:
                    break
                self._stop_event.wait(remaining)

    def _take_pending(self, limit: int) -> list[str]:
        selected: list[str] = []
        while self._pending_ids and len(selected) < limit:
            publication_id = self._pending_ids.popleft()
            self._pending_id_set.discard(publication_id)
            selected.append(publication_id)
        return selected

    def _enqueue_pending(self, publication_id: str) -> None:
        if publication_id in self._pending_id_set:
            return
        self._pending_id_set.add(publication_id)
        self._pending_ids.append(publication_id)
