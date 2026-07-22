from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr
from pydantic.alias_generators import to_camel

T = TypeVar("T")


def normalize_email(value: str) -> str:
    return value.strip().lower() if isinstance(value, str) else value


NormalizedEmail = Annotated[EmailStr, BeforeValidator(normalize_email)]


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