from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from workflow_platform.common.ids import new_id
from workflow_platform.common.time import utc_now
from workflow_platform.protocols.base import StrictModel
from workflow_platform.protocols.enums import EventType


class EventModel(StrictModel):
    event_id: str = Field(default_factory=new_id)
    event_version: str = "1.0"
    event_type: EventType
    timestamp: datetime = Field(default_factory=utc_now)
    workflow_run_id: str | None = None
    node_run_id: str | None = None
    payload: dict[str, Any]
