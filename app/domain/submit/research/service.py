from app.domain.submit.research.schema import (
    ResearchSubmitSchema,
    Comment
)
from app.domain.user.model import User
from app.domain.submit.research.repository import ResearchRepository
from app.exceptions import NotFoundError
from app.enums.enums import ReportState


class ResearchService:
    def __init__(self, repo: ResearchRepository, user: User):
        self.repo = repo
        self.user = user

    async def get_all(self):
        """
        Retrieve all research records from the database.

        Returns:
            list[ResearchOut]: List of all research entries.
        """
        return await self.repo.get_all()

    async def get_by_user(self):
        """
        Retrieve research records submitted by the currently authenticated user.

        Raises:
            ValueError: If user context is not provided.

        Returns:
            list[ResearchOut]: List of research records by the user.
        """
        if not self.user:
            raise ValueError("User context required")
        return await self.repo.get_by_user(self.user.privy_id)

    async def get_by_state(self, state: str):
        """
        Retrieve research records filtered by a specific report state.

        Args:
            state (str): The desired report state.

        Returns:
            list[ResearchOut]: List of research entries in the specified state.
        """
        return await self.repo.get_by_state(state)

    async def get_by_id(self, research_id: str):
        """
        Retrieve a specific research record by its ID.

        Args:
            research_id (str): UUID of the research record.

        Raises:
            NotFoundError: If the research record is not found.

        Returns:
            ResearchOut: The requested research record.
        """
        research = await self.repo.get_by_id(research_id)
        if not research:
            raise NotFoundError("Research not found")
        return research

    async def create(self, data: ResearchSubmitSchema):
        """
        Create a new research record.

        Args:
            data (ResearchSubmitSchema): Payload for the new research.

        Raises:
            ValueError: If user context is missing.
        """
        if not self.user:
            raise ValueError("User context required")
        data.user_privy_id = self.user.privy_id
        await self.repo.create(entity=data, current_user=self.user)

    async def update(self, research_id: str, data: ResearchSubmitSchema):
        """
        Update an existing research record.

        Args:
            research_id (str): UUID of the research to update.
            data (ResearchSubmitSchema): Updated data.

        Raises:
            NotFoundError: If the research is not found.
            PermissionError: If the current user is not authorized.
        """
        research = await self.repo.get_by_id(research_id)
        if not research:
            raise NotFoundError("Research not found")
        if research.user_privy_id != self.user.privy_id:
            raise PermissionError("Not authorized to update this research")
        await self.repo.update(research_id, data)

    async def update_state(self, research_id: str, data: ReportState):
        """
        Update the state of an existing research record.

        Args:
            research_id (str): UUID of the research to update.
            data (ReportState): New report state.

        Raises:
            NotFoundError: If the research is not found.

        Returns:
            ResearchOut: The research record with the updated state.
        """
        research = await self.repo.update_state(
            research_id,
            state=data,
            current_user=self.user
        )
        if not research:
            raise NotFoundError("Research not found")
        return research

    async def add_comment(self, research_id: str, data: str):
        """
        Add a comment to a research record.

        Args:
            research_id (str): UUID of the research to update.
            data (str): Comment content to add.

        Raises:
            NotFoundError: If the research is not found.

        Returns:
            Comment: The comment that was added.
        """
        comment = Comment(
            role=self.user.role,
            content=data
        )
        research = await self.repo.add_comment(
            research_id,
            comment=comment,
            current_user=self.user
        )
        if not research:
            raise NotFoundError("Research not found")
        return comment
