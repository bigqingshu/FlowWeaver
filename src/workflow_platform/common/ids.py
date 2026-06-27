from __future__ import annotations

from uuid import uuid4


def new_id() -> str:
    """Return a public string ID.

    The stage-A spec prefers UUIDv7, but allows UUID4 when a UUIDv7 provider is
    unavailable in the first stage.
    """

    return str(uuid4())
