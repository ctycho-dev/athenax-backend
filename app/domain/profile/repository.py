from beanie import PydanticObjectId
from app.common.base_repository import BaseRepository
from app.domain.profile.model import Profile
from app.domain.profile.schema import ProfileCreate, ProfileOut
from app.exceptions import DatabaseError


class ProfileRepository(
    BaseRepository[Profile, ProfileOut, ProfileCreate]
):
    """
    MongoDB repository implementation for managing users.

    This class extends the BaseRepository and implements the BaseRepository interface for the UserCollection,
    providing CRUD operations and additional methods specific to users.
    """

    def __init__(self):
        """
        Initializes the UserRepository with the UserCollection and ProfileOut schema.
        """
        super().__init__(Profile, ProfileOut, ProfileCreate)

    async def get_by_user_id(
        self, 
        user_id: str,
    ) -> ProfileOut | None:
        """
        Retrieves all files associated with a specific company ID.

        Args:
            user_id (str): The ID of the company to filter files by

        Returns:
            list[FileOut]: List of file output schemas for the matching files

        Raises:
            DatabaseError: If there's an error during database operation
        """
        try:
            query = self.collection.find(
                {'user_id': PydanticObjectId(user_id)}
            )
            
            entity = await query.to_list()
            if not entity:
                return None

            serialized_entity = self._serialize(entity[0].model_dump())
            return ProfileOut(**serialized_entity)
        except Exception as e:
            raise DatabaseError(f"Failed to fetch profile for user {user_id}: {str(e)}") from e
