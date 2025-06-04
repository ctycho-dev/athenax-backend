from app.common.base_repository import BaseRepository
from app.domain.submit.research.model import ResearchSubmit
from app.domain.submit.research.schema import ResearchSubmitSchema, ResearchOut


class ResearchRepository(
    BaseRepository[ResearchSubmit, ResearchOut, ResearchSubmitSchema]
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
        super().__init__(ResearchSubmit, ResearchOut, ResearchSubmitSchema)

    async def get_by_user(
        self,
        privy_id: str,
    ) -> list[ResearchOut] | None:
        """
        Get user by privy_id with optional field projection.

        Args:
            privy_id: The user's privy_id

        Returns:
            User model instance or None if not found

        """
        data = await ResearchSubmit.find({"user_privy_id": privy_id}).to_list()

        return [ResearchOut(**self._serialize(x.model_dump())) for x in data]
