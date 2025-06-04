from app.common.metadata_document import BaseDocument


class WishlistCollection(BaseDocument):

    email: str

    class Settings:
        name = "wishlist"
