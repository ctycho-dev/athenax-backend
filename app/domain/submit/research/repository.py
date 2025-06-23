from datetime import datetime
from beanie.operators import Eq
from beanie import PydanticObjectId
from app.common.base_repository import BaseRepository
from app.domain.submit.research.model import ResearchSubmit
from app.domain.submit.research.schema import (
    ResearchSubmitSchema,
    ResearchOut,
    Comment
)
from app.domain.user.model import User
from app.exceptions import (
    NotFoundError
)
from app.enums.enums import (
    ReportState,
    UserRole
)


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
    
    async def get_by_state(
        self,
        state: str,
    ) -> list[ResearchOut]:
        """
        Retrieve audit submissions filtered by report state, ordered by newest first.

        Args:
            state (str): Desired state to filter audits by.

        Returns:
            list[ResearchOut]: List of audits in the given state.
        """
        data = (
            await ResearchSubmit.find(Eq(ResearchSubmit.state, state))
            .sort("-created_at")
            .to_list()
        )
        return [ResearchOut(**self._serialize(x.model_dump())) for x in data]

    async def update_state(
        self,
        _id: str,
        state: ReportState,
        current_user: User | None
    ) -> ResearchOut:
        """
        Update the state of an audit submission by its ID.

        Optionally updates metadata like `updated_at` and `updated_by`.

        Args:
            _id (str): The ID of the audit submission to update.
            state (ReportState): The new state to assign.
            current_user (User | None): The user performing the update.

        Returns:
            AuditOut: The updated audit submission.

        Raises:
            NotFoundError: If no audit with the specified ID is found.
        """
        doc = await self.collection.find_one({"_id": PydanticObjectId(_id)})
        if not doc:
            raise NotFoundError(f"Audit with ID {_id} not found")

        doc.state = state

        if hasattr(doc, 'updated_at'):
            doc.updated_at = datetime.now()

        if current_user and hasattr(doc, 'updated_by'):
            doc.updated_by = current_user

        await doc.save()
        return ResearchOut(**self._serialize(doc.model_dump()))

    async def add_comment(
        self,
        _id: str,
        comment: Comment,
        current_user: User | None
    ) -> Comment:
        """
        Add a comment to an audit submission and update state if role is BD.

        Also updates metadata like `updated_at` and `updated_by` if applicable.

        Args:
            _id (str): The ID of the audit submission to comment on.
            comment (Comment): The comment to add.
            current_user (User | None): The user performing the action.

        Returns:
            Comment: The comment that was added.

        Raises:
            NotFoundError: If the audit submission with the specified ID is not found.
        """
        doc = await self.collection.find_one({"_id": PydanticObjectId(_id)})
        if not doc:
            raise NotFoundError(f"Audit with ID {_id} not found")

        doc.comments.append(comment)

        if comment.role == UserRole.BD:
            doc.state = ReportState.UPDATE_INFO

        if hasattr(doc, 'updated_at'):
            doc.updated_at = datetime.now()

        if current_user and hasattr(doc, 'updated_by'):
            doc.updated_by = current_user

        await doc.save()
        return comment
