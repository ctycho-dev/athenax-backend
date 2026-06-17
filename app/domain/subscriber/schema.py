from datetime import datetime

from pydantic import EmailStr

from app.common.schema import CamelModel


class SubscriberCreateSchema(CamelModel):
    email: EmailStr


class SubscriberOutSchema(CamelModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime
