from __future__ import annotations

from typing import TypeVar

import msgpack
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def to_msgpack(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json", by_alias=True)
    return msgpack.packb(payload, use_bin_type=True)


def from_msgpack(data: bytes, model_type: type[ModelT]) -> ModelT:
    payload = msgpack.unpackb(data, raw=False)
    return model_type.model_validate(payload)
