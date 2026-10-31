from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base for every API schema: camelCase JSON, snake_case Python (guide §6.4)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class DataResponse[DataT](ApiModel):
    """Success envelope: { "data": ..., "meta": { ... } }."""

    data: DataT
    meta: dict[str, Any] = Field(default_factory=dict)


class ErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ApiModel):
    """Error envelope: { "error": { "code", "message", "details" } }."""

    error: ErrorBody
