from __future__ import annotations

from typing import Literal

from pydantic import Field

from flowweaver.protocols.base import StrictModel
from flowweaver.protocols.table_ref import FieldSchemaModel

PLUGIN_RUNTIME_PAYLOAD_VERSION: Literal["1"] = "1"


class PluginInputTableRefModel(StrictModel):
    slot_name: str = Field(min_length=1, max_length=128)
    table_ref_id: str = Field(min_length=1)
    ref_kind: Literal["sqlite_table"] = "sqlite_table"
    access_mode: Literal["read_only"] = "read_only"
    database_uri: str = Field(min_length=1)
    table_name: str = Field(min_length=1, max_length=512)
    schema_: list[FieldSchemaModel] = Field(alias="schema")
    materialized: bool

    @property
    def schema(self) -> list[FieldSchemaModel]:  # type: ignore[override]
        return self.schema_


class PluginOutputTableTargetModel(StrictModel):
    slot_name: str = Field(min_length=1, max_length=128)
    ref_kind: Literal["sqlite_table"] = "sqlite_table"
    access_mode: Literal["write_staging"] = "write_staging"
    database_path: str = Field(min_length=1)
    table_name: str = Field(min_length=1, max_length=512)


class PluginTaskRuntimeModel(StrictModel):
    protocol_version: Literal["1"] = PLUGIN_RUNTIME_PAYLOAD_VERSION
    inputs: list[PluginInputTableRefModel] = Field(default_factory=list)
    output_targets: list[PluginOutputTableTargetModel] = Field(
        default_factory=list
    )


class PluginOutputTableResultModel(StrictModel):
    slot_name: str = Field(min_length=1, max_length=128)
    ref_kind: Literal["sqlite_table"] = "sqlite_table"
    database_path: str = Field(min_length=1)
    table_name: str = Field(min_length=1, max_length=512)
    schema_: list[FieldSchemaModel] = Field(alias="schema")

    @property
    def schema(self) -> list[FieldSchemaModel]:  # type: ignore[override]
        return self.schema_


class PluginTaskRuntimeResultModel(StrictModel):
    protocol_version: Literal["1"] = PLUGIN_RUNTIME_PAYLOAD_VERSION
    outputs: list[PluginOutputTableResultModel] = Field(default_factory=list)
