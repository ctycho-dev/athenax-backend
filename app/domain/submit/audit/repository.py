from datetime import datetime
from beanie.operators import Eq
from beanie import PydanticObjectId

from app.common.base_repository import BaseRepository
from app.domain.submit.audit.model import AuditSubmit
from app.domain.user.model import User
from app.domain.submit.audit.schema import (
    AuditOut,
    AuditSubmitSchema,
    Comment
)
from app.exceptions import (
    NotFoundError
)
from app.enums.enums import (
    ReportState,
    UserRole
)


class AuditRepository(
    BaseRepository[AuditSubmit, AuditOut, AuditSubmitSchema]
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
        super().__init__(AuditSubmit, AuditOut, AuditSubmitSchema)

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
        data = await AuditSubmit.find({"user_privy_id": privy_id}).to_list()

        return [AuditOut(**self._serialize(x.model_dump())) for x in data]
    
    async def get_by_state(
        self,
        state: str,
    ) -> list[AuditOut]:
        """
        Retrieve audits filtered by their report state, ordered by created_at descending.

        Args:
            state (ReportState): The desired audit state.

        Returns:
            List[AuditOut]: List of audits in the given state, newest first.
        """
        data = (
            await AuditSubmit.find(Eq(AuditSubmit.state, state))
            .sort("-created_at")
            .to_list()
        )
        return [AuditOut(**self._serialize(x.model_dump())) for x in data]

    async def add_comment(
        self,
        _id: str,
        comment: Comment,
        current_user: User | None
    ) -> Comment:
        """
        Add a message to the workspace's messages array.
        Update the last message and then append the new one.
        """
        doc = await self.collection.find_one({"_id": PydanticObjectId(_id)})
        if not doc:
            raise NotFoundError(f"Workspace with ID {_id} not found")

        # Append the new message
        doc.comments.append(comment)
        if comment.role == UserRole.BD:
            doc.state = ReportState.UPDATE_INFO

        if hasattr(doc, 'updated_at'):
            doc.updated_at = datetime.now()

        if current_user and hasattr(doc, 'updated_by'):
            doc.updated_by = current_user

        await doc.save()

        return comment
