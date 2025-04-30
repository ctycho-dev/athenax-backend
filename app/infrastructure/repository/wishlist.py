from app.infrastructure.repository.base import BaseRepository
from app.database.models.wishlist import WishlistCollection
from app.schemas.wishlist import WishlistIn


class WishlistRepository(
    BaseRepository[WishlistCollection, WishlistIn, WishlistIn]
):
    """
    MongoDB repository implementation for managing users.

    This class extends the BaseRepository and implements the BaseRepository interface for the UserCollection,
    providing CRUD operations and additional methods specific to users.
    """

    def __init__(self):
        """
        Initializes the UserRepository with the UserCollection and UserOut schema.
        """
        super().__init__(WishlistCollection, WishlistIn, WishlistIn)
