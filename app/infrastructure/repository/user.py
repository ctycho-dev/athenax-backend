from app.infrastructure.repository.base import BaseRepository
from app.database.models.user import User
from app.schemas.user import UserCreate, UserOut


class UserRepository(
    BaseRepository[User, UserOut, UserCreate]
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
        super().__init__(User, UserOut, UserCreate)

    async def get_by_privy_id(
        self,
        privy_id: str,
    ) -> User | None:
        """
        Get user by privy_id with optional field projection.

        Args:
            privy_id: The user's privy_id

        Returns:
            User model instance or None if not found

        """
        user = await User.find_one({"privy_id": privy_id})

        return user
