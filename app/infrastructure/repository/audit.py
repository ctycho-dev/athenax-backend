from app.infrastructure.repository.base import BaseRepository
from app.database.models.audit import AuditForm
from app.schemas.audit import AuditOut, AuditFormSchema


class AuditRepository(
    BaseRepository[AuditForm, AuditOut, AuditFormSchema]
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
        super().__init__(AuditForm, AuditOut, AuditFormSchema)

    async def get_by_user(
        self,
        privy_id: str,
    ) -> list[AuditOut] | None:
        """
        Get user by privy_id with optional field projection.

        Args:
            privy_id: The user's privy_id

        Returns:
            User model instance or None if not found

        """
        data = await AuditForm.find({"user_privy_id": privy_id}).to_list()

        return [AuditOut(**self._serialize(x.model_dump())) for x in data]
