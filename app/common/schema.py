from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base model that converts snake_case to camelCase for JSON output"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,     # ✅ NEW: Accept snake_case field names
        validate_by_alias=True,    # ✅ NEW: Accept camelCase aliases  
        from_attributes=True,
        populate_by_name=True
    )


class PaginatedSchema(CamelModel, Generic[T]):
    items: list[T]
    total: int