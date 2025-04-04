"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
import pydantic
from typing import Optional
from typing_extensions import Annotated, NotRequired, TypedDict
from unstructured_client.types import BaseModel


class SnowflakeDestinationConnectorConfigTypedDict(TypedDict):
    account: str
    batch_size: int
    database: str
    host: str
    password: str
    port: int
    record_id_key: str
    role: str
    table_name: str
    user: str
    schema_: NotRequired[str]


class SnowflakeDestinationConnectorConfig(BaseModel):
    account: str

    batch_size: int

    database: str

    host: str

    password: str

    port: int

    record_id_key: str

    role: str

    table_name: str

    user: str

    schema_: Annotated[Optional[str], pydantic.Field(alias="schema")] = None
