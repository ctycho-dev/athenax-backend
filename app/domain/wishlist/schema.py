from pydantic import BaseModel


class WishlistIn(BaseModel):
    email: str
