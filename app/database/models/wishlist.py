from beanie import Document


class WishlistCollection(Document):

    email: str

    class Settings:
        name = "wishlist"
