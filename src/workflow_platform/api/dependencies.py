from __future__ import annotations

from fastapi import Request

from workflow_platform.engine.runtime_store import RuntimeStore


def get_runtime_store(request: Request) -> RuntimeStore:
    return request.app.state.runtime_store
