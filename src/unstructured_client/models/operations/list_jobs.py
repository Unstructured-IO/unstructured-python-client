"""Code generated by Speakeasy (https://speakeasy.com). DO NOT EDIT."""

from __future__ import annotations
import httpx
import pydantic
from pydantic import model_serializer
from typing import List, Optional
from typing_extensions import Annotated, NotRequired, TypedDict
from unstructured_client.models.shared import jobinformation as shared_jobinformation
from unstructured_client.types import (
    BaseModel,
    Nullable,
    OptionalNullable,
    UNSET,
    UNSET_SENTINEL,
)
from unstructured_client.utils import FieldMetadata, HeaderMetadata, QueryParamMetadata


class ListJobsRequestTypedDict(TypedDict):
    status: NotRequired[Nullable[str]]
    unstructured_api_key: NotRequired[Nullable[str]]
    workflow_id: NotRequired[Nullable[str]]


class ListJobsRequest(BaseModel):
    status: Annotated[
        OptionalNullable[str],
        FieldMetadata(query=QueryParamMetadata(style="form", explode=True)),
    ] = UNSET

    unstructured_api_key: Annotated[
        OptionalNullable[str],
        pydantic.Field(alias="unstructured-api-key"),
        FieldMetadata(header=HeaderMetadata(style="simple", explode=False)),
    ] = UNSET

    workflow_id: Annotated[
        OptionalNullable[str],
        FieldMetadata(query=QueryParamMetadata(style="form", explode=True)),
    ] = UNSET

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        optional_fields = ["status", "unstructured-api-key", "workflow_id"]
        nullable_fields = ["status", "unstructured-api-key", "workflow_id"]
        null_default_fields = []

        serialized = handler(self)

        m = {}

        for n, f in type(self).model_fields.items():
            k = f.alias or n
            val = serialized.get(k)
            serialized.pop(k, None)

            optional_nullable = k in optional_fields and k in nullable_fields
            is_set = (
                self.__pydantic_fields_set__.intersection({n})
                or k in null_default_fields
            )  # pylint: disable=no-member

            if val is not None and val != UNSET_SENTINEL:
                m[k] = val
            elif val != UNSET_SENTINEL and (
                not k in optional_fields or (optional_nullable and is_set)
            ):
                m[k] = val

        return m


class ListJobsResponseTypedDict(TypedDict):
    content_type: str
    r"""HTTP response content type for this operation"""
    status_code: int
    r"""HTTP response status code for this operation"""
    raw_response: httpx.Response
    r"""Raw HTTP response; suitable for custom response parsing"""
    response_list_jobs: NotRequired[List[shared_jobinformation.JobInformationTypedDict]]
    r"""Successful Response"""


class ListJobsResponse(BaseModel):
    content_type: str
    r"""HTTP response content type for this operation"""

    status_code: int
    r"""HTTP response status code for this operation"""

    raw_response: httpx.Response
    r"""Raw HTTP response; suitable for custom response parsing"""

    response_list_jobs: Optional[List[shared_jobinformation.JobInformation]] = None
    r"""Successful Response"""
