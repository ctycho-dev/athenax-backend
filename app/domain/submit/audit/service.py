# services/submit/audit.py
from app.domain.submit.audit.schema import (
    AuditSubmitSchema,
    Comment
)
from app.domain.user.model import User
from app.domain.submit.audit.repository import AuditRepository
from app.exceptions import NotFoundError
from app.enums.enums import ReportState


class AuditService:
    """
    Service layer for handling business logic related to audit operations.
    """

    def __init__(self, repo: AuditRepository, user: User):
        """
        Initialize the AuditService with a repository and a user context.
        
        Args:
            repo (AuditRepository): Repository for audit DB operations.
            user (User): Currently authenticated user.
        """
        self.repo = repo
        self.user = user

    async def get_all(self):
        """
        Retrieve all audit records from the database.

        Returns:
            list[AuditOut]: List of all audit entries.
        """
        return await self.repo.get_all()

    async def get_by_user(self):
        """
        Retrieve audit records submitted by the currently authenticated user.

        Raises:
            ValueError: If user context is not provided.

        Returns:
            list[AuditOut]: List of audits created by the current user.
        """
        if not self.user:
            raise ValueError("User context required")
        return await self.repo.get_by_user(self.user.privy_id)

    async def get_by_state(self, state: str):
        """
        Retrieve audits filtered by a specific report state.

        Args:
            state (str): The desired report state.

        Returns:
            list[AuditOut]: List of audits in the specified state.
        """
        return await self.repo.get_by_state(state)

    async def get_by_id(self, audit_id: str):
        """
        Retrieve a single audit by its unique ID.

        Args:
            audit_id (str): The audit's UUID.

        Raises:
            NotFoundError: If the audit is not found.

        Returns:
            AuditOut: The corresponding audit entry.
        """
        audit = await self.repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError(f"Audit with ID {audit_id} not found")
        return audit

    async def create(self, data: AuditSubmitSchema):
        """
        Create a new audit entry for the current user.

        Args:
            data (AuditSubmitSchema): Payload for the new audit.

        Raises:
            ValueError: If user context is not available.

        Returns:
            AuditOut: The newly created audit entry.
        """
        if not self.user:
            raise ValueError("User context required")
        data.user_privy_id = self.user.privy_id
        return await self.repo.create(entity=data, current_user=self.user)

    async def update(self, audit_id: str, data: AuditSubmitSchema):
        """
        Update an existing audit if the current user is the owner.

        Args:
            audit_id (str): UUID of the audit to update.
            data (AuditSubmitSchema): Updated audit data.

        Raises:
            NotFoundError: If the audit is not found.
            PermissionError: If the user is not authorized to modify the audit.

        Returns:
            AuditOut: The updated audit record.
        """
        audit = await self.repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit not found")
        if audit.user_privy_id != self.user.privy_id:
            raise PermissionError("Not authorized to update this audit")

        data.state = ReportState.CHECKING
        return await self.repo.update(audit_id, data, current_user=self.user)

    async def update_state(self, audit_id: str, data: ReportState):
        """
        Update the state of an existing audit.

        Args:
            audit_id (str): UUID of the audit to update.
            data (ReportState): New report state.

        Raises:
            NotFoundError: If the audit is not found.

        Returns:
            AuditOut: The audit with the updated state.
        """
        audit = await self.repo.update_state(
            audit_id,
            state=data,
            current_user=self.user
        )
        if not audit:
            raise NotFoundError("Audit not found")
        return audit

    async def add_comment(self, audit_id: str, data: str):
        """
        Add a comment to an audit. Also updates the audit's state if the user's role is BD.

        Args:
            audit_id (str): UUID of the audit to update.
            data (str): Comment content to add.

        Raises:
            NotFoundError: If the audit is not found.

        Returns:
            Comment: The comment that was added.
        """
        comment = Comment(
            role=self.user.role,
            content=data
        )
        audit = await self.repo.add_comment(
            audit_id,
            comment=comment,
            current_user=self.user
        )
        if not audit:
            raise NotFoundError("Audit not found")
        return comment

